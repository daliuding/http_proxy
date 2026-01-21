#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP请求解析器

负责解析HTTP请求的各个组成部分，包括请求行、头部和请求体。
"""

from urllib.parse import urlparse


class RequestParser:
    """HTTP请求解析器"""

    @staticmethod
    def parse(request_data: bytes) -> dict:
        """
        解析HTTP请求

        HTTP请求示例：
        GET /index.html HTTP/1.1\r\n
        Host: www.example.com\r\n
        User-Agent: Mozilla/5.0...\r\n
        \r\n
        [请求体，如果有]

        Args:
            request_data: 原始请求数据（bytes）

        Returns:
            dict: 解析后的请求信息字典，包含：
                - method: 请求方法（GET, POST等）
                - url: 请求URL
                - target_host: 目标主机（从Host头部获取）
                - path: URL路径
                - query: URL查询参数
                - http_version: HTTP协议版本
                - headers: 请求头部字典
                - body: 请求体
                - raw_request: 原始请求字符串
        """
        if not request_data:
            return {}

        try:
            # 将bytes转换为字符串
            request_str = request_data.decode("utf-8", errors="ignore")

            # 按\r\n分割成行
            lines = request_str.split("\r\n")

            if not lines:
                return {}

            # 1. 解析请求行（第一行）
            # 格式：METHOD URL HTTP/VERSION
            # 例如：GET /index.html?param=value HTTP/1.1
            request_line = lines[0]
            parts = request_line.split(" ", 2)  # 最多分割成3部分

            if len(parts) < 3:
                print(f"无效的请求行: {request_line}")
                return {}

            method = parts[0]  # GET, POST, PUT等
            url = parts[1]  # /index.html?param=value
            http_version = parts[2]  # HTTP/1.1

            # 2. 解析请求头部
            # 头部从第二行开始，直到遇到空行
            headers = {}
            body_start_index = 0

            for i, line in enumerate(lines[1:], start=1):
                if not line.strip():  # 空行表示头部结束
                    body_start_index = i + 1
                    break

                # 头部格式：Key: Value
                if ":" in line:
                    key, value = line.split(":", 1)  # 只分割第一个冒号
                    headers[key.strip()] = value.strip()

            # 3. 解析请求体（如果有）
            body = ""
            if body_start_index < len(lines):
                body = "\r\n".join(lines[body_start_index:])

            # 4. 解析URL
            # 使用urlparse解析URL，提取路径和查询参数
            parsed_url = urlparse(url)

            # 5. 获取目标主机
            # 优先从Host头部获取，如果没有则从URL中提取
            target_host = headers.get("Host", "")
            if not target_host and parsed_url.netloc:
                target_host = parsed_url.netloc

            # 返回解析结果
            return {
                "method": method,
                "url": url,
                "target_host": target_host,
                "path": parsed_url.path or "/",
                "query": parsed_url.query,
                "http_version": http_version,
                "headers": headers,
                "body": body,
                "raw_request": request_str,  # 保留原始请求字符串，方便调试
            }

        except Exception as e:
            print(f"解析请求时出错: {e}")
            return {}
