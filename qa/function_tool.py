'''存放处理不同问答类型的工具函数，核心文件'''

import base64
from typing import Callable, List, Dict, Tuple
import time
import json
from client.clientfactory import Clientfactory
from qa.purpose_type import userPurposeType
from pathlib import Path
from ppt_docx.ppt_generation import generate as generate_ppt
from ppt_docx.ppt_content import generate_ppt_content
from ppt_docx.docx_generation import generate_docx_content as generate_docx
from ppt_docx.docx_content import generate_docx_content
from rag import rag_chain
from audio.audio_extract import (
    extract_text,
    extract_language,
    extract_gender,
    get_tts_model_name,
)
from audio.audio_generate import audio_generate
from model.KG.search_service import search
from Internet.Internet_chain import InternetSearchChain
from kg.Graph import GraphDao
from config.config import Config
from qa.purpose_type import userPurposeType
from env import get_env_value


_dao = GraphDao()

def is_file_path(path):
    return Path(path).exists()

def relation_tool(entities: List[Dict] | None) -> str | None:
    if not entities or len(entities) == 0:
        return None

    relationships = set()  # 使用集合来避免重复关系
    relationship_match = []

    searchKey = Config.get_instance().get_with_nested_params("model", "graph-entity", "search-key")
    # 遍历每个实体并查询与其他实体的关系
    for entity in entities:
        entity_name = entity[searchKey]
        for k, v in entity.items():
            relationships.add(f"{entity_name} {k}: {v}")

        # 查询每个实体与其他实体的关系a-r-b
        relationship_match.append(_dao.query_relationship_by_name(entity_name))
        
    # 抽取并记录每个实体与其他实体的关系
    for i in range(len(relationship_match)):
        for record in relationship_match[i]:
            # 获取起始节点和结束节点的名称

            start_name = record["r"].start_node[searchKey]
            end_name = record["r"].end_node[searchKey]

            # 获取关系类型
            rel = type(record["r"]).__name__  # 获取关系名称，比如 CAUSES

            # 构建关系字符串并添加到集合，确保不会重复添加
            relationships.add(f"{start_name} {rel} {end_name}")

    # 返回关系集合的内容
    if relationships:
        return "；".join(relationships)
    else:
        return None


def check_entity(question: str) -> List[Dict]:
    code, result = search(question)
    if code == 0:
        return result
    else:
        return None


def KG_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    kg_info = None
    try:
        # 此处在使用知识图谱之前，需先检查问题的实体
        entities = check_entity(question)
        kg_info = relation_tool(entities)
    except:
        pass

    if kg_info is not None:
        print(f"KG_tool: \n {kg_info}")
        question = f"{question}\n从知识图谱中检索到的信息如下{kg_info}\n请你基于知识图谱的信息去回答,并给出知识图谱检索到的信息"

    response = Clientfactory().get_client().chat_with_ai_stream(question, history)
    return (response, question_type)


# 处理text问题的函数
def process_text_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    response = Clientfactory().get_client().chat_with_ai_stream(question, history)
    return (response, question_type)


# 处理RAG问题
def RAG_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    # 先利用question去检索得到docs
    response = rag_chain.invoke(question, history)
    return (response, question_type)


# 处理ImageGeneration问题的函数
def process_images_tool(question_type, question, history, image_url=None):
    client = Clientfactory.get_special_client(client_type=question_type)
    response = client.images.generations(
        model=get_env_value("IMAGE_GENERATE_MODEL"),  # 填写需要调用的模型编码
        prompt=question,
    )
    print(response.data[0].url)
    return (response.data[0].url, question_type)


def process_image_describe_tool(question_type, question, history, image_url=None):
    if question == "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'请问您有什么想了解的，我将尽力为您服务'":
        question = "描述这个图片，说明这个图片的主要内容"
    image_bases = []
    for img_url in image_url:
        if is_file_path(img_url):
            with open(img_url, "rb") as img_file:
                image_base = base64.b64encode(img_file.read()).decode("utf-8")
                image_bases.append(image_base)
        else:
            image_bases.append(img_url)

    # 构建 messages 内容
    message_content = []
    for image_base in image_bases:
        message_content.append({"type": "image_url", "image_url": {"url": image_base}})
    # 添加问题的文本内容
    message_content.append({"type": "text", "text": question})

    client = Clientfactory.get_special_client(client_type=question_type)
    # 发送请求
    response = client.chat.completions.create(
        model=get_env_value("IMAGE_DESCRIBE_MODEL"),
        messages=[
            {
                "role": "user",
                "content": message_content,
            }
        ],
    )
    return (response.choices[0].message.content, question_type)


