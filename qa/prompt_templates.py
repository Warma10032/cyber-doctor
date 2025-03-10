from qa.purpose_type import purpose_map

purpose_type_template = (
    f"你扮演文本分类的工具助手，类别有{len(purpose_map)}种，"
    f"分别为：文本生成,图片生成,视频生成,音频生成,图片描述,问候语,PPT生成,Word生成,网络搜索,基于知识库,基于知识图谱,其他。"
    f"下面给出一些例子用来辅助你判别："
    f"'我想了解糖尿病' ，文本分类结果是文本生成；"
    f"'请生成老年人练习太极的图片'，文本分类结果是图片生成；"
    f"'你可以生成一段关于春天的视频吗'，文本分类结果是视频生成；"
    f"'请将上述文本转换成语音'，文本分类结果是音频生成；"
    f"'糖尿病如何治疗？请用语音回答'，文本分类结果是音频生成；"
    f"'请你描述这张美丽的图片'，文本分类结果是图片描述；"
    f"'您好！你是谁？',文本分类结果是问候语；"
    f"'请你用制作一份关于糖尿病的PPT',文本分类结果是PPT生成；"
    f"'请你用word制作一份关于糖尿病的报告',文本分类结果是Word生成；"
    f"'请在互联网上找到养生保健的相关知识',文本分类结果是网络搜索；"
    f"'知识库中有什么糖尿病相关的知识',文本分类结果是基于知识库；"
    f"'知识图谱中有什么糖尿病相关的知识',文本分类结果是基于知识图谱；"
    f"'我有糖尿病，帮我制定一个饮食锻炼计划' ，文本分类结果是文本生成；"
    f"如果以上内容没有对应的类别，文本分类结果是其他。"
    f"请参考上面例子，直接给出一种分类结果，不要解释，不要多余的内容，不要多余的符号，不要多余的空格，不要多余的空行，不要多余的换行，不要多余的标点符号。"
    f"请你对以下内容进行文本分类："
)


def get_question_parser_prompt(text: str) -> str:
    """
    根据输入的文本生成prompt
    :param text: 输入的文本
    :return: prompt
    """
    return f"{purpose_type_template} {text}"
