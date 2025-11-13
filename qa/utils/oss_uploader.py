# utils/oss_uploader.py
import os
import oss2
from PIL import Image
import io
import uuid

# 从环境变量读取配置（更安全）
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "YOUR_ID")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "YOUR_KEY")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "YOUR_ENDPOINT")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "YOUR_BUCKET_NAME")

def upload_image_to_oss(image_path: str) -> str | None:
    """
    上传本地图片到 OSS，返回公网 URL
    """
    try:
        # 初始化 OSS 客户端
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
        
        # 生成唯一文件名（避免冲突）
        ext = os.path.splitext(image_path)[1].lower() or '.jpg'
        unique_name = f"gradio_uploads/{uuid.uuid4().hex}{ext}"
        
        # 读取图片
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 上传到 OSS
        bucket.put_object(unique_name, image_data)
        
        # 生成公网 URL
        # 注意：endpoint 要去掉 https:// 前缀
        endpoint_domain = OSS_ENDPOINT.replace("https://", "").replace("http://", "")
        public_url = f"https://{OSS_BUCKET_NAME}.{endpoint_domain}/{unique_name}"
        
        print(f"✅ Uploaded to OSS: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"❌ OSS upload failed for {image_path}: {e}")
        return None
