#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP代理服务器 - 重构版本
模块化设计，分离HTTP和HTTPS处理逻辑

使用前请先安装依赖：
    pip install requests
    或
    uv sync
"""

import socket
from typing import Optional, Tuple

from parsers.request_parser import RequestParser
from utils.logger import RequestLogger
from handlers.http_handler import HTTPHandler
from handlers.https_handler import HTTPSHandler
from builders.response_builder import ResponseBuilder


class ProxyServer:
    """代理服务器主类"""

    def __init__(self, host="127.0.0.1", port=8888, log_file="proxy_log.json"):
        """
        初始化代理服务器

        Args:
            host: 监听地址（127.0.0.1表示只监听本地，0.0.0.0表示监听所有网络接口）
            port: 监听端口
            log_file: 日志文件路径，用于保存所有请求记录
        """
        self.host = host
        self.port = port
        self.socket = None

        # 初始化各个模块
        self.request_parser = RequestParser()
        self.logger = RequestLogger(log_file)
        self.http_handler = HTTPHandler()
        self.https_handler = HTTPSHandler(self.logger)
        self.response_builder = ResponseBuilder()

    def start(self):
        """启动代理服务器"""
        # 创建一个TCP socket
        # AF_INET 表示使用IPv4
        # SOCK_STREAM 表示使用TCP协议
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 设置socket选项，允许地址重用（这样即使端口被占用，重启后也能立即使用）
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 绑定到指定的地址和端口
        self.socket.bind((self.host, self.port))

        # 开始监听，参数10表示最多允许10个连接在队列中等待
        self.socket.listen(10)

        # 设置socket超时，这样accept()会定期返回，可以检查KeyboardInterrupt
        # 在Windows上，阻塞的socket操作可能不会立即响应Ctrl-C
        self.socket.settimeout(1.0)  # 1秒超时

        print(f"代理服务器启动在 {self.host}:{self.port}")
        print(f"等待客户端连接...")
        print("按 Ctrl+C 停止服务器")

        try:
            # 无限循环，持续接受客户端连接
            while True:
                try:
                    # accept() 会阻塞等待，直到有客户端连接或超时
                    # client_socket: 与客户端通信的socket对象
                    # client_address: 客户端的地址元组 (IP, 端口)
                    client_socket, client_address = self.socket.accept()
                except socket.timeout:
                    # 超时是正常的，继续循环以检查KeyboardInterrupt
                    continue

                print(f"收到来自 {client_address[0]}:{client_address[1]} 的连接")

                try:
                    # 接收完整的HTTP请求
                    request_data = self._receive_full_request(client_socket)

                    if request_data:
                        # 解析HTTP请求
                        request_info = self.request_parser.parse(request_data)

                        if request_info:
                            # 打印解析结果
                            self._print_request_info(request_info)

                            # 将请求记录到JSON文件
                            self.logger.log(request_info, client_address)

                            # 根据请求方法选择处理器
                            method = request_info.get("method", "").upper()

                            if method == "CONNECT":
                                # HTTPS请求：使用HTTPS处理器
                                response_data = self.https_handler.handle(
                                    request_info, client_socket
                                )
                                # CONNECT请求已完全处理（包括数据转发），不需要继续
                                if response_data is not None:
                                    # 如果返回了错误响应，发送给客户端
                                    self._send_response(client_socket, response_data)
                            else:
                                # HTTP请求：使用HTTP处理器
                                response_data = self.http_handler.handle(request_info)

                                # 将响应发送回客户端
                                if response_data:
                                    self._send_response(client_socket, response_data)
                                else:
                                    print("[ERROR] 未能获取响应")
                        else:
                            print("无法解析请求")
                            # 发送错误响应
                            error_response = self.response_builder.create_error_response(
                                400, "Bad Request: Unable to parse request"
                            )
                            self._send_response(client_socket, error_response)
                    else:
                        print("未收到请求数据")

                except Exception as e:
                    print(f"处理请求时出错: {e}")
                finally:
                    # 关闭客户端连接
                    # 注意：对于HTTP/1.1，如果响应头部有Connection: close，应该关闭连接
                    # 对于HTTP/1.0，默认关闭连接
                    # 对于CONNECT请求，连接已在处理器中关闭
                    try:
                        client_socket.close()
                    except:
                        pass
                    print(f"已关闭与 {client_address} 的连接\n")

        except KeyboardInterrupt:
            print("\n正在关闭服务器...")
            self.stop()
        except Exception as e:
            print(f"\n服务器出错: {e}")
            self.stop()

    def stop(self):
        """停止代理服务器"""
        if self.socket:
            self.socket.close()
            print("服务器已关闭")

    def _receive_full_request(self, client_socket: socket.socket) -> bytes:
        """
        接收完整的HTTP请求

        HTTP请求格式：
        - 请求行（方法 URL 协议版本）
        - 请求头部（每行一个键值对）
        - 空行（\r\n\r\n）
        - 请求体（可选，如果有Content-Length头部）

        Args:
            client_socket: 客户端socket连接

        Returns:
            bytes: 完整的请求数据
        """
        request_data = b""
        client_socket.settimeout(30)  # 设置30秒超时

        try:
            # 循环接收数据，直到收到完整的请求
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk

                # 检查是否已经收到请求头部（头部以\r\n\r\n结束）
                if b"\r\n\r\n" in request_data:
                    # 分离头部和body
                    headers_end = request_data.find(b"\r\n\r\n")
                    headers_data = request_data[:headers_end]

                    # 尝试解析Content-Length头部
                    headers_text = headers_data.decode("utf-8", errors="ignore")
                    content_length = 0

                    for line in headers_text.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            try:
                                content_length = int(line.split(":", 1)[1].strip())
                            except ValueError:
                                pass
                            break

                    # 如果已经收到完整的请求（头部 + body），退出循环
                    body_start = headers_end + 4  # +4 是 \r\n\r\n 的长度
                    if len(request_data) >= body_start + content_length:
                        break

                    # 如果Content-Length为0，说明没有body，也可以退出
                    if content_length == 0:
                        break

            return request_data
        except socket.timeout:
            print("接收请求超时")
            return b""
        except Exception as e:
            print(f"接收请求时出错: {e}")
            return b""

    def _print_request_info(self, request_info: dict) -> None:
        """
        打印请求信息（用于调试）

        Args:
            request_info: 解析后的请求信息字典
        """
        print("\n" + "=" * 50)
        print("解析到的请求信息：")
        print(f"  方法: {request_info.get('method')}")
        print(f"  URL: {request_info.get('url')}")
        print(f"  目标主机: {request_info.get('target_host')}")
        print(f"  路径: {request_info.get('path')}")
        print(f"  查询参数: {request_info.get('query')}")
        print(f"  HTTP版本: {request_info.get('http_version')}")
        print(f"  头部数量: {len(request_info.get('headers', {}))}")
        if request_info.get("body"):
            print(
                f"  请求体长度: {len(request_info.get('body'))} 字节"
            )
        print("=" * 50 + "\n")

    def _send_response(
        self, client_socket: socket.socket, response_data: bytes
    ) -> None:
        """
        将响应数据发送给客户端

        Args:
            client_socket: 客户端socket连接
            response_data: 响应数据（bytes）
        """
        if not response_data:
            return

        try:
            total_sent = 0
            while total_sent < len(response_data):
                sent = client_socket.send(response_data[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent
            print(f"[OK] 已转发响应给客户端 ({total_sent} 字节)")
        except Exception as e:
            print(f"[ERROR] 发送响应时出错: {e}")


def main():
    """主函数"""
    # 创建代理服务器实例
    # log_file参数指定日志文件路径，默认为 'proxy_log.json'
    proxy = ProxyServer(host="127.0.0.1", port=8888, log_file="proxy_log.json")

    print(f"日志将保存到: proxy_log.json")
    print()

    # 启动服务器
    proxy.start()


if __name__ == "__main__":
    main()
