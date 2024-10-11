from env import get_env_value
from abc import abstractmethod

from openai import OpenAI
from openai import Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from typing import List, Dict


# 抽象类，用于构造client
class LLMclientbase(object):
    def __init__(self):
        """
        初始化LLM客户端基类
        """
        self.__client = OpenAI(
            api_key=get_env_value(
                "LLM_API_KEY"
            ),  # 使用环境变量中的API密钥初始化OpenAI客户端
            base_url=get_env_value(
                "LLM_BASE_URL"
            ),  # 使用环境变量中的基础URL初始化OpenAI客户端
        )
        self.__model_name = get_env_value("MODEL_NAME")  # 使用环境变量中的模型名称

    @property
    def client(self):
        return self.__client

    @property
    def model_name(self):
        return self.__model_name

    # 以下全都是抽象函数
    @abstractmethod
    def chat_with_ai(self, prompt: str) -> str | None:
        """
        与AI进行聊天，返回AI的回复
        :param prompt: 用户输入的提示信息
        :return: AI的回复，可能为None
        """
        raise NotImplementedError()

    @abstractmethod
    def chat_with_ai_stream(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:
        """
        与AI进行流式聊天，返回流式回复
        :param prompt: 用户输入的提示信息
        :param history: 聊天历史记录，默认为None
        :return: 流式聊天完成或流式聊天块
        """
        raise NotImplementedError()

    @abstractmethod
    def construct_message(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> List[Dict[str, str]] | str | None:
        """
        构造消息，用于与AI进行聊天
        :param prompt: 用户输入的提示信息
        :param history: 聊天历史记录，默认为None
        :return: 构造的消息列表或字符串，可能为None
        """
        raise NotImplementedError()

    @abstractmethod
    def chat_using_messages(self, messages: List[Dict]) -> str | None:
        """
        使用消息列表与AI进行聊天，返回AI的回复
        :param messages: 消息列表
        :return: AI的回复，可能为None
        """
        raise NotImplementedError()
