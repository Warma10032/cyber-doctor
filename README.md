项目背景：

当前多模态大语言模型不断发展，在许多领域都有了不错的应用。我们小组基于东南大学暑期实训课程，开发了一个医疗健康领域的多模态大模型，这个大模型的目标用户是所有对自己健康关心的人。

使用方法

填写必要设置：填写setting.py中的数据库设置、新建.env填入大模型api、填写config/config-local.yaml中的配置文件

运行manage.py `python manage.py runserver`启动后端

报错可能：

1. Django数据库模型更改后需要进行迁移（请搜索如何操作）
2. 端口占用，会使用到mysql 3306端口、Django 8000端口、grodio 7860端口
