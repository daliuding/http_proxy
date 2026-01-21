#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTPS请求处理器

负责处理HTTPS CONNECT请求，建立隧道并转发加密数据。
"""

import socket
import select
from typing import Dict, Tuple, Optional
from builders.response_builder import ResponseBuilder
from utils.logger import RequestLogger


class HTTPSHandler:
    """HTTPS请求处理器"""

    def __init__(self, logger: RequestLogger):
        """
        初始化HTTPS处理器

        Args:
            logger: 请求日志记录器
        """
        self.logger = logger
        self.response_builder = ResponseBuilder()

    def handle(
        self, request_info: Dict, client_socket: socket.socket
    ) -> Optional[bytes]:
        """
        处理CONNECT请求，建立HTTPS隧道

        CONNECT方法的工作流程：
        1. 客户端发送：CONNECT host:port HTTP/1.1
        2. 代理服务器连接到目标服务器
        3. 代理服务器返回：HTTP/1.1 200 Connection established
        4. 建立隧道后，代理服务器只是转发数据，不解密HTTPS内容

        Args:
            request_info: 解析后的请求信息字典
            client_socket: 与客户端的socket连接

        Returns:
            bytes: 成功响应或错误响应，如果隧道已建立则返回None
        """
        try:
            # 从URL中提取目标主机和端口
            # CONNECT请求的URL格式通常是 host:port
            url = request_info.get("url", "")
            print(f"  CONNECT目标: {url}")

            # 解析主机和端口
            if ":" in url:
                host, port_str = url.split(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 443  # HTTPS默认端口
            else:
                host = url
                port = 443  # HTTPS默认端口

            print(f"  尝试连接到 {host}:{port}")

            # 连接到目标服务器
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(30)  # 30秒超时

            try:
                target_socket.connect((host, port))
                print(f"  [OK] 成功连接到 {host}:{port}")

                # 更新request_info以记录隧道建立
                request_info["tunnel_established"] = True
                request_info["target_host"] = f"{host}:{port}"

                # 记录CONNECT请求到日志
                try:
                    client_address = client_socket.getpeername()
                    self.logger.log(request_info, client_address)
                    print(f"[OK] 已记录CONNECT请求")
                except Exception as e:
                    print(f"[ERROR] 记录CONNECT日志时出错: {e}")

                # 发送200响应给客户端，表示隧道建立成功
                connect_response = "HTTP/1.1 200 Connection established\r\n\r\n"
                client_socket.send(connect_response.encode("utf-8"))
                print(f"  [OK] 已发送隧道建立响应给客户端")

                # 开始双向数据转发
                self._relay_data(client_socket, target_socket, host, port)

                # 返回None，表示隧道已建立并处理完成
                return None

            except socket.timeout:
                print(f"[ERROR] 连接超时: {host}:{port}")
                target_socket.close()
                return self.response_builder.create_error_response(
                    504, f"Gateway Timeout: Connection to {host}:{port} timed out"
                )
            except socket.error as e:
                print(f"[ERROR] 连接失败: {host}:{port} - {e}")
                target_socket.close()
                return self.response_builder.create_error_response(
                    502, f"Bad Gateway: Cannot connect to {host}:{port}"
                )
            except Exception as e:
                print(f"[ERROR] 连接异常: {host}:{port} - {e}")
                target_socket.close()
                return self.response_builder.create_error_response(
                    502, f"Bad Gateway: {str(e)}"
                )

        except Exception as e:
            print(f"[ERROR] 处理CONNECT请求时出错: {e}")
            return self.response_builder.create_error_response(
                500, f"Internal Server Error: {str(e)}"
            )

    def _relay_data(
        self,
        client_socket: socket.socket,
        target_socket: socket.socket,
        host: str,
        port: int,
    ) -> None:
        """
        在客户端和目标服务器之间双向转发数据

        这个方法会：
        1. 同时监听两个socket的数据
        2. 将从一个socket收到的数据转发到另一个socket
        3. 当任一连接关闭时，关闭所有连接

        Args:
            client_socket: 与客户端的socket连接
            target_socket: 与目标服务器的socket连接
            host: 目标主机（用于日志）
            port: 目标端口（用于日志）
        """
        print(f"  [SEND] 开始HTTPS隧道数据转发 ({host}:{port})")

        try:
            # 设置socket为非阻塞模式，这样可以使用select进行多路复用
            client_socket.setblocking(False)
            target_socket.setblocking(False)

            # 数据缓冲区大小
            BUFFER_SIZE = 4096

            # 使用select进行多路复用，同时监听两个socket
            while True:
                # 等待socket可读或可写
                readable, writable, exceptional = select.select(
                    [client_socket, target_socket],  # 可读的socket
                    [client_socket, target_socket],  # 可写的socket
                    [client_socket, target_socket],  # 异常的socket
                    1.0,  # 1秒超时
                )

                # 处理异常
                if exceptional:
                    print(f"  [ERROR] 隧道异常，关闭连接")
                    break

                # 处理可读的socket（有数据到达）
                for sock in readable:
                    try:
                        if sock == client_socket:
                            # 从客户端读取数据，转发到目标服务器
                            data = client_socket.recv(BUFFER_SIZE)
                            if not data:
                                print(f"  [SEND] 客户端关闭了连接")
                                return

                            # 直接转发到目标服务器（不解密HTTPS内容）
                            target_socket.send(data)
                            print(f"  [SEND] 转发客户端数据: {len(data)} 字节")

                        elif sock == target_socket:
                            # 从目标服务器读取数据，转发到客户端
                            data = target_socket.recv(BUFFER_SIZE)
                            if not data:
                                print(f"  [SEND] 目标服务器关闭了连接")
                                return

                            # 直接转发到客户端（不解密HTTPS内容）
                            client_socket.send(data)
                            print(f"  [RECV] 转发服务器数据: {len(data)} 字节")

                    except socket.error as e:
                        print(f"  [ERROR] 数据转发错误: {e}")
                        return
                    except Exception as e:
                        print(f"  [ERROR] 转发异常: {e}")
                        return

                # 如果没有数据可读，检查连接是否还活跃
                if not readable:
                    # 可以在这里添加心跳检测等逻辑
                    pass

        except KeyboardInterrupt:
            print(f"  [SEND] 用户中断，关闭隧道")
        except Exception as e:
            print(f"  [ERROR] 隧道转发异常: {e}")
        finally:
            # 关闭所有连接
            try:
                client_socket.close()
                target_socket.close()
                print(f"  [OK] HTTPS隧道已关闭 ({host}:{port})")
            except:
                pass
