# HTTP代理服务器

这是一个用Python编写的HTTP代理服务器，可以监听指定端口，接收HTTP请求并转发到目标服务器，同时记录所有请求到JSON文件。

## 功能特性

- ✅ 监听指定端口接收HTTP请求
- ✅ 解析并记录所有HTTP请求到JSON文件
- ✅ 记录详细的请求信息（方法、URL、头部、body等）
- ✅ 将HTTP请求转发到目标服务器
- ✅ 将目标服务器的响应返回给客户端
- ✅ 自动处理gzip压缩和chunked编码
- ✅ 错误处理和超时控制
- ✅ **支持HTTPS连接（CONNECT方法）**
- ✅ **建立HTTPS隧道，转发加密数据**
- ✅ **双向数据转发，支持客户端和服务器之间的加密通信**

## 环境要求

- Python >= 3.14
- [uv](https://github.com/astral-sh/uv) - 现代化的Python包管理工具

## 安装

### 1. 全局安装uv（如果尚未安装）

```bash
# Windows
python -m pip install --upgrade uv
```

### 2. 安装项目依赖

```bash
cd project-folder
uv sync
```
这一步，uv会自动创建 .venv/, 根据 pyproject.toml / uv.lock 安装完全一致的依赖版本。
注意：uv sync 是使用者、部署者安装依赖的方式，uv add是开发者修改依赖。

## 使用方法

### 使用uv运行脚本(默认激活venv环境)

```bash
cd project-folder
uv run proxy-server
```

### 默认配置

- 监听地址：127.0.0.1
- 监听端口：8888
- 日志文件：proxy_log.json

### 3. 配置浏览器代理

#### Chrome/Edge浏览器：
1. 打开设置 → 系统 → 打开计算机的代理设置
2. 在"手动代理设置"中：
   - 启用"使用代理服务器"
   - 地址：127.0.0.1
   - 端口：8888
   - 点击"保存"

#### Firefox浏览器：
1. 打开设置 → 网络设置
2. 选择"手动代理配置"
3. HTTP代理：127.0.0.1
4. 端口：8888
5. 点击"确定"

#### 使用 curl 测试代理（命令行方式）

除了配置浏览器，你也可以使用 curl 命令直接测试代理服务器：

```bash
# 基本 GET 请求测试
curl -x http://127.0.0.1:8888 http://httpbin.org/get

# 查看详细信息（包括请求和响应头）
curl -v -x http://127.0.0.1:8888 http://httpbin.org/get

# POST 请求测试（带 JSON 数据）
curl -x http://127.0.0.1:8888 -X POST http://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "value": 123}'

# 测试带自定义头部
curl -x http://127.0.0.1:8888 http://httpbin.org/headers \
  -H "User-Agent: MyTestAgent/1.0" \
  -H "X-Custom-Header: test-value"

# HTTPS 测试（使用 CONNECT 方法）
curl -x http://127.0.0.1:8888 https://httpbin.org/get

# HTTPS POST 请求测试
curl -x http://127.0.0.1:8888 -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "value": 123}'
```

**注意**：现在支持 HTTPS 和 HTTP 网站！推荐使用 `httpbin.org` 进行 HTTP 测试，使用 `https://httpbin.org` 进行 HTTPS 测试。

### 4. HTTPS测试示例

除了HTTP测试，现在也可以测试HTTPS网站。HTTPS请求使用CONNECT方法建立隧道，代理服务器会透明转发加密数据：

```bash
# 1. 基本HTTPS GET请求测试
curl -x http://127.0.0.1:8888 https://httpbin.org/get

# 2. 查看HTTPS请求详细信息（包括CONNECT隧道建立过程）
curl -v -x http://127.0.0.1:8888 https://httpbin.org/get

# 3. HTTPS POST请求测试（带JSON数据）
curl -x http://127.0.0.1:8888 -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "value": 123}'

# 4. HTTPS请求带查询参数
curl -x http://127.0.0.1:8888 "https://httpbin.org/get?key1=value1&key2=value2"

# 5. HTTPS请求带自定义头部
curl -x http://127.0.0.1:8888 https://httpbin.org/headers \
  -H "User-Agent: MyHTTPSAgent/1.0" \
  -H "X-Custom-Header: https-test-value" \
  -H "Authorization: Bearer test-token"

# 6. HTTPS PUT请求测试
curl -x http://127.0.0.1:8888 -X PUT https://httpbin.org/put \
  -H "Content-Type: application/json" \
  -d '{"update": "data"}'

# 7. HTTPS DELETE请求测试
curl -x http://127.0.0.1:8888 -X DELETE https://httpbin.org/delete

# 8. 测试访问百度HTTPS网站
curl -x http://127.0.0.1:8888 https://www.baidu.com

# 9. 测试访问GitHub API（HTTPS）
curl -x http://127.0.0.1:8888 https://api.github.com

# 10. HTTPS文件下载测试（保存到本地）
curl -x http://127.0.0.1:8888 https://httpbin.org/robots.txt -o robots.txt

# 11. 测试HTTPS重定向
curl -L -x http://127.0.0.1:8888 https://httpbin.org/redirect/3

# 12. HTTPS请求带表单数据
curl -x http://127.0.0.1:8888 -X POST https://httpbin.org/post \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=secret"
```

**HTTPS测试说明**：
- 所有HTTPS请求都会通过CONNECT方法建立隧道
- 代理服务器不会解密HTTPS内容，仅转发加密数据
- 如果遇到SSL证书验证错误，可以使用 `-k` 参数忽略证书验证（仅用于测试）
- 建议使用 `httpbin.org` 进行HTTPS功能测试，它提供了丰富的测试端点

### 5. 查看日志

所有HTTP和HTTPS请求都会被记录到 `proxy_log.json` 文件中，格式如下：

```json
[
  {
    "timestamp": "2024-01-01T12:00:00.123456",
    "client_address": "127.0.0.1:54321",
    "method": "GET",
    "url": "/",
    "target_host": "www.example.com",
    "path": "/",
    "query": "",
    "headers": {
      "Host": "www.example.com",
      "User-Agent": "Mozilla/5.0..."
    },
    "body": "",
    "body_length": 0
  }
]
```

## 工作原理

### HTTP请求处理流程
1. **监听端口**：服务器在指定端口上监听客户端连接
2. **接收请求**：接收来自浏览器的HTTP请求
3. **解析请求**：解析HTTP请求的方法、URL、头部和body
4. **记录日志**：将请求信息保存到JSON文件
5. **转发请求**：使用requests库将请求转发到目标服务器
6. **处理响应**：接收目标服务器的响应，自动处理压缩和编码
7. **返回响应**：将处理后的响应返回给客户端

### HTTPS请求处理流程
1. **监听端口**：服务器在指定端口上监听客户端连接
2. **接收CONNECT请求**：接收来自浏览器的CONNECT请求（格式：CONNECT host:port HTTP/1.1）
3. **建立隧道**：连接到目标HTTPS服务器
4. **发送隧道响应**：向客户端发送"200 Connection established"响应
5. **双向数据转发**：在客户端和目标服务器之间透明转发加密数据
6. **记录日志**：记录CONNECT请求的建立信息
7. **关闭隧道**：当任一端关闭连接时，关闭整个隧道

## 项目结构

```
proxy_practice/
├── proxy_server.py    # 代理服务器主程序（协调器）
├── handlers/          # 请求处理器模块
│   ├── __init__.py
│   ├── http_handler.py    # HTTP请求处理器
│   └── https_handler.py   # HTTPS请求处理器（CONNECT方法）
├── parsers/           # 请求解析模块
│   ├── __init__.py
│   └── request_parser.py  # HTTP请求解析器
├── builders/          # 响应构建模块
│   ├── __init__.py
│   └── response_builder.py # HTTP响应构建器
├── utils/             # 工具模块
│   ├── __init__.py
│   └── logger.py          # 请求日志记录器
├── pyproject.toml     # 项目配置文件（uv使用）
├── uv.lock           # 依赖锁定文件
├── proxy_log.json    # 请求日志文件（运行后自动生成）
└── README.md         # 项目说明文档
```

### 架构设计

项目采用模块化设计，将HTTP和HTTPS处理逻辑分离：

- **proxy_server.py**: 主服务器类，负责监听连接、协调各个模块
- **handlers/**: 请求处理器，分别处理HTTP和HTTPS请求
- **parsers/**: 请求解析器，负责解析HTTP请求的各个组成部分
- **builders/**: 响应构建器，负责构建HTTP响应
- **utils/**: 工具模块，包含日志记录等功能

这种设计遵循单一职责原则，使代码更易维护和扩展。

## 依赖说明

- **requests** (>=2.31.0): 用于转发HTTP请求到目标服务器

## 注意事项

- ✅ 现在支持HTTPS和HTTP请求
- ⚠️ 建议仅在本地网络环境中使用
- ⚠️ 日志文件会持续增长，请注意定期清理
- ⚠️ 代理会自动处理gzip压缩和chunked编码，确保响应正确传输
- ⚠️ 请求转发超时时间为30秒
- ⚠️ HTTPS隧道使用CONNECT方法，代理不解密HTTPS内容，仅转发加密数据

## 停止服务器

按 `Ctrl+C` 停止服务器

## 开发

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。所有依赖配置都在 `pyproject.toml` 文件中。

### 添加依赖

```bash
uv add <package-name>
```

### 移除依赖

```bash
uv remove <package-name>
```

### 更新依赖

```bash
uv sync --upgrade
```


