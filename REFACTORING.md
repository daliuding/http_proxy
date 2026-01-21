# 重构说明文档

## 重构目标

将原本1229行的单一文件 `proxy_server.py` 重构为模块化结构，分离HTTP和HTTPS处理逻辑，提高代码的可维护性和可扩展性。

## 重构后的项目结构

```
proxy_practice_fix/
├── proxy_server.py          # 主服务器类（协调器，约300行）
├── handlers/                # 请求处理器模块
│   ├── __init__.py
│   ├── http_handler.py      # HTTP请求处理器（约100行）
│   └── https_handler.py     # HTTPS请求处理器（约200行）
├── parsers/                 # 请求解析模块
│   ├── __init__.py
│   └── request_parser.py     # HTTP请求解析器（约100行）
├── builders/                # 响应构建模块
│   ├── __init__.py
│   └── response_builder.py  # HTTP响应构建器（约200行）
└── utils/                   # 工具模块
    ├── __init__.py
    └── logger.py            # 请求日志记录器（约100行）
```

## 设计原则

### 1. 单一职责原则（SRP）
每个模块只负责一个明确的功能：
- `RequestParser`: 只负责解析HTTP请求
- `RequestLogger`: 只负责记录请求日志
- `HTTPHandler`: 只负责处理HTTP请求
- `HTTPSHandler`: 只负责处理HTTPS CONNECT请求
- `ResponseBuilder`: 只负责构建HTTP响应
- `ProxyServer`: 只负责协调各个模块，管理连接生命周期

### 2. 关注点分离
- **HTTP和HTTPS处理分离**: 两种协议的处理逻辑完全独立，互不干扰
- **解析与处理分离**: 请求解析和请求处理分开，便于测试和维护
- **构建与处理分离**: 响应构建逻辑独立，可以复用

### 3. 依赖注入
- `HTTPSHandler` 接收 `RequestLogger` 作为依赖，而不是直接创建
- 各模块通过接口交互，降低耦合度

## 模块说明

### proxy_server.py
主服务器类，负责：
- 监听客户端连接
- 接收完整的HTTP请求
- 协调各个模块处理请求
- 管理连接生命周期

### handlers/http_handler.py
HTTP请求处理器，负责：
- 转发HTTP请求到目标服务器
- 使用 `requests` 库处理HTTP请求
- 处理请求头部（移除代理相关头部）
- 返回HTTP响应

### handlers/https_handler.py
HTTPS请求处理器，负责：
- 处理CONNECT请求
- 建立到目标服务器的TCP连接
- 建立HTTPS隧道
- 双向转发加密数据（使用select多路复用）

### parsers/request_parser.py
请求解析器，负责：
- 解析HTTP请求行（方法、URL、版本）
- 解析HTTP请求头部
- 解析HTTP请求体
- 提取目标主机信息

### builders/response_builder.py
响应构建器，负责：
- 从 `requests.Response` 对象构建HTTP响应
- 处理编码相关头部（gzip、chunked等）
- 构建错误响应
- 确保响应格式符合HTTP标准

### utils/logger.py
日志记录器，负责：
- 将请求信息记录到JSON文件
- 处理日志文件的读取和写入
- 支持HTTP和HTTPS请求的日志记录

## 重构优势

### 1. 可维护性
- 每个文件职责单一，代码量适中（100-300行）
- 修改HTTP处理逻辑不会影响HTTPS处理
- 易于定位和修复问题

### 2. 可测试性
- 每个模块可以独立测试
- 可以轻松mock依赖进行单元测试
- 测试覆盖更容易

### 3. 可扩展性
- 添加新的协议支持（如SOCKS）只需添加新的handler
- 修改响应构建逻辑不影响其他模块
- 可以轻松添加新的功能模块

### 4. 代码复用
- `ResponseBuilder` 可以被多个handler复用
- `RequestParser` 可以被其他工具复用
- 模块化设计便于在其他项目中复用

## 使用方式

重构后的使用方式与之前完全相同：

```bash
uv run proxy-server
```

所有功能保持不变，只是内部实现更加模块化和清晰。

## 迁移说明

- ✅ 所有原有功能保持不变
- ✅ API接口保持不变（main函数）
- ✅ 日志格式保持不变
- ✅ 配置文件格式保持不变
- ✅ 依赖项保持不变

## 后续优化建议

1. **添加单元测试**: 为每个模块编写单元测试
2. **添加类型提示**: 使用完整的类型注解提高代码可读性
3. **添加配置管理**: 将配置项提取到独立的配置模块
4. **添加异常处理**: 完善异常处理机制，提供更详细的错误信息
5. **性能优化**: 考虑使用异步IO（asyncio）提高并发性能
