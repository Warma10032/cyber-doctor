from typing import Tuple, List, Any

# , map_question_to_function_args
from qa.function_tool import map_question_to_function

from qa.purpose_type import userPurposeType


def get_answer(
    question: str, history: List[List | None] = None, question_type=None, image_url=None
) -> Tuple[Any, userPurposeType]:
    """
    根据问题获取答案或者完成任务
    :param history:
    :param question:
    :return:
    """

    function = map_question_to_function(question_type)

    args = [question_type, question, history, image_url]
    result = function(*args)

    return result
