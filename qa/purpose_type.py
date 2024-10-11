from enum  import Enum

class userPurposeType(Enum):
    #根据用户输入的文本信息的可能问题类型预定义
    text = 0  #未知问题
    Audio = 1   #语音生成
    Video = 2   #视频生成
    ImageGeneration = 3 #文生图
    ImageDescribe = 4 #图生文
    RAG = 5  #基于文件描述，后面有个向量库，对于单个用户，尽量从向量数据库给出回答，可能涉及检索加强
    Hello = 6   #问候语，给出特定输出
    PPT=7      #PPT生成
    InternetSearch = 8 #网络搜索
    Docx = 9   #生成word文件
    KnowledgeGraph = 10 #基于知识图谱的问答
 
  
purpose_map={
"其他":userPurposeType.text,
"文本生成":userPurposeType.text,
"音频生成":userPurposeType.Audio,
"视频生成":userPurposeType.Video,
"图片描述":userPurposeType.ImageDescribe,
"图片生成":userPurposeType.ImageGeneration,
"基于知识库":userPurposeType.RAG,
"问候语":userPurposeType.Hello,
"PPT生成":userPurposeType.PPT,
"Word生成":userPurposeType.Docx,
"网络搜索":userPurposeType.InternetSearch,
"基于知识图谱":userPurposeType.KnowledgeGraph,
}

