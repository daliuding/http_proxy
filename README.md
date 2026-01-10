# HTTP代理服务器

这是一个用Python编写的HTTP代理服务器，可以监听指定端口，记录所有HTTP请求到JSON文件。

## 功能特性

- ✅ 监听指定端口接收HTTP请求
- ✅ 解析并记录所有HTTP请求到JSON文件
- ✅ 记录详细的请求信息（方法、URL、头部、body等）

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

### 4. 查看日志

所有HTTP请求都会被记录到 `proxy_log.json` 文件中，格式如下：

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

1. **监听端口**：服务器在指定端口上监听客户端连接
2. **接收请求**：接收来自浏览器的HTTP请求
3. **解析请求**：解析HTTP请求的方法、URL、头部和body
4. **记录日志**：将请求信息保存到JSON文件

## 项目结构

```
proxy_practice/
├── proxy_server.py    # 代理服务器主程序
├── pyproject.toml     # 项目配置文件（uv使用）
├── uv.lock           # 依赖锁定文件
└── README.md         # 项目说明文档
```

## 注意事项

- ⚠️ 当前版本仅记录请求，暂不支持请求转发功能
- ⚠️ 当前版本对HTTPS（CONNECT方法）的支持有限
- ⚠️ 建议仅在本地网络环境中使用
- ⚠️ 日志文件会持续增长，请注意定期清理

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


