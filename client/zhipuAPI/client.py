try:
	from zhipuai import ZhipuAI  # requires zhipuai>=2.0.0
except Exception as exc:  # pragma: no cover
	raise ImportError(
		"zhipuai SDK not found or incompatible. Please install/upgrade with 'pip install -U \"zhipuai>=2.0.0\"'"
	) from exc

from env import get_env_value

Image_generate_client = ZhipuAI(api_key=get_env_value("IMAGE_GENERATE_API"))
Image_describe_client = ZhipuAI(api_key=get_env_value("IMAGE_DESCRIBE_API"))
Video_generate_client = ZhipuAI(api_key=get_env_value("VIDEO_GENERATE_API"))

