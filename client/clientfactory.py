'''向外部构建不同大模型代理的接口，构建完成后返回一个大模型代理'''
from client.ourAPI.client import OurAPI
from client.zhipuAPI.client import Image_generate_client, Image_describe_client
from client.zhipuAPI.client import Video_generate_client
from env import get_env_value
from qa.purpose_type import userPurposeType


class Clientfactory:
    # 初始化client字典，使用环境变量中的LLM_BASE_URL
    map_client_dict = {get_env_value("LLM_BASE_URL")}

    # 初始化client的url和apikey，使用环境变量中的LLM_BASE_URL，LLM_API_KEY
    def __init__(self):
        self._client_url = get_env_value("LLM_BASE_URL")
        self._api_key = get_env_value("LLM_API_KEY")

    def get_client(self):
        """
        获取默认的客户端实例
        """
        return OurAPI()  # 返回我们自己的API客户端实例

    @staticmethod
    def get_special_client(client_type: str):
        """
        根据客户端类型获取特定的客户端实例
        :param client_type: 客户端类型，字符串类型
        :return: 对应的客户端实例
        """
        print("get_special_client")
        if client_type == userPurposeType.ImageGeneration:
            return Image_generate_client
        if client_type == userPurposeType.ImageDescribe:
            return Image_describe_client
        if client_type == userPurposeType.Video:
            return Video_generate_client

        # 默认情况下使用文本生成模型
        return OurAPI()
