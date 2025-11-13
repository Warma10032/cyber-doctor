# config_loader.py
import os
from typing import Any, Dict

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """从环境变量加载数据库配置"""
        self.config = {
            "DJANGO_DB_HOST": os.getenv("DJANGO_DB_HOST", "114.215.183.142"),
            "DJANGO_DB_PORT": int(os.getenv("DJANGO_DB_PORT", "3306")),
            "DJANGO_DB_USER": os.getenv("DJANGO_DB_USER", "root"),
            "DJANGO_DB_PASSWORD": os.getenv("DJANGO_DB_PASSWORD", "123456"),
            "DJANGO_DB_NAME": os.getenv("DJANGO_DB_NAME", "cyber_doctor"),
        }

    def get(self, key: str) -> Any:
        return self.config.get(key)

# 全局实例
config = Config()
