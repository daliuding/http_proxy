#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP响应构建器

负责构建HTTP响应，包括错误响应和正常响应。
"""


class ResponseBuilder:
    """HTTP响应构建器"""

    @staticmethod
    def create_error_response(status_code: int, message: str) -> bytes:
        """
        创建HTTP错误响应

        Args:
            status_code: HTTP状态码（如400, 500等）
            message: 错误消息

        Returns:
            bytes: 编码后的错误响应
        """
        # 构建错误响应体
        body = message.encode("utf-8")

        # 构建响应头部
        response_headers = [
            f"HTTP/1.1 {status_code} {message}",
            "Content-Type: text/plain; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
            "",  # 空行
        ]

        # 组合响应
        response = "\r\n".join(response_headers).encode("utf-8") + body
        return response

    @staticmethod
    def build_from_requests_response(response) -> bytes:
        """
        从requests库的Response对象构建HTTP响应

        Args:
            response: requests.Response对象

        Returns:
            bytes: 编码后的HTTP响应
        """
        response_headers = []
        # 状态行：HTTP版本 状态码 状态文本
        # 清理reason中的换行符和特殊字符
        reason = response.reason if response.reason else "OK"
        reason = reason.replace("\r", "").replace("\n", "")
        response_headers.append(f"HTTP/1.1 {response.status_code} {reason}")

        # 添加所有响应头部
        # 确保头部格式正确：Key: Value
        # 清理头部值中的换行符（HTTP头部值不应该包含换行符）

        # 重要：处理编码相关的头部
        # requests库已经自动解码了chunked编码和gzip压缩
        # 所以response.content是完整的、解压后的body
        # 我们需要：
        # 1. 移除Transfer-Encoding头部
        # 2. 移除Content-Encoding头部（如果已解压）
        # 3. 更新Content-Length为实际body大小
        content_length_value = len(response.content)  # 实际body大小（已解压）

        # 先检查是否有gzip编码
        has_content_encoding_gzip = False
        for key, value in list(response.headers.items()):
            key_str_check = str(key).strip().lower()
            if key_str_check == "content-encoding":
                encoding_value = str(value).strip().lower()
                if "gzip" in encoding_value or "deflate" in encoding_value:
                    has_content_encoding_gzip = True
                    break

        for key, value in response.headers.items():
            # 确保key和value都是字符串
            original_key = str(key).strip()
            key_str = original_key.lower()  # 转换为小写以便比较
            value_str = str(value).strip()

            # 跳过空的key
            if not key_str:
                continue

            # 跳过Transfer-Encoding头部（因为我们已经解码了chunked编码）
            if key_str == "transfer-encoding":
                continue

            # 跳过Content-Encoding头部（如果已解压，如gzip）
            # requests库会自动解压gzip，所以我们需要移除这个头部
            if key_str == "content-encoding":
                encoding_value = value_str.lower()
                # 如果已解压（requests自动解压），移除这个头部
                if "gzip" in encoding_value or "deflate" in encoding_value:
                    print(
                        f"  跳过Content-Encoding头部（已自动解压）: {original_key}"
                    )
                    continue

            # 记录是否有Content-Length头部，并更新为实际body大小
            if key_str == "content-length":
                old_value = value_str
                value_str = str(content_length_value)
                if old_value != value_str:
                    print(
                        f"  更新Content-Length: {old_value} -> {value_str} (body实际大小)"
                    )
                else:
                    print(f"  Content-Length已正确: {value_str}")

            # 移除值中的换行符（HTTP规范不允许）
            value_str = value_str.replace("\r", " ").replace("\n", " ")

            # 构建头部行：Key: Value
            header_line = f"{original_key}: {value_str}"
            response_headers.append(header_line)

        # 强制设置Content-Length为实际body大小
        # 无论原来是否有Content-Length头部，都确保它是正确的
        if content_length_value > 0:
            # 删除所有现有的Content-Length头部（可能有多个或错误的值）
            response_headers = [
                h
                for h in response_headers
                if not h.lower().startswith("content-length:")
            ]

            # 在空行之前插入正确的Content-Length头部
            # 找到空行的位置（如果还没有空行，会在后面添加）
            empty_line_idx = -1
            for i, header_line in enumerate(response_headers):
                if not header_line.strip():
                    empty_line_idx = i
                    break

            if empty_line_idx > 0:
                response_headers.insert(
                    empty_line_idx, f"Content-Length: {content_length_value}"
                )
            else:
                # 如果没有空行，在最后添加（空行会在后面添加）
                response_headers.append(f"Content-Length: {content_length_value}")

            print(
                f"  强制设置Content-Length头部为: {content_length_value} 字节"
            )

        # 空行分隔头部和body
        response_headers.append("")

        # 组合响应：头部 + 空行 + body
        # 使用 \r\n 作为行分隔符（HTTP标准要求）
        response_header_text = "\r\n".join(response_headers)
        # 确保头部以 \r\n\r\n 结尾（HTTP标准要求）
        # join() 不会在最后添加分隔符，所以需要手动添加 \r\n
        if not response_header_text.endswith("\r\n\r\n"):
            # 如果最后不是 \r\n\r\n，添加它
            if response_header_text.endswith("\r\n"):
                # 如果最后是 \r\n，再添加一个 \r\n
                response_header_text += "\r\n"
            else:
                # 如果最后不是 \r\n，添加 \r\n\r\n
                response_header_text += "\r\n\r\n"

        header_bytes = response_header_text.encode("utf-8")
        body_bytes = response.content

        response_data = header_bytes + body_bytes

        # 调试信息
        print(f"  调试：响应头部大小 = {len(header_bytes)} 字节")
        print(f"  调试：响应体大小 = {len(body_bytes)} 字节")
        print(f"  调试：总响应大小 = {len(response_data)} 字节")

        # 调试：打印响应头部信息（用于排查问题）
        if len(response_headers) > 0:
            debug_lines = response_headers[: min(5, len(response_headers))]
            print(f"[OK] 收到响应: {response.status_code} {reason}")
            print(f"  响应头部（前{len(debug_lines)}行）: {debug_lines}")
            # 查找Content-Length头部
            for line in response_headers:
                if line.lower().startswith("content-length:"):
                    print(f"  最终Content-Length头部: {line}")
                    break

        return response_data
