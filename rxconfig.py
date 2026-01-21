import reflex as rx  
import os  
config = rx.Config(  
    app_name="be_holmes",  
    # 禁用 Reflex 的自动 Vite 配置，使用我们的 vite.config.ts  
    frontend_packages=["reflex"],  
    # 设置环境变量来配置 Vite  
    env={  
        "VITE_ALLOWED_HOSTS": "beholmes.zeabur.app,localhost,127.0.0.1,.zeabur.app",  
    },  
)  
