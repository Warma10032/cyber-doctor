'''大模型特征工程，提取要进行tts的文本和语种'''
from typing import List, Dict
from client.clientfactory import Clientfactory

_GENERATE_AUDIO_PROMPT_ = (
    "请从上述对话中帮我提取出即将要转成语音的文本，不要包含提示文字"
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

    for user_input, ai_response in history:
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": repr(ai_response)})

    messages.append({"role": "user", "content": question})
    messages.append({"role": "user", "content": _GENERATE_AUDIO_PROMPT_})

    return messages


def extract_text(question: str, history: List[List | None] | None = None) -> str:
    messages = __construct_messages(question, history or [])
    result = Clientfactory().get_client().chat_using_messages(messages)

    return result


def extract_language(text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "你现在扮演信息抽取的角色，要求根据用户输入和AI的回答，正确提取出信息，不要复述，无需包含提示文字",
        },
        {
            "role": "user",
            "content": f"""
            请从如下文本中提取出文本转语音的语种，提取结果只有5种可能（普通话，陕西话，东北话，粤语，台湾话），
            如果文本中有语种信息，但不是以上5种，如英语、日语...则直接返回一个词：其他，
            如果如下文本不包含语种信息，直接返回一个字：无。
            （注意：结果中不要包含任何符号和提示信息）：\n{text}
            """,
        },
    ]
    result = Clientfactory().get_client().chat_using_messages(messages)
    return result


def get_tts_model_name(lang: str, gender: str) -> str:
    if lang == "无" and (gender == "无" or gender == "男声"):
        return "zh-CN-YunxiNeural", True  # 返回普通话男声

    if lang == "无" and gender == "女声":
        return "zh-CN-XiaoxiaoNeural", True  # 返回普通话女声

    if lang == "陕西话" and (gender == "女声" or gender == "无"):
        return "zh-CN-shaanxi-XiaoniNeural", True  # 返回陕西话女声

    if lang == "东北话" and (gender == "女声" or gender == "无"):
        return "zh-CN-liaoning-XiaobeiNeural", True  # 返回东北话女声

    if lang == "粤语" and gender == "女声":
        return "zh-HK-HiuMaanNeural", True  # 返回粤语女声

    if lang == "粤语" and (gender == "男声" or gender == "无"):
        return "zh-HK-WanLungNeural", True  # 返回粤语男声

    if lang == "台湾话" and gender == "男声":
        return "zh-TW-YunJheNeural", True  # 返回台湾话男声

    if lang == "台湾话" and (gender == "女声" or gender == "无"):
        return "zh-TW-HsiaoChenNeural", True  # 返回台湾话女声

    return "zh-CN-YunxiNeural", False  # 可设置一个默认返回值，防止未匹配的情况


def extract_gender(text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "你现在扮演信息抽取的角色，要求根据用户输入和AI的回答，正确提取出信息，不要复述，无需包含提示文字",
        },
        {
            "role": "user",
            "content": f"请从如下文本中提取出文本转语音的声音性别，提取的结果只有两种可能，男声和女声，如果如下文本不包含声音性别，"
            f"直接返回一个字：无。（注意：结果中不要包含任何符号和提示信息）：\n{text}",
        },
    ]

    result = Clientfactory().get_client().chat_using_messages(messages)

    return result
