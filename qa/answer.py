'''根据问答类型选择对应的工具函数进行处理'''
from typing import Tuple, List, Any

from qa.function_tool import map_question_to_function

from qa.purpose_type import userPurposeType


def get_answer(
    question: str, history: List[List | None] = None, question_type=None, image_url=None
) -> Tuple[Any, userPurposeType]:
    """
    根据问题类型调用对应的函数获取结果
    """

    function = map_question_to_function(question_type)

    args = [question_type, question, history, image_url]
    result = function(*args)

    return result
