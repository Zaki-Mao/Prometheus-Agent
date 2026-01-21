import reflex as rx

config = rx.Config(
    app_name="be_holmes",
    
    # 1. 允许的前端访问域名 (解决 Blocked request 报错)
    # 这里的 '*' 代表允许所有域名，或者你可以写 ["https://beholmes.zeabur.app"]
    cors_allowed_origins=["*"],
    
    # 2. 告诉前端去哪里找后端 (解决 502/连接失败)
    # 生产环境下，API 地址就是你的域名本身
    api_url="https://beholmes.zeabur.app",
    
    # 3. 部署相关配置
    deploy_url="https://beholmes.zeabur.app",
)
