'''本地知识库的RAG检索模型类'''
from model.model_base import Modelbase
from model.model_base import ModelStatus
from config.config import Config
from env import get_app_root

import os
import shutil
import markdown  # pip install markdown
import unstructured  # pip install unstructured
import docx  # pip install python-docx

from langchain_community.embeddings import ModelScopeEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    JSONLoader,
    MHTMLLoader,
    TextLoader,
    CSVLoader,
)
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from modelscope.hub.snapshot_download import snapshot_download


# 检索模型
class Retrievemodel(Modelbase):

    _retriever: VectorStoreRetriever

    def __init__(self, *args, **krgs):
        super().__init__(*args, **krgs)

        # 此处请自行改成下载embedding模型的位置
        self._embedding_download_path = Config.get_instance().get_with_nested_params(
            "model", "embedding", "model-path"
        )
        self._embedding_model_name = Config.get_instance().get_with_nested_params(
            "model", "embedding", "model-name"
        )
        self._embedding_model_path = os.path.join(
            self._embedding_download_path, self._embedding_model_name
        )
        if not os.path.exists(self._embedding_model_path):
            try:
                # 如果为空，则从modelscope下载模型
                model_dir = snapshot_download(
                    self._embedding_model_name,
                    cache_dir=self._embedding_download_path,
                )
                print(f"Model downloaded and saved to {model_dir}")
            except Exception as e:
                print(f"Failed to download model: {e}")
                if os.path.exists(self._embedding_model_path):
                    shutil.rmtree(self._embedding_model_path)
        # self._loader = PyPDFDirectoryLoader
        self._text_splitter = RecursiveCharacterTextSplitter
        # self._embedding = OpenAIEmbeddings()
        self._embedding = ModelScopeEmbeddings(model_id=self._embedding_model_path)
        self._data_path = Config.get_instance().get_with_nested_params(
            "Knowledge-base-path"
        )
        if not os.path.exists(self._data_path):
            os.makedirs(self._data_path)
        self._user_retrievers = {}


    # 建立向量库
    def build(self):

        # 加载PDF文件
        pdf_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        pdf_docs = pdf_loader.load()

        # 加载Word文件
        docx_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.docx",
            loader_cls=UnstructuredWordDocumentLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        docx_docs = docx_loader.load()

        # 加载txt文件
        txt_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.txt",
            loader_cls=TextLoader,
            silent_errors=True,
            loader_kwargs={"autodetect_encoding": True},
            use_multithreading=True,
        )
        txt_docs = txt_loader.load()

        # 加载csv文件
        csv_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.csv",
            loader_cls=CSVLoader,
            silent_errors=True,
            loader_kwargs={"autodetect_encoding": True},
            use_multithreading=True,
        )
        csv_docs = csv_loader.load()

        # 加载html文件
        html_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.html",
            loader_cls=UnstructuredHTMLLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        html_docs = html_loader.load()

        mhtml_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.mhtml",
            loader_cls=MHTMLLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        mhtml_docs = mhtml_loader.load()

        # 加载markdown文件
        markdown_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.md",
            loader_cls=UnstructuredMarkdownLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        markdown_docs = markdown_loader.load()

        # 要利用json数据要设置jq语句和content_key提取特定字段，这在不同json数据结构中有所不同，较为繁琐。
        # 官方文档：https://api.python.langchain.com/en/latest/document_loaders/langchain_community.document_loaders.json_loader.JSONLoader.html
        # json_loader = DirectoryLoader(self._data_path, glob="**/*.json", loader_kwargs={"jq_schema": ".","text_content":False},loader_cls=JSONLoader, silent_errors=True)
        # json_docs = json_loader.load()

        # 合并文档
        docs = (
            pdf_docs
            + docx_docs
            + txt_docs
            + csv_docs
            + html_docs
            + mhtml_docs
            + markdown_docs
        )

        # 创建一个 RecursiveCharacterTextSplitter 对象，用于将文档分割成块，chunk_size为最大块大小，chunk_overlap块之间可以重叠的大小
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000, chunk_overlap=100
        )
        splits = text_splitter.split_documents(docs)

        # 使用 FAISS 创建一个向量数据库，存储分割后的文档及其嵌入向量
        vectorstore = FAISS.from_documents(documents=splits, embedding=self._embedding)
        # 将向量存储转换为检索器，设置检索参数 k 为 6，即返回最相似的 6 个文档
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

        # 设置模型状态为 BUILDING
        self._model_status = ModelStatus.BUILDING

    @property
    def retriever(self) -> VectorStoreRetriever:
        if self._model_status == ModelStatus.FAILED:
            self.build()
            return self._retriever
        else:
            return self._retriever

    def build_user_vector_store(self):
        """根据用户的ID加载用户文件夹中的文件并为用户构建向量库"""
        user_data_path = os.path.join("user_data", self.user_id)  # 用户独立文件夹
        if not os.path.exists(user_data_path):
            print(f"用户文件夹 {user_data_path} 不存在")
            return

        try:
            # 清理旧的向量库（如果已经存在）
            if self.user_id in self._user_retrievers:
                del self._user_retrievers[self.user_id]
                print(f"用户 {self.user_id} 的旧向量库已删除")

                # 加载用户文件夹中的文件并构建向量库
                # 加载PDF文件
            pdf_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.pdf",
                loader_cls=PyPDFLoader,
                silent_errors=True,
                use_multithreading=True,
            )
            pdf_docs = pdf_loader.load()

            # 加载Word文件
            docx_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.docx",
                loader_cls=UnstructuredWordDocumentLoader,
                silent_errors=True,
                use_multithreading=True,
            )
            docx_docs = docx_loader.load()

            # 加载txt文件
            txt_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.txt",
                loader_cls=TextLoader,
                silent_errors=True,
                loader_kwargs={"autodetect_encoding": True},
                use_multithreading=True,
            )
            txt_docs = txt_loader.load()

            # 加载csv文件
            csv_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.csv",
                loader_cls=CSVLoader,
                silent_errors=True,
                loader_kwargs={"autodetect_encoding": True},
                use_multithreading=True,
            )
            csv_docs = csv_loader.load()

            # 加载html文件
            html_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.html",
                loader_cls=UnstructuredHTMLLoader,
                silent_errors=True,
                use_multithreading=True,
            )
            html_docs = html_loader.load()

            mhtml_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.mhtml",
                loader_cls=MHTMLLoader,
                silent_errors=True,
                use_multithreading=True,
            )
            mhtml_docs = mhtml_loader.load()

            # 加载markdown文件
            markdown_loader = DirectoryLoader(
                user_data_path,
                glob="**/*.md",
                loader_cls=UnstructuredMarkdownLoader,
                silent_errors=True,
                use_multithreading=True,
            )
            markdown_docs = markdown_loader.load()

            # 要利用json数据要设置jq语句和content_key提取特定字段，这在不同json数据结构中有所不同，较为繁琐。
            # 官方文档：https://api.python.langchain.com/en/latest/document_loaders/langchain_community.document_loaders.json_loader.JSONLoader.html
            # json_loader = DirectoryLoader(self._data_path, glob="**/*.json", loader_kwargs={"jq_schema": ".","text_content":False},loader_cls=JSONLoader, silent_errors=True)
            # json_docs = json_loader.load()

            # 合并文档
            docs = (
                pdf_docs
                + docx_docs
                + txt_docs
                + csv_docs
                + html_docs
                + mhtml_docs
                + markdown_docs
            )

            if not docs:
                print(f"用户 {self.user_id} 文件夹中没有找到文档")
                return

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000, chunk_overlap=100
            )
            splits = text_splitter.split_documents(docs)

            # 为该用户构建向量库
            vectorstore = FAISS.from_documents(
                documents=splits, embedding=self._embedding
            )
            user_retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

            # 将用户的retriever存储到字典中
            self._user_retrievers[self.user_id] = user_retriever
            print(f"用户 {self.user_id} 的向量库已构建完成")

        except Exception as e:
            print(f"构建用户 {self.user_id} 向量库时出错: {e}")

    def get_user_retriever(self) -> VectorStoreRetriever:
        """获取用户的retriever，如果不存在则返回None"""
        return self._user_retrievers.get(self.user_id, None)

    def upload_user_file(self, file):
        """将用户上传的文件存储到用户的文件夹中"""
        user_data_path = os.path.join("user_data", self.user_id)
        os.makedirs(user_data_path, exist_ok=True)  # 确保用户文件夹存在

        file_path = os.path.join(user_data_path, file.name)
        with open(file_path, "wb") as f:
            f.write(file.read())

        print(f"文件 {file.name} 已成功上传到用户 {self.user_id} 的文件夹")

    # 展示用户已上传的文件
    def list_uploaded_files(self):
        """展示用户文件夹中已经上传的文件"""
        user_data_path = os.path.join("user_data", self.user_id)
        if not os.path.exists(user_data_path):
            print(f"用户文件夹 {user_data_path} 不存在")
            return []

        files = os.listdir(user_data_path)
        if files:
            print(f"用户 {self.user_id} 已上传的文件：")
            for file in files:
                print(file)
        else:
            print(f"用户 {self.user_id} 文件夹为空")

        return files

    # 删除指定文件或清空用户文件夹
    def delete_uploaded_file(self, filename=None):
        """删除用户文件夹中的指定文件，或清空文件夹"""
        user_data_path = os.path.join("user_data", self.user_id)
        if not os.path.exists(user_data_path):
            print(f"用户文件夹 {user_data_path} 不存在")
            return

        if filename:
            file_path = os.path.join(user_data_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"文件 {filename} 已成功删除")
            else:
                print(f"文件 {filename} 不存在")
        else:
            # 清空文件夹
            for file in os.listdir(user_data_path):
                file_path = os.path.join(user_data_path, file)
                os.remove(file_path)
            print(f"用户 {self.user_id} 文件夹已清空")

    def view_uploaded_file(self, filename):
        """根据文件名返回用户文件的路径"""
        user_data_path = os.path.join("user_data", self.user_id)  # 定义用户文件夹路径
        file_path = os.path.join(user_data_path, filename)  # 拼接完整的文件路径

        if not os.path.exists(file_path):
            print(f"文件 {filename} 不存在")
            return None

        # 文件存在时返回文件的完整路径
        print(f"文件 {filename} 路径已成功获取")
        return file_path


INSTANCE = Retrievemodel()
