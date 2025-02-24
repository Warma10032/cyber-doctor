<div align="center">
 <img src="README/bot.jpg" width="200" />
</div>

<h1 align="center">「赛博华佗」🩺 cyber-doctor 你的健康小管家</h1>

**语言**

- [English](./README_en.md)
- [中文](./README.md)

---

![](https://img.shields.io/github/stars/Warma10032/cyber-doctor?style=social)
![](https://img.shields.io/github/forks/Warma10032/cyber-doctor?style=social)
![](https://img.shields.io/github/contributors/Warma10032/cyber-doctor)
![](https://img.shields.io/github/issues/Warma10032/cyber-doctor)
![](README/License-GPLv3-blue.svg)

## 项目演示视频

https://www.bilibili.com/video/BV1CU2aYpEn2

## 项目背景

医疗资源不平衡一直以来是社会关注的重点问题，它导致众多医疗不公平事件发生。在相对落后地区的人们想要获得优秀的医疗资源往往需要前往一线城市，这不仅费时费力费钱，而且极大的影响了他们的接受医疗救助的基本权利。当前多模态大语言模型不断发展，在许多领域都有了不错的应用。我们小组基于东南大学暑期实训课程，开发了一个医疗健康领域的多模态大模型，这个大模型的目标用户是所有对自己健康关心的人，帮助进行基本的疾病诊断，病历分析，专业知识答疑等功能。本项目狭义上可以作为一个多功能的健康小助手，帮助管理个人健康，提供基础的医疗建议；广义上可以配置在任何领域，通过微调的大模型和RAG技术让大模型掌握目标领域的专业知识，成为任意专业的专家。

## 界面展示

### 文本交流界面

![](README/文本交流界面.png)

### 语音对话界面

![](README/语音对话界面.png)

## 功能特色

- **多功能多模态整合，借助AI智能体判断任务的种类，将多个模型整合工作，解决复杂问题。**
- **单独的语音对话模块，语音输入语音输出，只需要会说话就能使用，降低大模型学习成本。**

## 功能介绍

![功能模块](README/功能模块.png)

| 功能         | 功能介绍                                                                                                 |
| ------------ | -------------------------------------------------------------------------------------------------------- |
| 图片识别     | 借助多模态大模型的能力，识别图片中的图像和文字。可用于识别病历，识别药品说明书等                         |
| 视频生成     | 借助多模态大模型的能力，生成视频                                                                         |
| 图片生成     | 借助多模态大模型的能力，生成图片                                                                         |
| ppt/word生成 | 可自动生成固定格式的纯文字PPT和Word文档                                                                  |
| 多轮对话     | 具有记忆功能，对话界面的所有内容会作为历史记录一同输入大模型                                             |
| 检索增强对话 | 多模态输入框不只能输入文本，还能上传文件。大模型会根据文件内容调整输出                                   |
| 语音输入     | 多模态输入框可以上传音频文件。进入语音对话模式可以直接使用麦克风进行语音输入                             |
| 语音输出     | 要求大模型以语音的形式进行输出时，大模型会返回一段音频，支持多种方言，在语音对话模式下默认以语言形式输出 |
| 知识图谱增强 | 支持配置相关领域的neo4j知识图谱，用专业知识改善大模型输出                                                |
| 知识库增强   | 支持利用多种格式的文件作为专属知识库，大模型会结合知识库中的文件进行输出                                 |
| 联网检索增强 | 通过自动化爬虫检索网络上的相关信息，利用网络增强大模型知识的时效性                                       |

## 典型功能展示

### 病历识别

![](README/病历识别.png)

### PPT/Word生成

![](README/PPT&Word生成.png)

![](README/PPT&Word展示.png)

### 知识图谱检索增强：

![](README/知识图谱检索.png)

### 联网检索增强：

![](README/联网搜索.png)

## 技术栈

- **Python**
- **PyTorch**
- **Transformers**
- **Gradio**：简易的UI和交互生成工具
- **Langchain**：基于 Langchain 框架，构建语言模型进行链式操作
- **modelscope & huggingface**：预训练大模型的下载与配置
- **RAG**：结合检索与生成的技术，用于增强生成式模型的回答质量
- **Knowledge Graph (Neo4j)**：Neo4j图数据库的配置和Cypher语句操作
- **TTS (edge-tts)，STT (whisper)**：语音转文本，文本转语音
- **OpenAi & zhipuai**：相关大模型sdk调用方法

Option：

- **Ollama**：本地大模型api封装

## 如何启动项目

1. **从Github上拉取项目**

   ```bash
   git clone https://github.com/Warma10032/cyber-doctor.git
   或者
   git clone git@github.com:Warma10032/cyber-doctor.git
   ```
   
2. **配置大模型API**

   复制 `.env.example`为 `.env`，填写 `.env`内相关API配置。

   API目前支持：

   1. 所有支持OpenAI SDK接口的API，包括
      - [智谱AI](https://open.bigmodel.cn/)
      - [豆包大模型](https://www.volcengine.com/experience/ark?utm_term=202502dsinvite&ac=DSASUQY5&rc=II9TBGSX)
      - [硅基流动集成平台](https://cloud.siliconflow.cn/i/VWOdVvvM)
      - [deepseek](https://platform.deepseek.com/)
      - [千问Qwen](https://bailian.console.aliyun.com/)
   2. Ollama封装的本地API

如果你还未申请API，欢迎通过我的邀请链接进行注册获取新人试用额度。

   由于团队本身缺少申请/测试多家API的能力，可能会有各种bug，**欢迎各位提出相关的issue和PR一起来解决API适配问题，你的行动是对开源社区最大的帮助。**

3. **填写 `config/config-web.yaml`配置文件**

4. **创建python环境（python>=3.10，建议为3.10）**

   建议使用conda管理环境

   ```bash
   conda create --name myenv python=3.10
   conda activate myenv
   ```

   安装依赖库

   ```bash
   pip install -r requirements.txt
   ```
   
5. **启动项目**

   ```bash
   python app.py
   ```

   启动后访问 http://localhost:7860

Option：

1. **下载Neo4j图数据库（使用知识图谱检索增强功能的必要条件）**

   推荐教程：

   - [Windows系统下Neo4j安装教程——CSDN博客](https://blog.csdn.net/jing_zhong/article/details/112557084)
   - [Docker化部署Neo4j](https://cloud.baidu.com/article/3314714)

   提醒：

   - 免费的社区版即可，能创建一个图数据库
   - 创建时记住用户名和密码
   - 填写config/config-web.yaml配置文件
   - 记得启动Neo4j服务
2. **配置一个专业领域的图数据库**

   推荐开源知识图谱平台：[OpenKG](http://openkg.cn/datasets-type/)

   如果想配置医疗健康领域的数据库，推荐下载如下开源知识图谱

   [面向家庭常见疾病的知识图谱](http://data.openkg.cn/dataset/medicalgraph)（本项目使用了该图谱，使用该图谱可以不更改config/config-web.yaml的相关配置文件）

   1. 下载到本地后，改.dump文件名为你要导入的数据库名称（eg：neo4j.dump）
   2. 关闭neo4j服务

      ```
      Windows: neo4j stop
      Linux: sudo neo4j stop
      ```
   3. 运行导入指令（这一步简中互联网上找不到正确的教程😡）

      ```
      neo4j-admin database load <database-name> --from-path=/path/to/dump-folder/ --overwrite-destination=true
      ```

      `--from-path`：存放对应"database-name".dump文件的文件夹路径

      `--overwrite-destination`：**注意会覆盖你原先数据库中的数据**
   4. 若运行上面的命令后输出

      ```
      The loaded database 'neo4j' is not on a supported version (current format: AF4.3.0 introduced in 4.3.0). Use the 'neo4j-admin database migrate' command
      ```

      还需要运行如下命令

      ```
      neo4j-admin database migrate 
      ```
   5. 启动neo4j服务

      ```
      Windows: neo4j start
      Linux: sudo neo4j start
      ```

## 项目结构

```
cyber-doctor/
├── .env                            # 环境配置文件，存储API密钥、模型配置等敏感信息
├── .env.example                    # 环境配置文件示例，展示需要配置的环境变量
├── .gitignore                      # Git版本控制忽略文件配置
├── LICENSE                         # 项目许可证文件
├── README.md                       # 项目中文说明文档
├── README_en.md                    # 项目英文说明文档
├── __init__.py                     # Python包初始化文件
├── app.py                          # 项目启动文件，构建Gradio界面，处理多模态信息，可自定义ASR模型和界面
├── env.py                          # 封装读取.env文件的接口
├── requirements.txt                # 项目依赖包列表
├── Internet/                       # 联网搜索相关功能模块
│   ├── __init__.py                   # 包初始化文件
│   ├── Internet_chain.py             # 联网搜索链，协调关键词提取、搜索爬取和检索过程
│   ├── Internet_prompt.py            # 大模型特征工程，提取搜索关键词
│   └── retrieve_Internet.py          # 调用model/Internet接口检索搜索结果
├── README/                         # 存放项目文档相关资源
├── audio/                          # 音频处理相关功能模块
│   ├── __init__.py                   # 包初始化文件
│   ├── audio_extract.py              # 大模型特征工程，提取TTS目标文本和语种
│   └── audio_generate.py             # 封装调用edge-tts语音合成接口
├── client/                         # 大模型客户端模块，作为用户与API的桥梁
│   ├── __init__.py                   # 包初始化文件
│   ├── LLMclientbase.py              # 大模型客户端基类定义
│   ├── LLMclientgeneric.py           # 封装调用大模型API接口进行对话生成的通用函数
│   ├── clientfactory.py              # 封装构建不同大模型客户端的工厂类
│   ├── ourAPI/                       # 自定义API接口实现
│   │   ├── __init__.py                 # 包初始化文件
│   │   └── client.py                   # 自定义API客户端实现
│   └── zhipuAPI/                     # 智谱AI API接口实现
│       ├── __init__.py                 # 包初始化文件
│       └── client.py                   # 智谱AI客户端实现
├── config/                         # 配置文件目录
│   ├── __init__.py                   # 包初始化文件
│   ├── config-web.yaml               # 不同(Web)开发环境下的应用配置文件
│   └── config.py                     # 配置加载和处理模块
├── kg/                             # 知识图谱相关功能模块
│   └── Graph.py                      # 知识图谱对象实现
├── model/                          # 检索功能使用到的模型相关功能模块，包括联网RAG、知识库RAG、知识图谱RAG
│   ├── __init__.py                   # 包初始化文件
│   ├── model_base.py                 # 模型基类定义
│   ├── Internet/                     # 联网RAG向量库实现
│   │   ├── __init__.py                 # 包初始化文件
│   │   ├── Internet_model.py           # 构建联网RAG向量库
│   │   └── Internet_service.py         # 联网RAG向量库接口
│   ├── KG/                           # 知识图谱RAG的匹配自动机实现
│   │   ├── __init__.py                 # 包初始化文件
│   │   ├── data_utils.py               # 知识图谱数据处理工具
│   │   ├── search_model.py             # 构建知识图谱RAG的匹配自动机
│   │   └── search_service.py           # 知识图谱RAG的匹配自动机接口
│   └── RAG/                          # 知识库RAG向量库实现
│       ├── __init__.py                 # 包初始化文件
│       ├── retrieve_model.py           # 构建知识库RAG向量库
│       └── retrieve_service.py         # 知识库RAG向量库接口
├── ppt_docx/                       # PPT和Word文档生成模块
│   ├── docx_content.py               # 大模型生成Word内容
│   ├── docx_generation.py            # Word内容转换为Word文档
│   ├── ppt_content.py                # 大模型生成PPT内容
│   └── ppt_generation.py             # PPT内容转换为PPT文档
├── qa/                             # 问答系统核心模块
│   ├── __init__.py                   # 包初始化文件
│   ├── answer.py                     # 根据问题类型选择对应的工具函数生成回答
│   ├── function_tool.py              # 工具函数集合
│   ├── prompt_templates.py           # 提示词模板定义
│   ├── purpose_type.py               # 问题类型定义
│   └── question_parser.py            # 问题类型解析判断
├── rag/                            # 检索增强生成模块
│   ├── __init__.py                   # 包初始化文件
│   ├── rag_chain.py                  # RAG链式调用实现
│   └── retrieve/                     # 检索功能实现
│       ├── __init__.py                 # 包初始化文件
│       └── retrieve_document.py        # 文档检索实现
└── resource/                       # 资源文件目录，存放图片等静态资源
```

## 项目现状

项目从原本Django+vue框架中分离，在开发时我们是设计了一个简单的前后端框架和界面的。可以提供简单的登录、注册、创建用户自己的知识库和可交互的对知识库进行增删改查的功能。但由于该部分不是本人负责，我对如何教大家如何配置该部分代码还不是很懂，各位如果希望本项目能提供相关功能，欢迎反馈，我再对项目进行更新。

你可能发现了本项目类似一个大杂烩，将众多功能缝合到了一起。但其实在单独的每个功能实现上，还有很大的优化空间。

例如对知识图谱的处理，目前只是匹配所有实体和与该实体直接相连的关系。其实可以增添对关系类型的判断等，优化知识图谱对大模型输出的影响，避免干扰大模型的输出。这些将在我有时间的时候进行更新，也欢迎你的意见与建议，敬请期待吧。

## 贡献者

感谢以下成员对项目的贡献

团队成员：

- [YM](https://github.com/YM556)
- [L-MARK](https://github.com/L-MARK)
- [Goku-30](https://github.com/Goku-30)
- [laobaishui](https://github.com/laobaishui)

开源领域大神（除了我）：

<a href="https://github.com/Warma10032/cyber-doctor/contributors">
  <img src="https://contrib.rocks/image?repo=Warma10032/cyber-doctor" /></a>

## 参考项目

本项目参考了以下开源项目，感谢他／她们的付出

- [meet-libai](https://github.com/BinNong/meet-libai)

## Star History

<a href="https://star-history.com/#warma10032/cyber-doctor&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=warma10032/cyber-doctor&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=warma10032/cyber-doctor&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=warma10032/cyber-doctor&type=Date" />
 </picture>
</a>
