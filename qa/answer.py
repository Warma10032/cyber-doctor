'''根据问答类型选择对应的工具函数进行处理'''
from typing import Tuple, List, Any

from qa.function_tool import map_question_to_function

from qa.purpose_type import userPurposeType


# qa/answer.py
def get_answer(question, chatbot, question_type, image_url):
    function = map_question_to_function(question_type)
    args = [question_type, question, chatbot, image_url]  # 注意：history 应该是 chatbot
    result = function(*args)
    
    # 统一返回格式：(内容, 类型)
    if isinstance(result, tuple):
        return result
    else:
        return (result, question_type)  # ← 确保总是元组

