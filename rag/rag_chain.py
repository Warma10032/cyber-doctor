# retrieve类型有很多种,这个文件用于调用不同RAG类型接口
from rag.retrieve.retrieve_document import retrieve_docs
from typing import List
from openai import Stream
from openai.types.chat import ChatCompletionChunk
from client.clientfactory import Clientfactory


def invoke(question: str, history: List[List]) -> Stream[ChatCompletionChunk]:
    try:
        docs, _context = retrieve_docs(
            question
        )  # 此处得到的是检索到的文件片段和文件处理后的文本
    except Exception as e:
        _context = ""

    prompt = f"请根据搜索到的文件信息\n{_context}\n 回答问题：\n{question}"
    response = Clientfactory().get_client().chat_with_ai_stream(prompt)

    return response
