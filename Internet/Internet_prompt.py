'''大模型特征工程，提取搜索关键词'''
from typing import List, Dict
from client.clientfactory import Clientfactory

_GENERATE_Internet_PROMPT_ = (
    "请根据用户的提问，提取出一个可以在搜索引擎上搜索的问题（不要有多余的内容）"
)


def __construct_messages(
    question: str, history: List[List | None]
) -> List[Dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": "你现在扮演信息抽取的角色，要求根据用户输入和AI的回答，正确提取出信息，无需包含提示文字",
        }
    ]

    messages.append({"role": "user", "content": f"用户提问：{question}"})
    messages.append({"role": "user", "content": _GENERATE_Internet_PROMPT_})

    return messages


def extract_question(question: str, history: List[List | None] | None = None) -> str:
    messages = __construct_messages(question, history or [])
    result = Clientfactory().get_client().chat_using_messages(messages)

    return result
