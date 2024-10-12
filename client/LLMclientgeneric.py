'''封装调用大模型代理的API接口的函数'''
from typing import List, Dict

from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai import Stream

from client.LLMclientbase import LLMclientbase
from overrides import override


# 实例化函数
class LLMclientgeneric(LLMclientbase):

    def __init__(self, *args, **krgs):
        super().__init__()

    # 该函数只负责单论对话交流，不支持流式输出，无历史输入
    @override
    def chat_with_ai(self, prompt: str) -> str | None:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt},
            ],
            top_p=0.7,
            temperature=0.95,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    # 该函数支持流式输出并且可以输入历史，是主要功能函数
    @override
    def chat_with_ai_stream(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.construct_message(prompt, history if history else []),
            top_p=0.7,
            temperature=0.95,
            max_tokens=1024,
            stream=True,
        )
        return response

    # 该函数用于构造消息，进行提示词工程
    @override
    def construct_message(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> List[Dict[str, str]] | str | None:
        messages = [
            {
                "role": "system",
                "content": "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的回答。",
            }
        ]

        for user_input, ai_response in history:
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": ai_response.__repr__()})

        messages.append({"role": "user", "content": prompt})
        return messages

    # 该函数用于直接输入消息进行对话，在ppt/word生成中作用
    @override
    def chat_using_messages(self, messages: List[Dict]) -> str | None:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            top_p=0.7,
            temperature=0.95,
            max_tokens=1024,
        )

        return response.choices[0].message.content
