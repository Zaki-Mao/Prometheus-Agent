FROM python:3.12-slim

WORKDIR /app

# 1. 安装系统依赖和 Node.js (保证编译成功)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 复制所有代码
COPY . .

# 4. 关键步骤：在构建时就编译好！(解决 502 超时问题)
RUN reflex export --frontend-only --no-zip

# 5. 暴露端口
EXPOSE 3000
EXPOSE 8000

# 6. 启动命令：
# 将目录指向 .web (而不是 _static)，这样我们至少能看到目录结构，保证不报错
CMD ["sh", "-c", "reflex run --env prod --backend-only & python3 -m http.server 3000 --directory .web"]
