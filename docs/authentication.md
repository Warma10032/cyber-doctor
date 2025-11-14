# Django 认证服务与 Gradio 集成指南

本项目新增了一个基于 **Django + JWT** 的认证服务，并将其与 Gradio 前端完成了整合。本文档介绍从环境配置到运行的完整流程，以及主要 API 的使用方式。

## 1. 环境准备

1. 安装新增依赖（若使用 `requirements.txt`，请重新安装一次依赖）：

   ```bash
   pip install -r requirements.txt
   ```

   关键新依赖：

   - `PyJWT`：生成与校验 JWT
   - `redis`：刷新令牌与黑名单存储（未配置 `REDIS_URL` 时会自动降级到本地 JSON 文件）

2. 配置 `.env`：

   ```ini
   # Django 认证服务
   DJANGO_SECRET_KEY=请修改为随机值
   DJANGO_DEBUG=false
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
   # DJANGO_DB_PATH=authserver/db.sqlite3  # 可选自定义数据库路径

   # JWT
   JWT_SECRET_KEY=请修改为随机值
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_LIFETIME_MINUTES=60
   REFRESH_TOKEN_LIFETIME_DAYS=7
   AUTH_TOKEN_NAMESPACE=cyber_doctor          # Redis key 前缀
   REDIS_URL=redis://127.0.0.1:6379/0         # 若不配置则使用文件降级

   # Gradio 前端调用地址
   AUTH_SERVER_BASE_URL=http://127.0.0.1:8000
   ```

   `.env.example` 已更新，可参考后拷贝。

3. 初始化数据库并启动 Django 认证服务：

   ```bash
   # 第一次运行需要迁移数据库
   python3 authserver/manage.py migrate

   # 启动服务（默认监听 8000 端口）
   python3 authserver/manage.py runserver 0.0.0.0:8000
   ```

   > 可选：`python3 authserver/manage.py createsuperuser` 创建后台账号，访问 `/admin/` 进行用户管理。

4. Redis（可选但推荐）：

   - 启动本地 Redis：`docker run -p 6379:6379 redis:7`
   - 或者配置云端 Redis，将连接串写入 `REDIS_URL`
   - 如果未配置，项目会退化到 `authserver/token_store.json` 持久化刷新令牌与黑名单（单机开发模式可接受）

## 2. 认证服务接口

服务统一挂载在 `/auth/` 路径下，返回 JSON。

| HTTP 方法 | 路径           | 说明                               |
| --------- | -------------- | ---------------------------------- |
| POST      | `/auth/register/` | 注册账号（`username`、`password`） |
| POST      | `/auth/login/`    | 登录，返回 `access_token` / `refresh_token` 及剩余秒数 |
| POST      | `/auth/refresh/`  | 使用 `refresh_token` 续签，默认轮换刷新令牌 |
| POST      | `/auth/logout/`   | 注销，需携带 `Authorization: Bearer <access>`，并在 body 中传 `refresh_token`（若有） |
| GET       | `/auth/me/`       | 获取当前用户信息，需要 `Authorization` 头部 |

### Token 生命周期

- Access Token：默认 60 分钟
- Refresh Token：默认 7 天
- 登出或刷新时会自动吊销旧 Refresh Token
- 可通过 `ACCESS_TOKEN_LIFETIME_MINUTES` / `REFRESH_TOKEN_LIFETIME_DAYS` 调整

## 3. Gradio 前端联动

- `app.py` 在界面顶部新增了登录面板（注册 / 登录 / 刷新 / 退出）
- 登录成功后：
  - 前端会保存 `auth_state`（包含用户信息与 token 生命周期）
  - 每次调用问答链时，会把 `user_id` 写入 `Retrievemodel.INSTANCE.set_user_id`
  - 由于 RAG 向量库原本就以 `user_data/<user_id>` 分区，登录后各用户互不干扰
- Access Token 过期后需要手动刷新，刷新失败会自动清空登录状态

## 4. 运行顺序建议

1. 启动 Redis（可选）
2. 启动 Django 认证服务
3. 启动 Gradio 前端：`python3 app.py`
4. 在界面顶部完成注册 / 登录后，再使用知识库上传与问答功能

## 5. 常见问题

| 现象                         | 排查建议                                                |
| ---------------------------- | ------------------------------------------------------- |
| 登录提示 “无法连接认证服务” | 确认 `AUTH_SERVER_BASE_URL` 是否正确、服务是否已启动   |
| 刷新失败自动退出登录         | `refresh_token` 已过期或被吊销，需要重新登录           |
| 未配置 Redis 仍能运行        | 已回退到 `token_store.json`，仅适用于单机开发环境      |
| 想自定义端口                 | 修改 `AUTH_SERVER_BASE_URL` 与 `runserver` 监听端口     |

如需进一步扩展（如角色权限、邮件找回等），可继续基于 `authserver/users/views.py` 与 `core` 目录进行开发。
