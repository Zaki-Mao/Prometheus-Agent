import reflex as rx  
config = rx.Config(  
    app_name="be_holmes",  
      
    # 允许所有域名的 CORS 请求  
    cors_allowed_origins=["*"],  
      
    # 关键修改：使用相同的域名  
    # 前端会自动添加 /api 路径来访问后端  
    api_url="https://beholmes.zeabur.app",  
      
    # 部署相关配置  
    deploy_url="https://beholmes.zeabur.app",  
)  