def process_ppt_tool(
    question_type, question: str, history: List[List[str] | None] = None, image_url=None
) -> Tuple[Tuple[str, str], userPurposeType]:
    raw_text: str = generate_ppt_content(question, history)
    try:
        ppt_content = json.loads(raw_text)
    except:
        return None, userPurposeType.PPT
    ppt_file: str = generate_ppt(
        ppt_content
    )  # 这个语句由于模型能力有限，可能不会按照格式输出，会导致冲突，要用str正则语句修改，删除一些异常符号，否则会出bug
    return (ppt_file, "ppt"), userPurposeType.PPT


def process_docx_tool(
    question_type, question: str, history: List[List[str] | None] = None, image_url=None
) -> Tuple[Tuple[str, str], userPurposeType]:
    # 先生成word的文案
    raw_text: str = generate_docx_content(question, history)
    try:
        docx_content = json.loads(raw_text)
    except:
        return None, userPurposeType.Docx
    docx_file: str = generate_docx(docx_content)
    return (docx_file, "docx"), userPurposeType.Docx


def process_text_video_tool(question_type, question, history, image_url=None):
    client = Clientfactory.get_special_client(client_type=question_type)
    try:
        chatRequest = client.videos.generations(
            model=get_env_value("VIDEO_GENERATE_MODEL"),
            prompt=question,
        )
        print(chatRequest)

        start_time = time.time()  # 开始计时
        video_url = None
        timeout = 120
        while time.time() - start_time < timeout:
            # 请求视频生成结果
            print(chatRequest.id)
            response = client.videos.retrieve_videos_result(id=chatRequest.id)

            # 检查任务状态是否成功
            if response.task_status == "SUCCESS" and response.video_result:
                video_url = response.video_result[0].url
                print("视频URL:", video_url)
                return ((video_url, "视频"), question_type)
            else:
                print("任务未完成，请等待...")

            # 等待一段时间再请求
            time.sleep(2)  # 每次请求后等待2秒再继续

    except:
        return (None, question_type)


# 处理audio问题的函数
def process_audio_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    # 先让大语言模型生成需要转换成语音的文字
    text = extract_text(question, history)
    # 判断需要生成哪种语言（东北、陕西、粤...）
    lang = extract_language(question)
    # 判断需要生成男声还是女声
    gender = extract_gender(question)
    # 上面三步均与大语言模型进行交互

    # 选择用于生成的模型
    model_name, success = get_tts_model_name(lang=lang, gender=gender)
    if success:
        audio_file = audio_generate(text, model_name)
    else:
        audio_file = audio_generate(
            "由于目标语言包缺失，我将用普通话回复您。" + text, model_name
        )
    return ((audio_file, "audio"), question_type)


# 处理联网搜索问题的函数
def process_InternetSearch_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    response, links, success = InternetSearchChain(question, history)
    return (response, question_type, links, success)


QUESTION_TO_FUNCTION = {
    userPurposeType.text: process_text_tool,
    userPurposeType.RAG: RAG_tool,
    userPurposeType.ImageGeneration: process_images_tool,
    userPurposeType.Audio: process_audio_tool,
    userPurposeType.InternetSearch: process_InternetSearch_tool,
    userPurposeType.ImageDescribe: process_image_describe_tool,
    userPurposeType.PPT: process_ppt_tool,
    userPurposeType.Docx: process_docx_tool,
    userPurposeType.Video: process_text_video_tool,
    userPurposeType.KnowledgeGraph: KG_tool,
}


# 根据用户不同的意图选择不同的函数
def map_question_to_function(purpose: userPurposeType) -> Callable:
    if purpose in QUESTION_TO_FUNCTION:
        return QUESTION_TO_FUNCTION[purpose]
    else:
        raise ValueError("没有找到意图对应的函数")
