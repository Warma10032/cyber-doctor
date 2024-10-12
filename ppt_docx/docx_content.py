'''大模型特征工程，让大模型输出json格式的数据'''
import json
import re
from typing import List, Dict
from client.clientfactory import Clientfactory

# 模拟一个用于生成 docx 内容的 JSON 模板
__output_format_docx = json.dumps({
    "title": "example title",
    "sections": [
        {
            "heading": "Section 1",
            "paragraphs": [
                {
                    "heading": "Paragraph 1",
                    "content": "Details of paragraph 1"
                },
                {
                    "heading": "Paragraph 2",
                    "content": "Details of paragraph 2"
                }
            ]
        },
        {
            "heading": "Section 2",
            "paragraphs": [
                {
                    "heading": "Paragraph 1",
                    "content": "Details of paragraph 1"
                },
                {
                    "heading": "Paragraph 2",
                    "content": "Details of paragraph 2"
                },
                {
                    "heading": "Paragraph 3",
                    "content": "Details of paragraph 3"
                }
            ]
        }
    ]
}, ensure_ascii=True)

# 定义一个 prompt 用于生成 docx 内容
_GENERATE_DOCX_PROMPT_ = f'''请你根据用户要求生成docx的详细内容，不要省略。按这个JSON格式输出{__output_format_docx}，只能返回JSON，且JSON不要用```包裹，不要返回markdown格式'''

# 构造消息函数，历史记录被包括在内
def __construct_messages_docx(question: str, history: List[List | None]) -> List[Dict[str, str]]:
    messages = [
        {"role": "system",
         "content": "你现在扮演信息抽取的角色，要求根据用户输入和AI的回答，正确提取出信息。"}]

    for user_input, ai_response in history:
        messages.append({"role": "user", "content": user_input})
        messages.append(
            {"role": "assistant", "content": repr(ai_response)})
    messages.append({"role": "system", "content": question})
    messages.append({"role": "user", "content": _GENERATE_DOCX_PROMPT_})

    return messages

# 生成 docx 内容的函数
def generate_docx_content(question: str,
                         history: List[List | None] | None = None) -> str:
    messages = __construct_messages_docx(question, history or [])
    print(messages)
    result = Clientfactory().get_client().chat_using_messages(messages)
    print(result)
    print(type(result))

    # 处理生成内容中的多余部分，比如“json”关键字或者反引号
    result = re.sub(r'\bjson\b', '', result)
    result = re.sub(r'`', '', result)

    # 检查生成内容的结尾是否正确
    index_of_last = result.rfind('"')
    total_result = None
    print(result)

    if index_of_last != -1 and result[index_of_last + 1:] == '}]}]}':
        # 如果格式正确，不做改变
        total_result = result
        print(total_result)
        return total_result
    else:
        # 如果格式不正确，修复 JSON 的结尾
        total_result = result[:index_of_last + 1] + '}]}]}'
        print(total_result)
        return total_result
