'''调用model/Internet中的接口，检索搜索到的资料'''
from typing import List,Tuple
from langchain_core.documents import Document
from model.Internet.Internet_service import retrieve

def format_docs(docs:List[Document]):
    return "\n-------------分割线--------------\n".join(doc.page_content for doc in docs)

def retrieve_html(question:str)->Tuple[List[Document],str]:
    docs = retrieve(question) # 这里的到的是文件
    _context = format_docs(docs) # 这里处理成文本
    print(_context)
    return (docs,_context)