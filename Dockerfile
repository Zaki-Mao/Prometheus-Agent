FROM python:3.12-slim

WORKDIR /app

# 安装依赖
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 编译前端
RUN reflex export --frontend-only --no-zip

EXPOSE 3000
EXPOSE 8000

# 启动命令
CMD ["sh", "-c", "reflex run --env prod --backend-only & python3 -m http.server 3000 --directory .web/build/client"]
