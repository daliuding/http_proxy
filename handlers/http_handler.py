#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP请求处理器

负责处理HTTP请求的转发和响应。
"""

import requests
from typing import Dict, Optional
from builders.response_builder import ResponseBuilder


class HTTPHandler:
    """HTTP请求处理器"""

    def __init__(self):
        """初始化HTTP处理器"""
        self.response_builder = ResponseBuilder()

    def handle(self, request_info: Dict) -> Optional[bytes]:
        """
        处理HTTP请求，转发到目标服务器并返回响应

        Args:
            request_info: 解析后的请求信息字典

        Returns:
            bytes: 目标服务器的响应数据（HTTP响应格式），如果出错则返回错误响应
        """
        try:
            method = request_info.get("method")
            url = request_info.get("url")
            headers = request_info.get("headers", {}).copy()
            body = request_info.get("body", "")
            target_host = request_info.get("target_host")

            # 检查是否有目标主机
            if not target_host:
                print("[ERROR] 错误：无法确定目标主机（缺少Host头部）")
                return self.response_builder.create_error_response(
                    400, "Bad Request: No Host header"
                )

            # 构建完整的URL
            # 如果URL已经是完整URL（以http://或https://开头），直接使用
            # 否则，使用Host头部构建完整URL
            if url.startswith("http://") or url.startswith("https://"):
                full_url = url
            else:
                # 通过代理访问时，URL通常是相对路径，需要加上协议和主机
                # 注意：这里只支持HTTP，HTTPS需要CONNECT隧道
                full_url = f"http://{target_host}{url}"

            print(f"[SEND] 转发请求: {method} {full_url}")

            # 移除一些不应该转发的代理相关头部
            # Connection: 控制连接行为，不应该转发
            # Proxy-Connection: 代理专用头部，不应该转发
            headers.pop("Connection", None)
            headers.pop("Proxy-Connection", None)
            headers.pop("Proxy-Authorization", None)  # 代理认证信息，不应该转发

            # 使用requests库转发请求
            # requests库会自动处理很多HTTP细节，比手动构建socket连接简单
            try:
                response = requests.request(
                    method=method,  # 请求方法（GET, POST等）
                    url=full_url,  # 完整URL
                    headers=headers,  # 请求头部
                    data=body if body else None,  # 请求体（如果有）
                    allow_redirects=False,  # 不自动跟随重定向（让客户端自己处理）
                    timeout=30,  # 30秒超时
                    stream=False,  # 不使用流式传输，直接获取完整响应
                )

                # 使用ResponseBuilder构建响应
                return self.response_builder.build_from_requests_response(response)

            except requests.exceptions.Timeout:
                print("[ERROR] 错误：请求超时")
                return self.response_builder.create_error_response(
                    504, "Gateway Timeout"
                )
            except requests.exceptions.ConnectionError:
                print(f"[ERROR] 错误：无法连接到目标服务器 {target_host}")
                return self.response_builder.create_error_response(
                    502, f"Bad Gateway: Cannot connect to {target_host}"
                )
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] 转发请求时出错: {e}")
                return self.response_builder.create_error_response(
                    502, f"Bad Gateway: {str(e)}"
                )

        except Exception as e:
            print(f"[ERROR] 处理请求时出错: {e}")
            return self.response_builder.create_error_response(
                500, f"Internal Server Error: {str(e)}"
            )
