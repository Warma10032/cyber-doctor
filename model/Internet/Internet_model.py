'''联网搜索的RAG检索模型类'''
from model.model_base import Modelbase
from model.model_base import ModelStatus

import os
from env import get_app_root

from langchain_community.embeddings import ModelScopeEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import DirectoryLoader, MHTMLLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS

from config.config import Config

# 检索模型
class InternetModel(Modelbase):
    
    _retriever: VectorStoreRetriever

    def __init__(self,*args,**krgs):
        super().__init__(*args,**krgs)

        # 此处请自行改成下载embedding模型的位置
        self._embedding_model_path =Config.get_instance().get_with_nested_params("model", "embedding", "model-name")
        self._text_splitter = RecursiveCharacterTextSplitter
        #self._embedding = OpenAIEmbeddings()
        self._embedding = ModelScopeEmbeddings(model_id=self._embedding_model_path)
        self._data_path = os.path.join(get_app_root(), "data/cache/internet")
        
        #self._logger: Logger = Logger("rag_retriever")

    # 建立向量库
    def build(self):
        # 加载html文件
        html_loader = DirectoryLoader(self._data_path, glob="**/*.html", loader_cls=UnstructuredHTMLLoader, silent_errors=True, use_multithreading=True)
        html_docs = html_loader.load()
        
        mhtml_loader = DirectoryLoader(self._data_path, glob="**/*.mhtml", loader_cls=MHTMLLoader, silent_errors=True, use_multithreading=True)
        mhtml_docs = mhtml_loader.load()
        
        
        #合并文档
        docs =  html_docs + mhtml_docs
        
        # 创建一个 RecursiveCharacterTextSplitter 对象，用于将文档分割成块，chunk_size为最大块大小，chunk_overlap块之间可以重叠的大小
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)
        
        # 使用 FAISS 创建一个向量数据库，存储分割后的文档及其嵌入向量
        vectorstore = FAISS.from_documents(documents=splits, embedding=self._embedding)
        # 将向量存储转换为检索器，设置检索参数 k 为 6，即返回最相似的 6 个文档
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
        

        
    @property
    def retriever(self)-> VectorStoreRetriever:
        self.build()
        return self._retriever

INSTANCE = InternetModel()