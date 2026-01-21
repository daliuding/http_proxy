#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
请求日志记录器

负责将HTTP请求信息记录到JSON文件。
"""

import json
from datetime import datetime
from typing import Dict, Tuple


class RequestLogger:
    """请求日志记录器"""

    def __init__(self, log_file: str = "proxy_log.json"):
        """
        初始化日志记录器

        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file

    def log(self, request_info: Dict, client_address: Tuple[str, int]) -> None:
        """
        将请求信息记录到JSON文件

        这个方法会：
        1. 读取现有的日志文件（如果存在）
        2. 将新请求添加到日志列表
        3. 保存回文件

        Args:
            request_info: 解析后的请求信息字典
            client_address: 客户端地址元组 (IP, 端口)
        """
        # 构建日志条目
        # 注意：我们只保存必要的信息，不保存原始请求字符串（可能很大）
        log_entry = {
            "timestamp": datetime.now().isoformat(),  # ISO格式的时间戳
            "client_address": f"{client_address[0]}:{client_address[1]}",  # 客户端IP:端口
            "method": request_info.get("method"),  # 请求方法
            "url": request_info.get("url"),  # 请求URL
            "target_host": request_info.get("target_host"),  # 目标主机
            "path": request_info.get("path"),  # URL路径
            "query": request_info.get("query"),  # 查询参数
            "http_version": request_info.get("http_version"),  # HTTP版本
            "headers": request_info.get("headers", {}),  # 请求头部
            "body": request_info.get("body", ""),  # 请求体
            "body_length": len(request_info.get("body", "")),  # 请求体长度（字节）
        }

        # 如果是CONNECT请求，添加额外信息
        if request_info.get("method") == "CONNECT":
            log_entry["tunnel_established"] = request_info.get(
                "tunnel_established", False
            )

        try:
            # 读取现有的日志文件
            # 如果文件不存在或格式错误，则创建一个空列表
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    # 确保logs是列表
                    if not isinstance(logs, list):
                        logs = []
            except FileNotFoundError:
                # 文件不存在，创建新列表
                logs = []
            except json.JSONDecodeError:
                # JSON格式错误，创建新列表
                print(f"警告：日志文件 {self.log_file} 格式错误，将创建新文件")
                logs = []

            # 添加新的日志条目
            logs.append(log_entry)

            # 将日志写回文件
            # ensure_ascii=False: 允许中文字符正常显示
            # indent=2: 格式化JSON，使其更易读
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            print(
                f"[OK] 已记录请求到 {self.log_file}: {request_info.get('method')} {request_info.get('url')}"
            )

        except Exception as e:
            print(f"[ERROR] 记录日志时出错: {e}")
