#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP代理服务器 - 第四步
添加将请求转发到目标服务器的功能

使用前请先安装依赖：
    pip install requests
    或
    uv sync
"""

import socket
import json
from datetime import datetime
from urllib.parse import urlparse
import requests


class ProxyServer:
    def __init__(self, host='127.0.0.1', port=8888, log_file='proxy_log.json'):
        """
        初始化代理服务器
        
        Args:
            host: 监听地址（127.0.0.1表示只监听本地，0.0.0.0表示监听所有网络接口）
            port: 监听端口
            log_file: 日志文件路径，用于保存所有请求记录
        """
        self.host = host
        self.port = port
        self.log_file = log_file
        self.socket = None
        
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
        
        print(f"代理服务器启动在 {self.host}:{self.port}")
        print(f"等待客户端连接...")
        print("按 Ctrl+C 停止服务器")
        
        try:
            # 无限循环，持续接受客户端连接
            while True:
                # accept() 会阻塞等待，直到有客户端连接
                # client_socket: 与客户端通信的socket对象
                # client_address: 客户端的地址元组 (IP, 端口)
                client_socket, client_address = self.socket.accept()
                
                print(f"收到来自 {client_address[0]}:{client_address[1]} 的连接")
                
                try:
                    # 接收完整的HTTP请求
                    request_data = self.receive_full_request(client_socket)
                    
                    if request_data:
                        # 解析HTTP请求
                        request_info = self.parse_request(request_data)
                        
                        if request_info:
                            # 打印解析结果
                            print("\n" + "="*50)
                            print("解析到的请求信息：")
                            print(f"  方法: {request_info.get('method')}")
                            print(f"  URL: {request_info.get('url')}")
                            print(f"  目标主机: {request_info.get('target_host')}")
                            print(f"  路径: {request_info.get('path')}")
                            print(f"  查询参数: {request_info.get('query')}")
                            print(f"  HTTP版本: {request_info.get('http_version')}")
                            print(f"  头部数量: {len(request_info.get('headers', {}))}")
                            if request_info.get('body'):
                                print(f"  请求体长度: {len(request_info.get('body'))} 字节")
                            print("="*50 + "\n")
                            
                            # 将请求记录到JSON文件
                            self.log_request(request_info, client_address)
                            
                            # 转发请求到目标服务器
                            response_data = self.forward_request(request_info)
                            
                            # 将响应发送回客户端
                            # 注意：socket.send()可能不会一次性发送所有数据
                            # 需要循环发送直到所有数据都发送完毕
                            if response_data:
                                # #region agent log
                                # 记录实际发送的响应数据的前200字节（用于检查格式）
                                header_part = response_data[:200]
                                header_part_hex = header_part.hex()
                                header_part_repr = repr(header_part)
                                log_data = {
                                    "sessionId": "debug-session",
                                    "runId": "run1",
                                    "hypothesisId": "G",
                                    "location": "proxy_server.py:97",
                                    "message": "实际发送的响应数据（前200字节）",
                                    "data": {
                                        "total_length": len(response_data),
                                        "header_part_hex": header_part_hex,
                                        "header_part_repr": header_part_repr,
                                        "header_part_text": header_part.decode('utf-8', errors='replace')[:200]
                                    },
                                    "timestamp": int(datetime.now().timestamp() * 1000)
                                }
                                try:
                                    with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                                except:
                                    pass
                                # #endregion
                                
                                total_sent = 0
                                while total_sent < len(response_data):
                                    sent = client_socket.send(response_data[total_sent:])
                                    if sent == 0:
                                        raise RuntimeError("Socket connection broken")
                                    total_sent += sent
                                print(f"✓ 已转发响应给客户端 ({total_sent} 字节)")
                            else:
                                print("✗ 未能获取响应")
                        else:
                            print("无法解析请求")
                            # 发送错误响应
                            error_response = self.create_error_response(400, "Bad Request: Unable to parse request")
                            client_socket.send(error_response)
                    else:
                        print("未收到请求数据")
                        
                except Exception as e:
                    print(f"处理请求时出错: {e}")
                finally:
                    # 关闭客户端连接
                    # 注意：对于HTTP/1.1，如果响应头部有Connection: close，应该关闭连接
                    # 对于HTTP/1.0，默认关闭连接
                    try:
                        client_socket.close()
                    except:
                        pass
                    print(f"已关闭与 {client_address} 的连接\n")
                    
        except KeyboardInterrupt:
            print("\n正在关闭服务器...")
            self.stop()
    
    def stop(self):
        """停止代理服务器"""
        if self.socket:
            self.socket.close()
            print("服务器已关闭")
    
    def receive_full_request(self, client_socket):
        """
        接收完整的HTTP请求
        
        HTTP请求格式：
        - 请求行（方法 URL 协议版本）
        - 请求头部（每行一个键值对）
        - 空行（\r\n\r\n）
        - 请求体（可选，如果有Content-Length头部）
        
        Returns:
            bytes: 完整的请求数据
        """
        request_data = b''
        client_socket.settimeout(30)  # 设置30秒超时
        
        try:
            # 循环接收数据，直到收到完整的请求
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                
                # 检查是否已经收到请求头部（头部以\r\n\r\n结束）
                if b'\r\n\r\n' in request_data:
                    # 分离头部和body
                    headers_end = request_data.find(b'\r\n\r\n')
                    headers_data = request_data[:headers_end]
                    
                    # 尝试解析Content-Length头部
                    headers_text = headers_data.decode('utf-8', errors='ignore')
                    content_length = 0
                    
                    for line in headers_text.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            try:
                                content_length = int(line.split(':', 1)[1].strip())
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
            return b''
        except Exception as e:
            print(f"接收请求时出错: {e}")
            return b''
    
    def parse_request(self, request_data):
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
        """
        if not request_data:
            return {}
        
        try:
            # 将bytes转换为字符串
            request_str = request_data.decode('utf-8', errors='ignore')
            
            # 按\r\n分割成行
            lines = request_str.split('\r\n')
            
            if not lines:
                return {}
            
            # 1. 解析请求行（第一行）
            # 格式：METHOD URL HTTP/VERSION
            # 例如：GET /index.html?param=value HTTP/1.1
            request_line = lines[0]
            parts = request_line.split(' ', 2)  # 最多分割成3部分
            
            if len(parts) < 3:
                print(f"无效的请求行: {request_line}")
                return {}
            
            method = parts[0]      # GET, POST, PUT等
            url = parts[1]         # /index.html?param=value
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
                if ':' in line:
                    key, value = line.split(':', 1)  # 只分割第一个冒号
                    headers[key.strip()] = value.strip()
            
            # 3. 解析请求体（如果有）
            body = ''
            if body_start_index < len(lines):
                body = '\r\n'.join(lines[body_start_index:])
            
            # 4. 解析URL
            # 使用urlparse解析URL，提取路径和查询参数
            parsed_url = urlparse(url)
            
            # 5. 获取目标主机
            # 优先从Host头部获取，如果没有则从URL中提取
            target_host = headers.get('Host', '')
            if not target_host and parsed_url.netloc:
                target_host = parsed_url.netloc
            
            # 返回解析结果
            return {
                'method': method,
                'url': url,
                'target_host': target_host,
                'path': parsed_url.path or '/',
                'query': parsed_url.query,
                'http_version': http_version,
                'headers': headers,
                'body': body,
                'raw_request': request_str  # 保留原始请求字符串，方便调试
            }
            
        except Exception as e:
            print(f"解析请求时出错: {e}")
            return {}
    
    def log_request(self, request_info, client_address):
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
            'timestamp': datetime.now().isoformat(),  # ISO格式的时间戳
            'client_address': f"{client_address[0]}:{client_address[1]}",  # 客户端IP:端口
            'method': request_info.get('method'),  # 请求方法
            'url': request_info.get('url'),  # 请求URL
            'target_host': request_info.get('target_host'),  # 目标主机
            'path': request_info.get('path'),  # URL路径
            'query': request_info.get('query'),  # 查询参数
            'http_version': request_info.get('http_version'),  # HTTP版本
            'headers': request_info.get('headers', {}),  # 请求头部
            'body': request_info.get('body', ''),  # 请求体
            'body_length': len(request_info.get('body', ''))  # 请求体长度（字节）
        }
        
        try:
            # 读取现有的日志文件
            # 如果文件不存在或格式错误，则创建一个空列表
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
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
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 已记录请求到 {self.log_file}: {request_info.get('method')} {request_info.get('url')}")
            
        except Exception as e:
            print(f"✗ 记录日志时出错: {e}")
    
    def forward_request(self, request_info):
        """
        将HTTP请求转发到目标服务器
        
        代理服务器的工作流程：
        1. 接收客户端请求
        2. 解析请求，获取目标服务器地址
        3. 将请求转发到目标服务器
        4. 接收目标服务器的响应
        5. 将响应返回给客户端
        
        Args:
            request_info: 解析后的请求信息字典
            
        Returns:
            bytes: 目标服务器的响应数据（HTTP响应格式）
        """
        try:
            method = request_info.get('method')
            url = request_info.get('url')
            headers = request_info.get('headers', {}).copy()
            body = request_info.get('body', '')
            target_host = request_info.get('target_host')
            
            # 检查是否有目标主机
            if not target_host:
                print("✗ 错误：无法确定目标主机（缺少Host头部）")
                return self.create_error_response(400, "Bad Request: No Host header")
            
            # 处理CONNECT方法（用于HTTPS隧道，暂时不支持）
            if method == 'CONNECT':
                print("⚠ 警告：收到CONNECT请求（HTTPS隧道），暂不支持")
                return self.create_error_response(501, "Not Implemented: HTTPS tunneling not supported")
            
            # 构建完整的URL
            # 如果URL已经是完整URL（以http://或https://开头），直接使用
            # 否则，使用Host头部构建完整URL
            if url.startswith('http://') or url.startswith('https://'):
                full_url = url
            else:
                # 通过代理访问时，URL通常是相对路径，需要加上协议和主机
                # 注意：这里暂时只支持HTTP，HTTPS需要CONNECT隧道
                full_url = f"http://{target_host}{url}"
            
            print(f"→ 转发请求: {method} {full_url}")
            
            # 移除一些不应该转发的代理相关头部
            # Connection: 控制连接行为，不应该转发
            # Proxy-Connection: 代理专用头部，不应该转发
            headers.pop('Connection', None)
            headers.pop('Proxy-Connection', None)
            headers.pop('Proxy-Authorization', None)  # 代理认证信息，不应该转发
            
            # 使用requests库转发请求
            # requests库会自动处理很多HTTP细节，比手动构建socket连接简单
            try:
                response = requests.request(
                    method=method,           # 请求方法（GET, POST等）
                    url=full_url,           # 完整URL
                    headers=headers,         # 请求头部
                    data=body if body else None,  # 请求体（如果有）
                    allow_redirects=False,  # 不自动跟随重定向（让客户端自己处理）
                    timeout=30,             # 30秒超时
                    stream=False            # 不使用流式传输，直接获取完整响应
                )
                
                # 构建HTTP响应
                # HTTP响应格式：
                # HTTP/1.1 200 OK\r\n
                # Header1: Value1\r\n
                # Header2: Value2\r\n
                # \r\n
                # [响应体]
                
                response_headers = []
                # 状态行：HTTP版本 状态码 状态文本
                # 清理reason中的换行符和特殊字符
                reason = response.reason if response.reason else "OK"
                reason = reason.replace('\r', '').replace('\n', '')
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
                has_content_length = False
                has_content_encoding_gzip = False
                content_length_value = len(response.content)  # 实际body大小（已解压）
                
                # 调试信息
                print(f"  调试：response.content长度 = {content_length_value} 字节")
                print(f"  调试：response.headers中的Content-Length = {response.headers.get('Content-Length', 'N/A')}")
                print(f"  调试：response.headers中的Content-Encoding = {response.headers.get('Content-Encoding', 'N/A')}")
                print(f"  调试：response.raw.headers中的Content-Length = {response.raw.headers.get('Content-Length', 'N/A')}")
                print(f"  调试：response.raw.headers中的Content-Encoding = {response.raw.headers.get('Content-Encoding', 'N/A')}")
                
                # 先检查是否有gzip编码
                for key, value in list(response.headers.items()):
                    key_str_check = str(key).strip().lower()
                    if key_str_check == 'content-encoding':
                        encoding_value = str(value).strip().lower()
                        if 'gzip' in encoding_value or 'deflate' in encoding_value:
                            has_content_encoding_gzip = True
                            break
                
                for key, value in response.headers.items():
                    # 确保key和value都是字符串
                    original_key = str(key).strip()
                    key_str = original_key.lower()  # 转换为小写以便比较
                    value_str = str(value).strip()
                    
                    # #region agent log
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "proxy_server.py:467",
                        "message": "处理响应头部",
                        "data": {
                            "original_key": original_key,
                            "key_str": key_str,
                            "value_str": value_str[:100] if len(value_str) > 100 else value_str,
                            "has_colon_in_value": ':' in value_str
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                    # #endregion
                    
                    # 跳过空的key
                    if not key_str:
                        continue
                    
                    # 跳过Transfer-Encoding头部（因为我们已经解码了chunked编码）
                    if key_str == 'transfer-encoding':
                        continue
                    
                    # 跳过Content-Encoding头部（如果已解压，如gzip）
                    # requests库会自动解压gzip，所以我们需要移除这个头部
                    if key_str == 'content-encoding':
                        encoding_value = value_str.lower()
                        # 如果已解压（requests自动解压），移除这个头部
                        if 'gzip' in encoding_value or 'deflate' in encoding_value:
                            print(f"  跳过Content-Encoding头部（已自动解压）: {original_key}")
                            continue
                    
                    # 记录是否有Content-Length头部，并更新为实际body大小
                    if key_str == 'content-length':
                        has_content_length = True
                        # 重要：无论什么情况，都更新Content-Length为实际body大小
                        # 因为如果原来是gzip压缩的，Content-Length是压缩后的大小
                        # 但response.content已经是解压后的内容了
                        old_value = value_str
                        value_str = str(content_length_value)
                        if old_value != value_str:
                            print(f"  更新Content-Length: {old_value} -> {value_str} (body实际大小)")
                        else:
                            print(f"  Content-Length已正确: {value_str}")
                    
                    # 移除值中的换行符（HTTP规范不允许）
                    value_str = value_str.replace('\r', ' ').replace('\n', ' ')
                    
                    # 构建头部行：Key: Value
                    header_line = f"{original_key}: {value_str}"
                    # #region agent log
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "E",
                        "location": "proxy_server.py:507",
                        "message": "添加头部行",
                        "data": {
                            "header_line": header_line,
                            "has_colon": ':' in header_line,
                            "is_valid_format": ':' in header_line and header_line.split(':', 1)[0].strip() != ''
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                    # #endregion
                    response_headers.append(header_line)
                
                # 强制设置Content-Length为实际body大小
                # 无论原来是否有Content-Length头部，都确保它是正确的
                # 因为如果原来是gzip压缩的，Content-Length是压缩后的大小
                # 但response.content已经是解压后的内容了
                if content_length_value > 0:
                    # #region agent log
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "F",
                        "location": "proxy_server.py:513",
                        "message": "删除Content-Length前的头部列表",
                        "data": {
                            "headers_before": response_headers[:15],
                            "headers_count": len(response_headers)
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                    # #endregion
                    
                    # 删除所有现有的Content-Length头部（可能有多个或错误的值）
                    response_headers = [h for h in response_headers if not h.lower().startswith('content-length:')]
                    
                    # #region agent log
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "F",
                        "location": "proxy_server.py:515",
                        "message": "删除Content-Length后的头部列表",
                        "data": {
                            "headers_after": response_headers[:15],
                            "headers_count": len(response_headers)
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                    # #endregion
                    
                    # 在空行之前插入正确的Content-Length头部
                    # 找到空行的位置（如果还没有空行，会在后面添加）
                    empty_line_idx = -1
                    for i, header_line in enumerate(response_headers):
                        if not header_line.strip():
                            empty_line_idx = i
                            break
                    
                    if empty_line_idx > 0:
                        response_headers.insert(empty_line_idx, f"Content-Length: {content_length_value}")
                    else:
                        # 如果没有空行，在最后添加（空行会在后面添加）
                        response_headers.append(f"Content-Length: {content_length_value}")
                    
                    print(f"  强制设置Content-Length头部为: {content_length_value} 字节")
                
                # 空行分隔头部和body
                response_headers.append("")
                
                # 组合响应：头部 + 空行 + body
                # 使用 \r\n 作为行分隔符（HTTP标准要求）
                # #region agent log
                import json
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "proxy_server.py:538",
                    "message": "响应头部列表内容（删除Content-Length后）",
                    "data": {
                        "headers_count": len(response_headers),
                        "headers": response_headers[:20]  # 只记录前20行
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                try:
                    with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                
                # #region agent log
                # 检查是否有格式错误的头部行（没有冒号且不是空行）
                invalid_headers = []
                for i, h in enumerate(response_headers):
                    if h.strip() and ':' not in h and not h.strip().startswith('HTTP/'):
                        invalid_headers.append({"index": i, "line": h})
                if invalid_headers:
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "proxy_server.py:555",
                        "message": "发现格式错误的头部行（没有冒号）",
                        "data": {"invalid_headers": invalid_headers},
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                # #endregion
                
                response_header_text = '\r\n'.join(response_headers)
                # 确保头部以 \r\n\r\n 结尾（HTTP标准要求）
                # join() 不会在最后添加分隔符，所以需要手动添加 \r\n
                if not response_header_text.endswith('\r\n\r\n'):
                    # 如果最后不是 \r\n\r\n，添加它
                    if response_header_text.endswith('\r\n'):
                        # 如果最后是 \r\n，再添加一个 \r\n
                        response_header_text += '\r\n'
                    else:
                        # 如果最后不是 \r\n，添加 \r\n\r\n
                        response_header_text += '\r\n\r\n'
                
                # #region agent log
                # 逐行检查响应头部文本，确保每行都有正确的格式
                header_lines_check = response_header_text.split('\r\n')
                problematic_lines = []
                for i, line in enumerate(header_lines_check):
                    # 检查：非空行必须要么是状态行（HTTP/开头），要么包含冒号
                    if line.strip():
                        if not line.strip().startswith('HTTP/') and ':' not in line:
                            problematic_lines.append({"line_num": i+1, "line": line, "line_hex": line.encode('utf-8').hex()})
                if problematic_lines:
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "I",
                        "location": "proxy_server.py:691",
                        "message": "发现格式有问题的头部行",
                        "data": {"problematic_lines": problematic_lines},
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                # #endregion
                
                header_bytes = response_header_text.encode('utf-8')
                
                # #region agent log
                # 验证修复后的头部格式
                header_ends_correctly = header_bytes.endswith(b'\r\n\r\n')
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "post-fix",
                    "hypothesisId": "L",
                    "location": "proxy_server.py:730",
                    "message": "修复后验证头部格式",
                    "data": {
                        "header_bytes_length": len(header_bytes),
                        "header_ends_with_double_crlf": header_ends_correctly,
                        "header_last_20_bytes_hex": header_bytes[-20:].hex() if len(header_bytes) >= 20 else header_bytes.hex(),
                        "header_last_20_bytes_text": header_bytes[-20:].decode('utf-8', errors='replace') if len(header_bytes) >= 20 else header_bytes.decode('utf-8', errors='replace')
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                try:
                    with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                
                body_bytes = response.content
                
                # #region agent log
                # 检查body的开头部分，看是否包含可能被误认为是头部的字符串
                body_start = body_bytes[:50] if len(body_bytes) > 50 else body_bytes
                body_start_text = body_start.decode('utf-8', errors='replace')
                # 检查body开头是否包含"@uv"或类似可能被误认为是头部的字符串
                if b'@uv' in body_start or '@uv' in body_start_text:
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "J",
                        "location": "proxy_server.py:694",
                        "message": "body开头包含@uv字符串",
                        "data": {
                            "body_start_hex": body_start.hex(),
                            "body_start_text": body_start_text,
                            "body_start_repr": repr(body_start)
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    try:
                        with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    except:
                        pass
                # 检查头部和body之间的分隔是否正确
                # 头部应该以\r\n\r\n结尾（空行分隔）
                header_ends_with_double_crlf = header_bytes.endswith(b'\r\n\r\n')
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "K",
                    "location": "proxy_server.py:694",
                    "message": "检查头部和body之间的分隔",
                    "data": {
                        "header_bytes_length": len(header_bytes),
                        "header_ends_with_double_crlf": header_ends_with_double_crlf,
                        "header_last_10_bytes_hex": header_bytes[-10:].hex() if len(header_bytes) >= 10 else header_bytes.hex(),
                        "body_first_10_bytes_hex": body_start[:10].hex() if len(body_start) >= 10 else body_start.hex(),
                        "body_first_10_bytes_text": body_start[:10].decode('utf-8', errors='replace') if len(body_start) >= 10 else body_start_text
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                try:
                    with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                
                response_data = header_bytes + body_bytes
                
                # #region agent log
                # 记录最终响应头部文本的前几行（用于检查格式）
                header_lines = response_header_text.split('\r\n')[:15]
                # 检查头部字节中第118-137字节位置的内容（curl报错位置）
                header_bytes_118_137 = header_bytes[118:137] if len(header_bytes) > 118 else b''
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "proxy_server.py:691",
                    "message": "最终响应头部文本（前15行）",
                    "data": {
                        "header_lines": header_lines,
                        "header_bytes_length": len(header_bytes),
                        "header_bytes_118_137_hex": header_bytes_118_137.hex(),
                        "header_bytes_118_137_repr": repr(header_bytes_118_137),
                        "header_bytes_118_137_text": header_bytes_118_137.decode('utf-8', errors='replace')
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                try:
                    with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                
                # #region agent log
                # 检查响应数据中第118-137字节位置的内容（curl报错位置）
                response_data_118_137 = response_data[118:137] if len(response_data) > 118 else b''
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H",
                    "location": "proxy_server.py:694",
                    "message": "完整响应数据中第118-137字节位置（curl报错位置）",
                    "data": {
                        "response_data_length": len(response_data),
                        "response_data_118_137_hex": response_data_118_137.hex(),
                        "response_data_118_137_repr": repr(response_data_118_137),
                        "response_data_118_137_text": response_data_118_137.decode('utf-8', errors='replace'),
                        "is_in_header": len(header_bytes) > 137,
                        "is_in_body": len(header_bytes) <= 118
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                try:
                    with open('.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                
                # 调试信息
                print(f"  调试：响应头部大小 = {len(header_bytes)} 字节")
                print(f"  调试：响应体大小 = {len(body_bytes)} 字节")
                print(f"  调试：总响应大小 = {len(response_data)} 字节")
                
                # 调试：打印响应头部信息（用于排查问题）
                if len(response_headers) > 0:
                    debug_lines = response_headers[:min(5, len(response_headers))]
                    print(f"✓ 收到响应: {response.status_code} {reason}")
                    print(f"  响应头部（前{len(debug_lines)}行）: {debug_lines}")
                    # 查找Content-Length头部
                    for line in response_headers:
                        if line.lower().startswith('content-length:'):
                            print(f"  最终Content-Length头部: {line}")
                            break
                
                return response_data
                
            except requests.exceptions.Timeout:
                print("✗ 错误：请求超时")
                return self.create_error_response(504, "Gateway Timeout")
            except requests.exceptions.ConnectionError:
                print(f"✗ 错误：无法连接到目标服务器 {target_host}")
                return self.create_error_response(502, f"Bad Gateway: Cannot connect to {target_host}")
            except requests.exceptions.RequestException as e:
                print(f"✗ 转发请求时出错: {e}")
                return self.create_error_response(502, f"Bad Gateway: {str(e)}")
                
        except Exception as e:
            print(f"✗ 处理请求时出错: {e}")
            return self.create_error_response(500, f"Internal Server Error: {str(e)}")
    
    def create_error_response(self, status_code, message):
        """
        创建HTTP错误响应
        
        Args:
            status_code: HTTP状态码（如400, 500等）
            message: 错误消息
            
        Returns:
            bytes: 编码后的错误响应
        """
        # 构建错误响应体
        body = message.encode('utf-8')
        
        # 构建响应头部
        response_headers = [
            f"HTTP/1.1 {status_code} {message}",
            "Content-Type: text/plain; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
            ""  # 空行
        ]
        
        # 组合响应
        response = '\r\n'.join(response_headers).encode('utf-8') + body
        return response


def main():
    """主函数"""
    # 创建代理服务器实例
    # log_file参数指定日志文件路径，默认为 'proxy_log.json'
    proxy = ProxyServer(host='127.0.0.1', port=8888, log_file='proxy_log.json')
    
    print(f"日志将保存到: {proxy.log_file}")
    print()
    
    # 启动服务器
    proxy.start()


if __name__ == '__main__':
    main()

