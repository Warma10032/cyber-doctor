'''问答类型判断函数，根据特定输入和大模型进行分类分类。'''
from typing import List, Dict

from client.clientfactory import Clientfactory

from qa.prompt_templates import get_question_parser_prompt
from qa.purpose_type import purpose_map
from qa.purpose_type import userPurposeType

from icecream import ic


def parse_question(question: str, image_url=None) -> userPurposeType:

    if "根据知识库" in question:
        return purpose_map["基于知识库"]
    
    if "根据知识图谱" in question:
        return purpose_map["基于知识图谱"]

    if "搜索" in question:
        return purpose_map["网络搜索"]
    
    if ("word" in question or "Word" in question or "WORD" in question) and ("生成" in question or "制作" in question):
        return purpose_map["Word生成"]
    
    if ("ppt" in question or "PPT" in question or "PPT" in question) and ("生成" in question or "制作" in question):
        return purpose_map["PPT生成"]
    
    if image_url is not None:
        return purpose_map["图片描述"]

    # 在这个函数中我们使用大模型去判断问题类型
    prompt = get_question_parser_prompt(question)
    response = Clientfactory().get_client().chat_with_ai(prompt)
    ic("大模型分类结果：" + response)

    if response == "图片生成" and len(question) > 0:
        return purpose_map["图片生成"]
    if response == "视频生成" and len(question) > 0:
        return purpose_map["视频生成"]
    if response == "PPT生成" and len(question) > 0:
        return purpose_map["PPT生成"]
    if response == "Word生成" and len(question) > 0:
        return purpose_map["Word生成"]
    if response == "音频生成" and len(question) > 0:
        return purpose_map["音频生成"]
    if response == "文本生成":
        return purpose_map["文本生成"]
    return purpose_map["其他"]



