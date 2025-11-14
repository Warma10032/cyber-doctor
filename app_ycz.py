import base64
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import PyPDF2
import chardet
import gradio as gr
import httpx
import mimetypes
import speech_recognition as sr
from docx import Document
from icecream import ic
from opencc import OpenCC
from pydub import AudioSegment

from audio.audio_generate import audio_generate
from client.clientfactory import Clientfactory
from env import get_env_value
from model.RAG.retrieve_model import INSTANCE as RAG_INSTANCE
from qa.answer import get_answer
from qa.function_tool import process_image_describe_tool
from qa.purpose_type import userPurposeType
from qa.question_parser import parse_question


AVATAR = ("resource/user.png", "resource/bot.jpg")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

AUTH_STORAGE_KEY = "cyber-doctor-auth"

# 修改全局的 JS_SAVE_AUTH 常量
JS_SAVE_AUTH = f"""
function(auth_state) {{
    console.log('[JS] Saving auth_state:', auth_state);
    // 在 window 上也存一份，供其他地方使用
    if (auth_state) {{
        window.__auth_state__ = auth_state;
        console.log('[JS] Stored in window.__auth_state__');
    }}
    
    if (auth_state && auth_state.user) {{
        const dataStr = JSON.stringify(auth_state);
        localStorage.setItem('{AUTH_STORAGE_KEY}', dataStr);
        console.log('[JS] ✓ Auth saved to localStorage, user:', auth_state.user.account);
    }} else {{
        localStorage.removeItem('{AUTH_STORAGE_KEY}');
        console.log('[JS] Auth cleared from localStorage');
    }}
    return auth_state;
}}
"""


JS_LOAD_AUTH = f"""
function() {{
    const raw = localStorage.getItem('{AUTH_STORAGE_KEY}');
    if (!raw) {{
        return null;
    }}
    try {{
        return JSON.parse(raw);
    }} catch (err) {{
        console.warn('Failed to parse auth state from storage', err);
        localStorage.removeItem('{AUTH_STORAGE_KEY}');
        return null;
    }}
}}
"""

JS_SAVE_AUTH_TEXT = f"""
function(value) {{
    if (value && value !== "null" && value !== "") {{
        localStorage.setItem('{AUTH_STORAGE_KEY}', value);
    }} else {{
        localStorage.removeItem('{AUTH_STORAGE_KEY}');
    }}
    return value;
}}
"""

APP_CSS = """
#auth-modal, #register-modal, #account-modal {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    z-index: 1000;
}
#auth-card, #register-card, #account-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    box-shadow: 0 10px 20px rgba(0,0,0,0.08);
    width: min(480px, 96vw);
    padding: 20px;
}
#auth-modal .gr-box, #auth-modal .gr-block, #auth-modal .gr-group,
#register-modal .gr-box, #register-modal .gr-block, #register-modal .gr-group,
#account-modal .gr-box, #account-modal .gr-block, #account-modal .gr-group {
    border-radius: 12px;
    padding: 24px;
}
#register-link {
    background: transparent;
    border: none;
    color: #2563eb;
    text-decoration: underline;
    font-size: 0.9rem;
    width: auto;
    padding: 4px 0;
}
#register-link:hover {
    color: #1d4ed8;
}
#layout {
    min-height: 100vh;
}
#sidebar {
    background: #4169E1;  /* 宝蓝色侧边栏 */
    padding: 16px;
    gap: 12px;
    border-right: 1px solid #e5e7eb;
}
#sidebar .gr-button, #sidebar .gr-select, #sidebar .gr-radio {
    width: 100%;
}
#sidebar-toggle {
    width: 48px;
}
/* AI医生标题 - 黑色 */
#sidebar-title h2 {
    color: #000000 !important;
}
/* 历史会话标题 - 黑色 */
#history-title h4 {
    color: #000000 !important;
}
/* 当前用户信息 - 黑色 */
#user-info {
    color: #000000 !important;
}
#user-info p,
#user-info strong {
    color: #000000 !important;
}
"""




TITLE_SYSTEM_PROMPT = (
    "你是一名医疗问答助手，需要根据首轮对话内容生成8-16字的会话主题，"
    "语言保持中文，突出健康/医疗意图，不要包含序号、引号或表情。"
)
TITLE_MAX_LENGTH = 30
TITLE_MIN_LENGTH = 4
DEFAULT_SESSION_TITLE = "新会话"
AUTO_REFRESH_THRESHOLD = 60  # 自动刷新判定阈值（秒）

_title_client = None

# pip install whisper
# pip install openai-whisper
# pip install soundfile
# pip install pydub
# pip install opencc-python-reimplemented


def convert_to_simplified(text):
    converter = OpenCC("t2s")
    return converter.convert(text)


def convert_audio_to_wav(audio_file_path):
    audio = AudioSegment.from_file(audio_file_path)  # 自动识别格式
    wav_file_path = audio_file_path.rsplit(".", 1)[0] + ".wav"  # 生成 WAV 文件路径
    audio.export(wav_file_path, format="wav")  # 将音频文件导出为 WAV 格式
    return wav_file_path


def audio_to_text(audio_file_path):
    # 创建识别器对象
    # 如果不是 WAV 格式，先转换为 WAV
    if not audio_file_path.endswith(".wav"):
        audio_file_path = convert_audio_to_wav(audio_file_path)

    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        # 使用 Google Web Speech API 进行语音识别，不用下载模型但对网络要求高
        # text = recognizer.recognize_google(audio_data, language="zh-CN")
        # 使用 whisper 进行语音识别，自动下载模型到本地
        text = recognizer.recognize_whisper(audio_data, language="zh")
        text_simplified = convert_to_simplified(text)
    return text_simplified

def close_modal_handler():
    """关闭模态框处理函数"""
    print("[DEBUG] close_modal_handler() called")
    ic("Closing modal")
    return gr.update(visible=False)

# pip install PyPDF2
def pdf_to_str(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def docx_to_str(file_path):
    doc = Document(file_path)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)
    return "\n".join(text)


# pip install chardet
def text_file_to_str(text_file):
    with open(text_file, "rb") as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result["encoding"]

    # 使用检测到的编码来读取文件
    with open(text_file, "r", encoding=encoding) as file:
        return file.read()


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


def _auth_base_url() -> str:
    base = get_env_value("AUTH_SERVER_BASE_URL") or "http://127.0.0.1:8000"
    return base.rstrip("/")


def _chat_base_url() -> str:
    return f"{_auth_base_url()}/chat"


def _shop_base_url() -> str:
    base = os.getenv("SHOP_BASE_URL") or "http://127.0.0.1:8001"
    return f"{base.rstrip('/')}/chatbot/"


def _default_auth_state() -> Dict[str, Any]:
    return {
        "user": None,
        "access_token": None,
        "refresh_token": None,
        "access_expires_at": 0.0,
        "refresh_expires_at": 0.0,
    }


def _is_logged_in(auth_state: Dict[str, Any]) -> bool:
    if not auth_state:
        return False
    if not auth_state.get("user"):
        return False
    expiry = auth_state.get("access_expires_at", 0.0)
    return expiry > time.time()


def _auth_status_message(auth_state: Dict[str, Any]) -> str:
    if _is_logged_in(auth_state):
        user = auth_state.get("user") or {}
        remaining = max(int(auth_state["access_expires_at"] - time.time()), 0)
        username = user.get("account") or user.get("username") or user.get("uid") or "用户"
        return f"当前用户：**{username}**"
    return "当前用户：未登录"


def _http_request(
    url: str,
    *,
    method: str = "POST",
    json_data: Dict[str, Any] | None = None,
    token: str | None = None,
) -> Tuple[bool, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.request(
            method,
            url,
            json=json_data,
            headers=headers,
            timeout=10,
            proxies=None,
        )
    except Exception as exc:  # pragma: no cover
        return False, f"无法连接服务：{exc}"

    if response.status_code >= 400:
        try:
            data = response.json()
            detail = data.get("detail") or data
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        return False, detail

    if response.status_code == 204 or not response.content:
        return True, {}

    try:
        return True, response.json()
    except ValueError:
        return False, "服务返回了无效的 JSON 响应"


def _auth_request(
    path: str,
    *,
    method: str = "POST",
    json_data: Dict[str, Any] | None = None,
    token: str | None = None,
) -> Tuple[bool, Any]:
    url = f"{_auth_base_url()}/auth/{path.lstrip('/')}"
    return _http_request(url, method=method, json_data=json_data, token=token)


def _chat_request(
    path: str,
    *,
    method: str = "GET",
    json_data: Dict[str, Any] | None = None,
    token: str | None = None,
) -> Tuple[bool, Any]:
    url = f"{_chat_base_url()}/{path.lstrip('/')}"
    return _http_request(url, method=method, json_data=json_data, token=token)


def _shop_request(
    path: str,
    *,
    method: str = "GET",
    json_data: Dict[str, Any] | None = None,
    token: str | None = None,
) -> Tuple[bool, Any]:
    url = f"{_shop_base_url()}/{path.lstrip('/')}"
    return _http_request(url, method=method, json_data=json_data, token=token)


def _should_auto_migrate() -> bool:
    return (os.getenv("AUTO_MIGRATE", "true").lower() in {"1", "true", "yes", "on"})


def ensure_database() -> None:
    if not _should_auto_migrate():
        return

    manage_py = Path(__file__).resolve().parent / "authserver" / "manage.py"
    if not manage_py.exists():
        print("[auto-migrate] manage.py not found, skip database migration.")
        return

    cmd = [sys.executable, str(manage_py), "migrate", "--noinput"]
    print("[auto-migrate] Running Django migrations...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print("[auto-migrate] Migration failed.")
        if exc.stdout:
            print(exc.stdout.strip())
        if exc.stderr:
            print(exc.stderr.strip())
        return

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    print("[auto-migrate] Migration completed.")


def _state_from_login_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    now = time.time()
    return {
        "user": data.get("user"),
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "access_expires_at": now + float(data.get("access_expires_in", 0)),
        "refresh_expires_at": now + float(data.get("refresh_expires_in", 0)),
    }


def _auto_refresh_auth_state(auth_state: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    auth_state = auth_state or _default_auth_state()
    now = time.time()
    refresh_token = auth_state.get("refresh_token")
    if not refresh_token:
        if auth_state.get("access_expires_at", 0.0) <= now:
            return _default_auth_state(), bool(auth_state.get("user"))
        return auth_state, False

    refresh_exp = auth_state.get("refresh_expires_at", 0.0)
    if refresh_exp <= now:
        return _default_auth_state(), True

    access_exp = auth_state.get("access_expires_at", 0.0)
    if access_exp > now + AUTO_REFRESH_THRESHOLD:
        return auth_state, False

    success, payload = _auth_request(
        "refresh/",
        json_data={"refresh_token": refresh_token},
    )
    if not success:
        print(f"[auth] auto refresh failed: {payload}")
        return _default_auth_state(), True

    return _state_from_login_payload(payload), True


def prepare_auth_state_on_load(auth_state: Dict[str, Any] | None) -> Dict[str, Any]:
    state = auth_state or _default_auth_state()
    new_state, _ = _auto_refresh_auth_state(state)
    return new_state


def _resolve_user_id(auth_state: Dict[str, Any]) -> str:
    if _is_logged_in(auth_state):
        user = auth_state.get("user") or {}
        candidate = user.get("uid") or user.get("id")
        if candidate:
            return str(candidate)
    return "guest"


def _prepare_user_context(auth_state: Dict[str, Any] | None) -> Dict[str, Any]:
    if not auth_state:
        auth_state = _default_auth_state()
    user_id = _resolve_user_id(auth_state)
    RAG_INSTANCE.set_user_id(user_id)
    return auth_state


def _serialize_auth_state(auth_state: Dict[str, Any] | None) -> str:
    return json.dumps(auth_state or _default_auth_state())


def _format_currency(value: Any) -> str:
    try:
        return f"¥{float(value):.2f}"
    except (TypeError, ValueError):
        return "¥0.00"


def load_cart_panel(auth_state: Dict[str, Any] | None):
    auth_state = auth_state or _default_auth_state()
    if not _is_logged_in(auth_state):
        return "请先登录后查看购物车。", [], "合计：¥0.00"

    success, payload = _shop_request(
        "shop/api/cart/",
        method="GET",
        token=auth_state.get("access_token"),
    )
    if not success:
        return f"加载购物车失败：{payload}", [], "合计：¥0.00"

    rows = []
    for item in payload.get("items", []):
        rows.append(
            [
                item.get("name") or "-",
                item.get("quantity") or 0,
                _format_currency(item.get("price")),
                _format_currency(item.get("subtotal")),
                item.get("added_at") or "",
            ]
        )

    total = _format_currency(payload.get("total", 0))
    return "", rows, f"合计：{total}"


def load_orders_panel(auth_state: Dict[str, Any] | None):
    auth_state = auth_state or _default_auth_state()
    if not _is_logged_in(auth_state):
        return "请先登录后查看订单。", []

    success, payload = _shop_request(
        "shop/api/orders/",
        method="GET",
        token=auth_state.get("access_token"),
    )
    if not success:
        return f"加载订单失败：{payload}", []

    rows = []
    for order in payload.get("orders", []):
        rows.append(
            [
                order.get("order_number"),
                order.get("status_display") or order.get("status"),
                _format_currency(order.get("total_amount")),
                order.get("created_at") or "",
                len(order.get("items") or []),
            ]
        )
    return "", rows


def refresh_shop_panels(auth_state: Dict[str, Any] | None):
    cart_msg, cart_rows, cart_total = load_cart_panel(auth_state)
    orders_msg, orders_rows = load_orders_panel(auth_state)
    return cart_msg, cart_rows, cart_total, orders_msg, orders_rows


def reset_cart_panel():
    return "请先登录后查看购物车。", [], "合计：¥0.00"


def reset_orders_panel():
    return "请先登录后查看订单。", []


def _default_chat_state() -> Dict[str, Any]:
    return {
        "session_id": None,
        "sessions": [],
        "loaded": False,
        "session_options": {},
        "title_generated": {},
    }


def _title_map(chat_state: Dict[str, Any]) -> Dict[str, bool]:
    mapping = chat_state.get("title_generated")
    if not isinstance(mapping, dict):
        mapping = {}
        chat_state["title_generated"] = mapping
    return mapping


def _mark_session_title_status(chat_state: Dict[str, Any], conversation: Dict[str, Any]) -> None:
    conv_id = conversation.get("conversation_id")
    if not conv_id:
        return
    mapping = _title_map(chat_state)
    raw_title = (conversation.get("title") or "").strip()
    if not raw_title or raw_title == DEFAULT_SESSION_TITLE:
        mapping.setdefault(conv_id, False)
    else:
        mapping[conv_id] = True


def _set_title_generated(chat_state: Dict[str, Any], session_id: str, value: bool) -> None:
    mapping = _title_map(chat_state)
    mapping[session_id] = value


def _should_generate_title(chat_state: Dict[str, Any], session_id: str | None) -> bool:
    if not session_id:
        return False
    mapping = _title_map(chat_state)
    return not mapping.get(session_id, False)


def _update_local_session_title(chat_state: Dict[str, Any], session_id: str, title: str) -> None:
    sessions = chat_state.get("sessions") or []
    for conv in sessions:
        if conv.get("conversation_id") == session_id:
            conv["title"] = title
            break


DEFAULT_SESSION_TITLE = "新会话"


def _format_session_title(conv: Dict[str, Any]) -> str:
    title = (conv.get("title") or "").strip()
    return title or DEFAULT_SESSION_TITLE


def _conversation_key(conversation: Dict[str, Any]) -> str | None:
    conv_id = conversation.get("conversation_id") or conversation.get("id")
    return conv_id


def _normalize_conversation(conversation: Dict[str, Any]) -> Dict[str, Any] | None:
    conv_id = _conversation_key(conversation)
    if not conv_id:
        return None
    return {
        "conversation_id": conv_id,
        "uid": conversation.get("uid") or conversation.get("user_id"),
        "title": conversation.get("title") or "",
        "created_at": conversation.get("created_at"),
        "updated_at": conversation.get("updated_at"),
    }


def _normalize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    sender = message.get("sender")
    if isinstance(sender, bool):
        sender = "user" if sender else "assistant"
    text = message.get("message_text")
    if text is None:
        text = message.get("content") or ""
    return {
        "message_id": message.get("message_id") or message.get("id"),
        "sender": sender,
        "message_text": text,
        "created_at": message.get("created_at"),
        "model_id": message.get("model_id"),
    }


def _merge_session(chat_state: Dict[str, Any], conversation: Dict[str, Any]) -> None:
    sessions: List[Dict[str, Any]] = chat_state.get("sessions", [])
    existing = {item["conversation_id"]: item for item in sessions if item.get("conversation_id")}
    conv_id = conversation.get("conversation_id")
    if not conv_id:
        return
    existing[conv_id] = conversation
    _mark_session_title_status(chat_state, conversation)
    # 最新的会话放前面
    chat_state["sessions"] = sorted(
        existing.values(),
        key=lambda item: item.get("updated_at") or "",
        reverse=True,
    )


def _session_selector_update(chat_state: Dict[str, Any]) -> gr.update:
    sessions = chat_state.get("sessions") or []
    options: Dict[str, str] = {}
    choices: List[str] = []
    for conv in sessions:
        base_label = _format_session_title(conv)
        label = base_label
        suffix = 2
        while label in options:
            label = f"{base_label} #{suffix}"
            suffix += 1
        conv_id = conv.get("conversation_id") or conv.get("id")
        if not conv_id:
            continue
        options[label] = conv_id
        choices.append(label)

    chat_state["session_options"] = options
    selected_label: str | None = None
    current_id = chat_state.get("session_id")
    if current_id:
        for label, sid in options.items():
            if sid == current_id:
                selected_label = label
                break
    if selected_label is None and choices:
        selected_label = choices[0]
        chat_state["session_id"] = options[selected_label]

    return gr.update(
        choices=choices,
        value=selected_label,
        interactive=bool(sessions),
    )


def load_sessions(
    auth_state: Dict[str, Any] | None,
    chat_state: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], gr.update]:
    auth_state = auth_state or _default_auth_state()
    chat_state = chat_state or _default_chat_state()
    if not _is_logged_in(auth_state):
        chat_state = _default_chat_state()
        return chat_state, gr.update(choices=[], value=None, interactive=False)

    success, payload = _chat_request("sessions/", token=auth_state.get("access_token"))
    if not success:
        chat_state["sessions"] = []
        chat_state["session_id"] = None
        chat_state["session_options"] = {}
        return (
            chat_state,
            gr.update(choices=[], value=None, interactive=False),
        )

    raw_sessions = payload.get("sessions") or []
    normalized_sessions: List[Dict[str, Any]] = []
    for conv in raw_sessions:
        normalized = _normalize_conversation(conv)
        if normalized:
            normalized_sessions.append(normalized)

    chat_state["sessions"] = normalized_sessions
    for conv in normalized_sessions:
        _mark_session_title_status(chat_state, conv)
    chat_state["loaded"] = True

    current_id = chat_state.get("session_id")
    if not current_id and normalized_sessions:
        current_id = normalized_sessions[0]["conversation_id"]
    chat_state["session_id"] = current_id

    update = _session_selector_update(chat_state)
    return chat_state, update


def _messages_to_history(messages: List[Dict[str, Any]]) -> List[List[Any]]:
    history: List[List[Any]] = []
    for msg in messages:
        sender = msg.get("sender")
        content = msg.get("message_text") or msg.get("content")
        if sender == "user":
            history.append([content, None])
        elif sender == "assistant":
            if history and history[-1][1] in {None, ""}:
                history[-1][1] = content
            else:
                history.append([None, content])
    return history


def load_messages(
    auth_state: Dict[str, Any] | None,
    chat_state: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], gr.update]:
    auth_state = auth_state or _default_auth_state()
    chat_state = chat_state or _default_chat_state()

    session_id = chat_state.get("session_id")
    if not _is_logged_in(auth_state) or not session_id:
        return chat_state, gr.update(value=[])

    success, payload = _chat_request(
        f"sessions/{session_id}/messages/",
        token=auth_state.get("access_token"),
    )
    if not success:
        return chat_state, gr.update(value=[])

    raw_messages = payload.get("messages") or []
    normalized_messages = [_normalize_message(msg) for msg in raw_messages]
    chat_state["messages"] = normalized_messages
    history = _messages_to_history(normalized_messages)
    return chat_state, gr.update(value=history)


def _create_session(
    auth_state: Dict[str, Any] | None,
    chat_state: Dict[str, Any] | None,
    title: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    auth_state = auth_state or _default_auth_state()
    chat_state = chat_state or _default_chat_state()
    if not _is_logged_in(auth_state):
        return chat_state, None

    payload: Dict[str, Any] = {}
    if title:
        payload["title"] = title
    success, data = _chat_request(
        "sessions/",
        method="POST",
        json_data=payload,
        token=auth_state.get("access_token"),
    )
    if not success:
        return chat_state, None

    normalized = _normalize_conversation(data)
    if not normalized:
        return chat_state, None

    chat_state["session_id"] = normalized["conversation_id"]
    _merge_session(chat_state, normalized)
    return chat_state, normalized


def ensure_session(
    auth_state: Dict[str, Any] | None,
    chat_state: Dict[str, Any] | None,
    *,
    title: str | None = None,
) -> Tuple[Dict[str, Any], str | None]:
    chat_state = chat_state or _default_chat_state()
    if chat_state.get("session_id"):
        return chat_state, chat_state["session_id"]
    chat_state, conversation = _create_session(auth_state, chat_state, title=title)
    session_id = conversation["conversation_id"] if conversation else None
    chat_state["session_id"] = session_id
    return chat_state, session_id


def set_active_session(
    chat_state: Dict[str, Any] | None,
    session_id: str | None,
) -> Dict[str, Any]:
    chat_state = chat_state or _default_chat_state()
    chat_state["session_id"] = session_id
    return chat_state


def save_message(
    auth_state: Dict[str, Any] | None,
    session_id: str,
    sender: str,
    content: str,
    *,
    model_id: int | None = None,
) -> None:
    auth_state = auth_state or _default_auth_state()
    if not _is_logged_in(auth_state):
        return
    payload: Dict[str, Any] = {
        "sender": sender,
        "message_text": content,
        "content": content,
    }
    if model_id is not None:
        payload["model_id"] = model_id
    _chat_request(
        f"sessions/{session_id}/messages/",
        method="POST",
        json_data=payload,
        token=auth_state.get("access_token"),
    )


def _message_content_for_storage(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else ""
    return str(value)


def _get_title_client():
    global _title_client
    if _title_client is None:
        try:
            _title_client = Clientfactory().get_client()
        except Exception as exc:  # pragma: no cover - graceful degradation
            print(f"[title] 初始化模型失败: {exc}")
            _title_client = None
    return _title_client


def _clean_title_text(text: str) -> str:
    normalized = (text or "").strip()
    normalized = re.sub(r"[\r\n\t]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[\"'“”‘’`]+", "", normalized)
    if len(normalized) > TITLE_MAX_LENGTH:
        normalized = normalized[:TITLE_MAX_LENGTH]
    return normalized


def _fallback_title(user_text: str) -> str:
    fallback = (user_text or "新会话").strip()
    if not fallback:
        fallback = "新会话"
    fallback = re.sub(r"\s+", " ", fallback)
    if len(fallback) > TITLE_MAX_LENGTH:
        fallback = fallback[:TITLE_MAX_LENGTH]
    return fallback


def _generate_session_title_summary(user_text: str, assistant_text: str) -> str:
    fallback = _fallback_title(user_text)
    client = _get_title_client()
    if not client:
        return fallback

    content = (
        "请根据下面的用户提问与助手回答，总结一个中文会话主题。"
        "要求突出医疗或健康意图，8-16个字以内，不要出现标点或序号。\n"
        f"用户提问：{user_text[:400]}\n"
        f"助手回答：{assistant_text[:400]}"
    )

    try:
        response = client.chat_using_messages(
            [
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ]
        )
    except Exception as exc:  # pragma: no cover
        print(f"[title] 生成失败: {exc}")
        return fallback

    cleaned = _clean_title_text(response or "")
    if len(cleaned) < TITLE_MIN_LENGTH:
        return fallback
    return cleaned


def _update_remote_session_title(
    auth_state: Dict[str, Any], session_id: str, title: str
) -> bool:
    if not _is_logged_in(auth_state):
        return False
    success, payload = _chat_request(
        f"sessions/{session_id}/",
        method="PATCH",
        json_data={"title": title},
        token=auth_state.get("access_token"),
    )
    if not success:
        print(f"[title] 更新会话标题失败: {payload}")
        return False
    return True


def _maybe_generate_session_title(
    auth_state: Dict[str, Any],
    chat_state: Dict[str, Any],
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    if not _should_generate_title(chat_state, session_id):
        return
    user_message = (user_message or "").strip()
    assistant_message = (assistant_message or "").strip()
    if not user_message:
        return
    summary = _generate_session_title_summary(user_message, assistant_message)
    if not summary:
        return
    if _update_remote_session_title(auth_state, session_id, summary):
        _set_title_generated(chat_state, session_id, True)
        _update_local_session_title(chat_state, session_id, summary)


def reset_chat_ui() -> Tuple[Dict[str, Any], gr.update, gr.update]:
    chat_state = _default_chat_state()
    return (
        chat_state,
        gr.update(choices=[], value=None, interactive=False),
        gr.update(value=[]),
    )


def update_new_session_button(auth_state: Dict[str, Any] | None) -> gr.update:
    is_logged_in = _is_logged_in(auth_state or {})
    return gr.update(interactive=is_logged_in)


def auth_status_output(auth_state: Dict[str, Any] | None) -> str:
    return _auth_status_message(auth_state or _default_auth_state())


def maybe_close_modal(auth_state: Dict[str, Any] | None) -> gr.Column:
    if _is_logged_in(auth_state or {}):
        return gr.update(visible=False)
    return gr.update()


def show_modal() -> gr.update:
    return gr.update(visible=True)


def hide_modal() -> gr.update:
    print("[DEBUG] hide_modal() called")
    ic("hide_modal called")
    return gr.update(visible=False)



def update_user_panel(
    auth_state: Dict[str, Any] | None,
) -> Tuple[str, gr.update, gr.update, gr.update]:
    auth_state = auth_state or _default_auth_state()
    if _is_logged_in(auth_state):
        user = auth_state.get("user") or {}
        username = user.get("account") or user.get("username") or user.get("uid") or "已登录用户"
        info = f"👤 当前用户：**{username}**"
        return (
            info,
            gr.update(visible=False),
            gr.update(value="账户", visible=True),
            gr.update(visible=True),
        )
    return (
        "👤 当前用户：未登录",
        gr.update(value="登录", visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def toggle_sidebar(
    sidebar_open: bool | None,
) -> Tuple[bool, gr.update, gr.update]:
    current = True if sidebar_open is None else bool(sidebar_open)
    new_state = not current
    return (
        new_state,
        gr.update(visible=new_state),
        gr.update(value="◀" if new_state else "▶"),
    )


def new_session_action(
    auth_state: Dict[str, Any] | None,
    chat_state: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], gr.update, gr.update]:
    chat_state = chat_state or _default_chat_state()
    if not _is_logged_in(auth_state):
        chat_state = _default_chat_state()
        return chat_state, gr.update(interactive=False), gr.update(value=[])

    chat_state, conversation = _create_session(auth_state, chat_state)
    if conversation:
        chat_state["session_id"] = conversation["conversation_id"]
    return chat_state, _session_selector_update(chat_state), gr.update(value=[])


def select_session_action(
    auth_state: Dict[str, Any] | None,
    chat_state: Dict[str, Any] | None,
    selected_label: str | None = None,
) -> Tuple[Dict[str, Any], gr.update]:
    chat_state = chat_state or _default_chat_state()
    session_id = (chat_state.get("session_options") or {}).get(selected_label)
    chat_state = set_active_session(chat_state, session_id)
    return load_messages(auth_state, chat_state)


def login_action(auth_state: Dict[str, Any], username: str, password: str):
    auth_state = auth_state or _default_auth_state()
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return (
            auth_state,
            _auth_status_message(auth_state),
            "请输入用户名和密码。",
            gr.update(),
        )

    success, payload = _auth_request(
        "login/",
        json_data={"username": username, "password": password},
    )
    if not success:
        return (
            auth_state,
            _auth_status_message(auth_state),
            f"登录失败：{payload}",
            gr.update(value=""),
        )

    new_state = _state_from_login_payload(payload)
    return (
        new_state,
        _auth_status_message(new_state),
        "登录成功。",
        gr.update(value=""),
    )


def open_register_modal_action() -> Tuple[gr.update, gr.update]:
    return gr.update(visible=True), gr.update(visible=False)


def close_register_modal_action() -> Tuple[gr.update, gr.update]:
    return gr.update(visible=False), gr.update(visible=True)


def register_action_ext(
    account: str,
    password: str,
    nickname: str,
    email: str,
    wx_id: str,
    phone_number: str,
) -> str:
    account = (account or "").strip()
    password = password or ""
    if not account or not password:
        return "注册失败：账号与密码不能为空。"

    payload = {
        "username": account,
        "password": password,
        "nickname": (nickname or "").strip(),
        "email": (email or "").strip(),
        "wx_id": (wx_id or "").strip(),
        "phone_number": (phone_number or "").strip(),
    }
    success, resp = _auth_request("register/", json_data=payload)
    if not success:
        return f"注册失败：{resp}"
    return f"注册成功：{account}，请返回登录窗口。"


def open_account_modal_action(
    auth_state: Dict[str, Any] | None,
) -> Tuple[
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    str,
    gr.update,
]:
    auth_state = auth_state or _default_auth_state()
    default_result = (
        gr.update(visible=False),
        gr.update(value="", interactive=False),
        gr.update(value="", interactive=False),
        gr.update(value="", interactive=False),
        gr.update(value="", interactive=False),
        gr.update(value="", interactive=False),
        gr.update(value="", interactive=False),
        "请先登录后再查看账户信息。",
        gr.update(interactive=False),
    )

    if not _is_logged_in(auth_state):
        return default_result

    success, payload = _auth_request(
        "me/",
        method="GET",
        token=auth_state.get("access_token"),
    )
    if not success:
        return (
            gr.update(visible=False),
            *default_result[1:7],
            f"加载账户信息失败：{payload}",
            gr.update(interactive=False),
        )

    def _field(key: str) -> str:
        return (payload or {}).get(key) or ""

    return (
        gr.update(visible=True),
        gr.update(value=_field("account"), interactive=False),
        gr.update(value=_field("uid"), interactive=False),
        gr.update(value=_field("nickname"), interactive=False),
        gr.update(value=_field("email"), interactive=False),
        gr.update(value=_field("wx_id"), interactive=False),
        gr.update(value=_field("phone_number"), interactive=False),
        "",
        gr.update(interactive=False),
    )


def enable_account_edit_action() -> Tuple[
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
]:
    editable = gr.update(interactive=True)
    return (
        editable,
        editable,
        editable,
        editable,
        gr.update(interactive=True),
    )


def save_account_profile_action(
    auth_state: Dict[str, Any] | None,
    nickname: str,
    email: str,
    wx_id: str,
    phone_number: str,
) -> Tuple[
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    str,
    gr.update,
]:
    auth_state = auth_state or _default_auth_state()
    if not _is_logged_in(auth_state):
        return (
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            "请先登录后再修改信息。",
            gr.update(interactive=False),
        )

    payload = {
        "nickname": (nickname or "").strip(),
        "email": (email or "").strip(),
        "wx_id": (wx_id or "").strip(),
        "phone_number": (phone_number or "").strip(),
    }
    success, resp = _auth_request(
        "me/",
        method="PATCH",
        json_data=payload,
        token=auth_state.get("access_token"),
    )
    if not success:
        editable = gr.update(interactive=True)
        return (
            editable,
            editable,
            editable,
            editable,
            f"更新失败：{resp}",
            gr.update(interactive=True),
        )

    def _field(key: str) -> str:
        return (resp or {}).get(key) or ""

    return (
        gr.update(value=_field("nickname"), interactive=False),
        gr.update(value=_field("email"), interactive=False),
        gr.update(value=_field("wx_id"), interactive=False),
        gr.update(value=_field("phone_number"), interactive=False),
        "信息已更新。",
        gr.update(interactive=False),
    )


def hide_account_modal_action() -> gr.update:
    return gr.update(visible=False)


def logout_action(auth_state: Dict[str, Any] | None):
    auth_state = auth_state or _default_auth_state()
    if _is_logged_in(auth_state):
        _auth_request(
            "logout/",
            json_data={"refresh_token": auth_state.get("refresh_token")},
            token=auth_state.get("access_token"),
        )
    new_state = _default_auth_state()
    return new_state, _auth_status_message(new_state), "已退出登录。"


# 核心函数
def grodio_view(chatbot, chat_input, auth_state, chat_state):

    auth_state = _prepare_user_context(auth_state)
    chat_state = chat_state or _default_chat_state()

    sessions_update = gr.update()
    session_before = chat_state.get("session_id")
    chat_state, session_id = ensure_session(
        auth_state,
        chat_state,
    )
    if session_id and session_id != session_before:
        sessions_update = _session_selector_update(chat_state)

    # 用户消息立即显示
    user_message = chat_input["text"]
    bot_response = "loading..."
    chatbot.append([user_message, bot_response])
    yield chatbot, auth_state, chat_state, sessions_update

    sessions_update = gr.update()

    # 处理用户上传的文件
    files = chat_input["files"]
    audios = []
    images = []
    pdfs = []
    docxs = []
    texts = []

    for file in files:
        file_type, _ = mimetypes.guess_type(file)
        if file_type.startswith("audio/"):
            audios.append(file)
        elif file_type.startswith("image/"):
            images.append(file)
        elif file_type.startswith("application/pdf"):
            pdfs.append(file)
        elif file_type.startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            docxs.append(file)
        elif file_type.startswith("text/"):
            texts.append(file)
        else:
            user_message += "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'该文件为不支持的文件类型'"
            print(f"Unknown file type: {file_type}")

    # 图片文件解析
    # if images != []:
    #     image_url = images
    #     image_base64 = [image_to_base64(image) for image in image_url]

    #     for i, image in enumerate(image_base64):
    #         chatbot[-1][
    #             0
    #         ] += f"""
    #             <div>
    #                 <img src="data:image/png;base64,{image}" alt="Generated Image" style="max-width: 100%; height: auto; cursor: pointer;" />
    #             </div>
    #             """
    #         yield chatbot, auth_state
    # else:
    #     image_url = None
    image_url = images if images else None

    question_type = parse_question(user_message, image_url)
    ic(question_type)

    # 音频文件解析
    if audios != []:
        for i, audio in enumerate(audios):
            audio_message = audio_to_text(audio)
            if audio_message == "":
                user_message += "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'音频识别失败，请稍后再试'"
            elif "作曲" in audio_message:
                user_message += "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'不好意思，我无法理解音乐'"
            else:
                user_message += f"音频{i+1}内容：{audio_message}"

    if pdfs != []:
        for i, pdf in enumerate(pdfs):
            pdf_text = pdf_to_str(pdf)
            user_message += f"PDF{i+1}内容：{pdf_text}"

    if docxs != []:
        for i, docx in enumerate(docxs):
            docx_text = docx_to_str(docx)
            user_message += f"DOCX{i+1}内容：{docx_text}"

    if texts != []:
        for i, text in enumerate(texts):
            text_string = text_file_to_str(text)
            user_message += f"文本{i+1}内容：{text_string}"

    if user_message == "":
        user_message = "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'请问您有什么想了解的，我将尽力为您服务'"
    answer = get_answer(user_message, chatbot, question_type, image_url)
    bot_response = ""

    if session_id and user_message:
        save_message(
            auth_state,
            session_id,
            "user",
            user_message,
        )

    # 处理文本生成/其他/文档检索/知识图谱检索
    if (
        answer[1] == userPurposeType.text
        or answer[1] == userPurposeType.RAG
        or answer[1] == userPurposeType.KnowledgeGraph
    ):
        # 流式输出
        for chunk in answer[0]:
            bot_response = bot_response + (chunk.choices[0].delta.content or "")
            chatbot[-1][1] = bot_response
            yield chatbot, auth_state, chat_state, sessions_update

    # 处理图片生成
    if answer[1] == userPurposeType.ImageGeneration:
        image_url = answer[0]
        describe = process_image_describe_tool(
            question_type=userPurposeType.ImageDescribe,
            question="描述这个图片，不要识别‘AI生成’",
            history="",
            image_url=[image_url],
        )
        combined_message = f"""
            **生成的图片:**
            ![Generated Image]({image_url})
            {describe[0]}
            """
        chatbot[-1][1] = combined_message
        bot_response = combined_message
        yield chatbot, auth_state, chat_state, sessions_update

    # 处理图片描述
    if answer[1] == userPurposeType.ImageDescribe:
        # answer[0] 应该是文字描述（不是 Base64）
        description = answer[0]
        # 如果需要显示原图 + 描述
        if image_url:
            # 上传原图到 OSS 获取公网 URL
            from qa.utils.oss_uploader import upload_image_to_oss
            oss_urls = []
            for img_path in image_url:
                oss_url = upload_image_to_oss(img_path)
                if oss_url:
                    oss_urls.append(oss_url)
            
            # 构建响应：图片 + 描述
            image_html = ""
            for url in oss_urls:
                image_html += f'<img src="{url}" style="max-width: 100%; height: auto;" />'
            
            bot_response = f"{image_html}\n\n{description}"
            chatbot[-1][1] = bot_response
        else:
            # 纯文字描述
            bot_response = description
            chatbot[-1][1] = bot_response
        
        yield chatbot, auth_state, chat_state, sessions_update

    # 处理视频
    if answer[1] == userPurposeType.Video:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "抱歉，视频生成失败，请稍后再试"
        bot_response = chatbot[-1][1]
        yield chatbot, auth_state, chat_state, sessions_update

    # 处理PPT
    if answer[1] == userPurposeType.PPT:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "抱歉，PPT生成失败，请稍后再试"
        bot_response = chatbot[-1][1]
        yield chatbot, auth_state, chat_state, sessions_update

    # 处理Docx
    if answer[1] == userPurposeType.Docx:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "抱歉，文档生成失败，请稍后再试"
        bot_response = chatbot[-1][1]
        yield chatbot, auth_state, chat_state, sessions_update

    # 处理音频生成
    if answer[1] == userPurposeType.Audio:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "抱歉，音频生成失败，请稍后再试"
        bot_response = chatbot[-1][1]
        yield chatbot, auth_state, chat_state, sessions_update

    # 处理联网搜索
    if answer[1] == userPurposeType.InternetSearch:
        if answer[3] == False:
            output_message = (
                "由于网络问题，访问互联网失败，下面由我根据现有知识给出回答："
            )
        else:
            # 将字典中的内容转换为 Markdown 格式的链接
            links = "\n".join(f"[{title}]({link})" for link, title in answer[2].items())
            links += "\n"
            output_message = f"参考资料：{links}"
        for i in range(0, len(output_message)):
            bot_response = output_message[: i + 1]
            chatbot[-1][1] = bot_response
            yield chatbot, auth_state, chat_state, sessions_update
        for chunk in answer[0]:
            bot_response = bot_response + (chunk.choices[0].delta.content or "")
            chatbot[-1][1] = bot_response
            yield chatbot, auth_state, chat_state, sessions_update

    if session_id:
        save_message(
            auth_state,
            session_id,
            "assistant",
            _message_content_for_storage(bot_response),
        )
        _maybe_generate_session_title(
            auth_state,
            chat_state,
            session_id,
            user_message,
            _message_content_for_storage(bot_response),
        )
        chat_state, sessions_update = load_sessions(auth_state, chat_state)

    yield chatbot, auth_state, chat_state, sessions_update


def gradio_audio_view(chatbot, audio_input, auth_state, chat_state):

    auth_state = _prepare_user_context(auth_state)
    chat_state = chat_state or _default_chat_state()

    sessions_update = gr.update()
    session_before = chat_state.get("session_id")
    chat_state, session_id = ensure_session(auth_state, chat_state)
    if session_id and session_id != session_before:
        sessions_update = _session_selector_update(chat_state)

    # 用户消息立即显示
    if audio_input is None:
        user_message = ""
    else:
        user_message = (audio_input, "audio")
    chatbot.append([user_message, "loading..."])
    yield chatbot, auth_state, chat_state, sessions_update

    sessions_update = gr.update()

    if audio_input is None:
        audio_message = "无音频"
    else:
        audio_message = audio_to_text(audio_input)

    chatbot[-1][0] = audio_message

    user_message = ""
    if audio_message == "无音频":
        user_message = "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'欢迎与我对话，我将用语音回答您'"
    elif audio_message == "":
        user_message = "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'音频识别失败，请稍后再试'"
    elif "作曲 作曲" in audio_message:
        user_message = "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'不好意思，我无法理解音乐'"
    else:
        user_message = audio_message

    if not user_message:
        user_message = "请你将下面的句子修饰后输出，不要包含额外的文字，句子:'请问您有什么想了解的，我将尽力为您服务'"

    question_type = parse_question(user_message)
    ic(question_type)
    answer = get_answer(user_message, chatbot, question_type)

    if session_id and user_message:
        save_message(
            auth_state,
            session_id,
            "user",
            user_message,
        )

    bot_response = ""
    assistant_content: Any = ""

    # 处理文本生成/其他/文档检索/知识图谱检索
    if (
        answer[1] == userPurposeType.text
        or answer[1] == userPurposeType.RAG
        or answer[1] == userPurposeType.KnowledgeGraph
    ):
        for chunk in answer[0]:
            chunk_content = chunk.choices[0].delta.content or ""
            bot_response += chunk_content
        try:
            assistant_content = (
                audio_generate(
                    text=bot_response,
                    model_name="zh-CN-YunxiNeural",
                ),
                "audio",
            )
        except Exception as exc:
            print(f"音频生成失败，直接返回文本: {exc}")
            assistant_content = bot_response

    elif answer[1] == userPurposeType.ImageGeneration:
        image_url = answer[0]
        describe = process_image_describe_tool(
            question_type=userPurposeType.ImageDescribe,
            question="描述这个图片，不要识别‘AI生成’",
            history=" ",
            image_url=[image_url],
        )
        assistant_content = f"""
            **生成的图片:**
            ![Generated Image]({image_url})
            {describe[0]}
            """
        bot_response = describe[0]

    elif answer[1] == userPurposeType.Video:
        assistant_content = answer[0] or "抱歉，视频生成失败，请稍后再试"
        bot_response = _message_content_for_storage(assistant_content)

    elif answer[1] == userPurposeType.PPT:
        assistant_content = answer[0] or "抱歉，PPT生成失败，请稍后再试"
        bot_response = _message_content_for_storage(assistant_content)

    elif answer[1] == userPurposeType.Docx:
        assistant_content = answer[0] or "抱歉，文档生成失败，请稍后再试"
        bot_response = _message_content_for_storage(assistant_content)

    elif answer[1] == userPurposeType.Audio:
        assistant_content = answer[0] or "抱歉，音频生成失败，请稍后再试"
        bot_response = _message_content_for_storage(assistant_content)

    elif answer[1] == userPurposeType.InternetSearch:
        if answer[3] == False:
            bot_response = "由于网络问题，访问互联网失败，下面由我根据现有知识给出回答："
        for chunk in answer[0]:
            chunk_content = chunk.choices[0].delta.content or ""
            bot_response += chunk_content
        try:
            assistant_content = (
                audio_generate(
                    text=bot_response,
                    model_name="zh-CN-YunxiNeural",
                ),
                "audio",
            )
        except Exception as exc:
            print(f"音频生成失败，直接返回文本: {exc}")
            assistant_content = bot_response

    else:
        bot_response = bot_response or "处理完成"
        assistant_content = bot_response

    if isinstance(assistant_content, str):
        bot_response = assistant_content
    chatbot[-1][1] = assistant_content

    if session_id:
        save_message(
            auth_state,
            session_id,
            "assistant",
            _message_content_for_storage(bot_response or assistant_content),
        )
        _maybe_generate_session_title(
            auth_state,
            chat_state,
            session_id,
            user_message,
            _message_content_for_storage(bot_response or assistant_content),
        )
        chat_state, sessions_update = load_sessions(auth_state, chat_state)

    yield chatbot, auth_state, chat_state, sessions_update


def _find_available_port(host: str, desired_port: int | None, max_attempts: int = 20) -> Tuple[int | None, bool]:
    """
    Return a usable port.

    If desired_port <= 0 or None, instruct Gradio to auto-pick.
    Otherwise probe forward until an available port is found.
    """
    if desired_port is None or desired_port <= 0:
        return None, False

    for offset in range(max_attempts):
        candidate = desired_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidate))
            except OSError:
                continue
        return candidate, offset != 0

    return None, True


# 切换到语音模式的函数
def toggle_voice_mode():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
    )


# 切换回文本模式的函数
def toggle_text_mode():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
    )


examples = [
    {"text": "您好", "files": []},
    {"text": "糖尿病的常见症状有哪些？", "files": []},
    {"text": "用语音重新回答我一次", "files": []},
    {"text": "帮我搜索一下养生知识", "files": []},
        {"text": "帮我生成一张老人练太极图片", "files": []},
    {
        "text": "帮我生成一份用于科普糖尿病发病原因，症状，治疗药物，预防措施的PPT",
        "files": [],
    },
    {"text": "请根据我给的参考资料，给我一个合理的饮食建议", "files": []},
    {"text": "请根据我给的参考资料，生成一个用于科普合理膳食的word", "files": []},
    {"text": "我最近想打太极养生，帮我生成一段老人打太极的视频吧", "files": []},
    {"text": "根据我的病历，给我一个合理的治疗方案", "files": []},
    {"text": "根据知识库介绍一下常见疾病", "files": []},
    {"text": "根据知识图谱告诉我糖尿病人适合吃的食物有哪些？", "files": []},
]


# 构建 Gradio 界面
with gr.Blocks(css=APP_CSS, analytics_enabled=False) as demo:
    auth_state = gr.State(_default_auth_state())
    auth_state_json = gr.Textbox(value="", visible=False)
    chat_state = gr.State(_default_chat_state())
    sidebar_state = gr.State(True)

<<<<<<< HEAD
    with gr.Column(visible=False, elem_id="auth-modal") as auth_modal:
        # 登录弹窗卡片容器，所有控件都放在卡片内，避免按钮漂浮在遮罩层上
        with gr.Group(elem_id="auth-card"):
            gr.Markdown("### 登录账户")
=======
    # 修改 auth_modal 的初始化
    with gr.Column(visible=False, elem_id="auth-modal", scale=0) as auth_modal:
        with gr.Group():
            gr.Markdown("### 账户中心")
>>>>>>> fbffb89 (ycz:图生文修复)
            username_input = gr.Textbox(
                label="账号", placeholder="请输入账号", lines=1
            )
            password_input = gr.Textbox(
                label="密码", placeholder="请输入密码", type="password", lines=1
            )
            with gr.Row():
                login_button = gr.Button("登录", variant="primary")
                close_modal_button = gr.Button("关闭", variant="secondary")
            register_link_button = gr.Button("注册账号", elem_id="register-link")
            auth_feedback = gr.Markdown("")

<<<<<<< HEAD
    with gr.Column(visible=False, elem_id="register-modal") as register_modal:
        # 注册弹窗卡片容器
        with gr.Group(elem_id="register-card"):
            gr.Markdown("### 注册新账户")
            register_account_input = gr.Textbox(label="账号", placeholder="请输入账号")
            register_nickname_input = gr.Textbox(label="昵称（可选）", placeholder="可留空")
            register_email_input = gr.Textbox(label="邮箱", placeholder="example@domain.com")
            register_password_input = gr.Textbox(
                label="密码", placeholder="请设置密码", type="password"
            )
            register_wx_input = gr.Textbox(label="微信号", placeholder="可留空")
            register_phone_input = gr.Textbox(label="手机号", placeholder="可留空")
            with gr.Row():
                register_submit_button = gr.Button("提交注册", variant="primary")
                register_back_button = gr.Button("返回登录", variant="secondary")
            register_feedback = gr.Markdown("")

    with gr.Column(visible=False, elem_id="account-modal") as account_modal:
        # 账户信息弹窗卡片容器
        with gr.Group(elem_id="account-card"):
            gr.Markdown("### 账户信息")
            account_account_display = gr.Textbox(label="账号", interactive=False)
            account_uid_display = gr.Textbox(label="用户 ID", interactive=False)
            account_nickname_input = gr.Textbox(label="昵称", interactive=False)
            account_email_input = gr.Textbox(label="邮箱", interactive=False)
            account_wx_input = gr.Textbox(label="微信号", interactive=False)
            account_phone_input = gr.Textbox(label="手机号", interactive=False)
            with gr.Row():
                account_edit_button = gr.Button("修改信息", variant="secondary")
                account_save_button = gr.Button("保存信息", variant="primary", interactive=False)
                account_close_button = gr.Button("关闭", variant="secondary")
            account_feedback = gr.Markdown("")
=======
>>>>>>> fbffb89 (ycz:图生文修复)

    with gr.Row(elem_id="layout", equal_height=True):
        with gr.Column(elem_id="sidebar", scale=0, min_width=260) as sidebar_column:
            gr.Markdown("## 「AI医生」🩺", elem_id="sidebar-title")
            new_session_button = gr.Button(
                "＋ 新建会话", variant="secondary", interactive=False
            )
            gr.Markdown("#### 历史会话",elem_id="history-title")
            session_list = gr.Radio(
                choices=[],
                value=None,
                interactive=False,
                show_label=False,
            )
            gr.Markdown("---")
            user_info_md = gr.Markdown("👤 当前用户：未登录",elem_id="user-info")
            login_open_button = gr.Button("登录", variant="primary")
            account_button = gr.Button("账户", variant="secondary", visible=False)
            logout_button = gr.Button("退出登录", variant="secondary", visible=False)

        with gr.Column(elem_id="main", scale=1) as main_column:
            with gr.Row():
                sidebar_toggle_button = gr.Button(
                    "◀", elem_id="sidebar-toggle", variant="secondary"
                )
                auth_status = gr.Markdown(_auth_status_message(_default_auth_state()))
                shop_button = gr.Button("进入商店", variant="primary")
            chatbot = gr.Chatbot(
                height=600,
                avatar_images=AVATAR,
                show_copy_button=True,
                latex_delimiters=[
                    {"left": "\\(", "right": "\\)", "display": True},
                    {"left": "\\[", "right": "\\]", "display": True},
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": "$", "right": "$", "display": True},
                ],
                placeholder="\n## 欢迎与我对话 \n",
            )
            with gr.Row():
                with gr.Column(scale=9):
                    chat_input = gr.MultimodalTextbox(
                        interactive=True,
                        file_count="multiple",
                        placeholder="输入消息或上传文件...",
                        show_label=False,
                    )
                    audio_input = gr.Audio(
                        sources=["microphone", "upload"],
                        label="录音输入",
                        visible=False,
                        type="filepath",
                    )
                with gr.Column(scale=1):
                    clear = gr.ClearButton(
                        [chatbot, chat_input, audio_input], value="清除记录"
                    )
                    toggle_voice_button = gr.Button("语音对话模式", visible=True)
                    toggle_text_button = gr.Button("文本交流模式", visible=False)
                    submit_audio_button = gr.Button("发送", visible=False)

            with gr.Row() as example_row:
                gr.Examples(
                    examples=examples,
                    inputs=chat_input,
                    visible=True,
                    examples_per_page=15,
                )

            with gr.Accordion("商城（当前登录）", open=False):
                cart_refresh_button = gr.Button("刷新购物车", variant="secondary")
                cart_message = gr.Markdown("请先登录后查看购物车。")
                cart_table = gr.Dataframe(
                    headers=["商品", "数量", "单价", "小计", "添加时间"],
                    datatype=["str", "number", "str", "str", "str"],
                    value=[],
                    interactive=False,
                )
                cart_summary = gr.Markdown("合计：¥0.00")

                orders_refresh_button = gr.Button("刷新订单", variant="secondary")
                orders_message = gr.Markdown("请先登录后查看订单。")
                orders_table = gr.Dataframe(
                    headers=["订单号", "状态", "金额", "创建时间", "商品数"],
                    datatype=["str", "str", "str", "str", "number"],
                    value=[],
                    interactive=False,
                )

    # === 事件绑定 ===
    # 进入商店（SSO：自动登录；无 token 时仅打开商城并提示）
    shop_button.click(
        fn=None,
        inputs=[auth_state],
        outputs=None,
        js=(
            "(state) => {\n"
            f"  const raw = localStorage.getItem('{AUTH_STORAGE_KEY}');\n"
            "  let finalToken = (state && state.access_token) ? state.access_token : null;\n"
            "  if (!finalToken && raw) {\n"
            "    try { finalToken = (JSON.parse(raw) || {}).access_token || null; } catch (e) {}\n"
            "  }\n"
            f"  const base = '{_shop_base_url().rstrip('/')}/';\n"
            "  if (finalToken) {\n"
            "    window.open(base + 'shop/sso/?token=' + encodeURIComponent(finalToken), '_blank');\n"
            "  } else {\n"
            "    alert('请先在聊天界面登录，再进入商店。');\n"
            "    window.open(base, '_blank');\n"
            "  }\n"
            "}"
        ),
    )
    login_open_button.click(
        fn=show_modal,
        inputs=None,
        outputs=[auth_modal],
    )

<<<<<<< HEAD
    register_link_button.click(
        fn=open_register_modal_action,
        inputs=None,
        outputs=[register_modal, auth_modal],
    )

    register_back_button.click(
        fn=close_register_modal_action,
        inputs=None,
        outputs=[register_modal, auth_modal],
    )

    register_submit_button.click(
        fn=register_action_ext,
        inputs=[
            register_account_input,
            register_password_input,
            register_nickname_input,
            register_email_input,
            register_wx_input,
            register_phone_input,
        ],
        outputs=[register_feedback],
    )

=======
    # 修改 close_modal_button 的事件链
>>>>>>> fbffb89 (ycz:图生文修复)
    close_modal_button.click(
        fn=close_modal_handler,
        inputs=None,
        outputs=[auth_modal],
        js="""
        function() {
            console.log('[JS-DEBUG] === Close Modal - Force Hide ===');
            
            try {
                const mainModal = document.getElementById('auth-modal');
                if (mainModal) {
                    mainModal.style.cssText = 'display: none !important; visibility: hidden !important;';
                    console.log('[JS-DEBUG] ✓ Modal hidden');
                }
                
                document.body.style.overflow = 'auto';
                console.log('[JS-DEBUG] ✓ Close Modal Complete');
                
            } catch(error) {
                console.error('[JS-ERROR]', error);
            }
            
            return true;
        }
        """
    )

<<<<<<< HEAD
=======



    register_button.click(
        fn=register_action,
        inputs=[username_input, password_input],
        outputs=[auth_feedback],
    )

>>>>>>> fbffb89 (ycz:图生文修复)
    login_event = login_button.click(
        fn=login_action,
        inputs=[auth_state, username_input, password_input],
        outputs=[auth_state, auth_status, auth_feedback, password_input],
    )
    login_event = login_event.then(
        load_sessions,
        inputs=[auth_state, chat_state],
        outputs=[chat_state, session_list],
    )
    login_event = login_event.then(
        load_messages,
        inputs=[auth_state, chat_state],
        outputs=[chat_state, chatbot],
    )
    login_event.then(
        update_new_session_button,
        inputs=[auth_state],
        outputs=[new_session_button],
    )
    login_event.then(
        update_user_panel,
        inputs=[auth_state],
        outputs=[user_info_md, login_open_button, account_button, logout_button],
    )
    login_event.then(
        maybe_close_modal,
        inputs=[auth_state],
        outputs=[auth_modal],
    )
    login_event = login_event.then(
        _serialize_auth_state,
        inputs=[auth_state],
        outputs=[auth_state_json],
    )
    login_event.then(
        None,
        inputs=[auth_state_json],
        outputs=[auth_state_json],
        js=JS_SAVE_AUTH_TEXT,
    )
    login_event.then(
        load_cart_panel,
        inputs=[auth_state],
        outputs=[cart_message, cart_table, cart_summary],
    )
    login_event.then(
        load_orders_panel,
        inputs=[auth_state],
        outputs=[orders_message, orders_table],
    )

    logout_event = logout_button.click(
        fn=logout_action,
        inputs=[auth_state],
        outputs=[auth_state, auth_status, auth_feedback],
    )
    logout_event = logout_event.then(
        lambda: gr.update(visible=False),
        inputs=None,
        outputs=[auth_modal],
    )
    logout_event.then(
        reset_chat_ui,
        inputs=None,
        outputs=[chat_state, session_list, chatbot],
    )
    logout_event.then(
        update_new_session_button,
        inputs=[auth_state],
        outputs=[new_session_button],
    )
    logout_event.then(
        update_user_panel,
        inputs=[auth_state],
        outputs=[user_info_md, login_open_button, account_button, logout_button],
    )
    logout_event = logout_event.then(
        lambda: _serialize_auth_state(_default_auth_state()),
        inputs=None,
        outputs=[auth_state_json],
    )
    logout_event.then(
        None,
        inputs=[auth_state_json],
        outputs=[auth_state_json],
        js=JS_SAVE_AUTH_TEXT,
    )
    logout_event.then(
        reset_cart_panel,
        inputs=None,
        outputs=[cart_message, cart_table, cart_summary],
    )
    logout_event.then(
        reset_orders_panel,
        inputs=None,
        outputs=[orders_message, orders_table],
    )

    chat_input.submit(
        fn=grodio_view,
        inputs=[chatbot, chat_input, auth_state, chat_state],
        outputs=[chatbot, auth_state, chat_state, session_list],
    )

    session_list.change(
        fn=select_session_action,
        inputs=[auth_state, chat_state, session_list],
        outputs=[chat_state, chatbot],
    )

    new_session_button.click(
        fn=new_session_action,
        inputs=[auth_state, chat_state],
        outputs=[chat_state, session_list, chatbot],
    )

    cart_refresh_button.click(
        fn=load_cart_panel,
        inputs=[auth_state],
        outputs=[cart_message, cart_table, cart_summary],
    )

    orders_refresh_button.click(
        fn=load_orders_panel,
        inputs=[auth_state],
        outputs=[orders_message, orders_table],
    )

    account_button.click(
        fn=open_account_modal_action,
        inputs=[auth_state],
        outputs=[
            account_modal,
            account_account_display,
            account_uid_display,
            account_nickname_input,
            account_email_input,
            account_wx_input,
            account_phone_input,
            account_feedback,
            account_save_button,
        ],
    )

    account_edit_button.click(
        fn=enable_account_edit_action,
        inputs=None,
        outputs=[
            account_nickname_input,
            account_email_input,
            account_wx_input,
            account_phone_input,
            account_save_button,
        ],
    )

    account_save_button.click(
        fn=save_account_profile_action,
        inputs=[
            auth_state,
            account_nickname_input,
            account_email_input,
            account_wx_input,
            account_phone_input,
        ],
        outputs=[
            account_nickname_input,
            account_email_input,
            account_wx_input,
            account_phone_input,
            account_feedback,
            account_save_button,
        ],
    )

    account_close_button.click(
        fn=hide_account_modal_action,
        inputs=None,
        outputs=[account_modal],
    )

    sidebar_toggle_button.click(
        fn=toggle_sidebar,
        inputs=[sidebar_state],
        outputs=[sidebar_state, sidebar_column, sidebar_toggle_button],
    )

    load_event = demo.load(
        fn=None,
        inputs=None,
        outputs=[auth_state],
        js=JS_LOAD_AUTH,
    )
    load_event = load_event.then(
        prepare_auth_state_on_load,
        inputs=[auth_state],
        outputs=[auth_state],
    )
    load_event = load_event.then(
        None,
        inputs=[auth_state],
        outputs=[auth_state],
        js=JS_SAVE_AUTH,
    )
    load_event = load_event.then(
        auth_status_output,
        inputs=[auth_state],
        outputs=[auth_status],
    )
    load_event = load_event.then(
        update_new_session_button,
        inputs=[auth_state],
        outputs=[new_session_button],
    )
    load_event = load_event.then(
        update_user_panel,
        inputs=[auth_state],
        outputs=[user_info_md, login_open_button, account_button, logout_button],
    )
    load_event = load_event.then(
        load_sessions,
        inputs=[auth_state, chat_state],
        outputs=[chat_state, session_list],
    )
    load_event = load_event.then(
        load_messages,
        inputs=[auth_state, chat_state],
        outputs=[chat_state, chatbot],
    )
    load_event = load_event.then(
        _serialize_auth_state,
        inputs=[auth_state],
        outputs=[auth_state_json],
    )
    load_event.then(
        None,
        inputs=[auth_state_json],
        outputs=[auth_state_json],
        js=JS_SAVE_AUTH_TEXT,
    )
    load_event = load_event.then(
        load_cart_panel,
        inputs=[auth_state],
        outputs=[cart_message, cart_table, cart_summary],
    )
    load_event.then(
        load_orders_panel,
        inputs=[auth_state],
        outputs=[orders_message, orders_table],
    )

    toggle_voice_button.click(
        fn=toggle_voice_mode,
        inputs=None,
        outputs=[
            chat_input,
            audio_input,
            toggle_voice_button,
            toggle_text_button,
            submit_audio_button,
        ],
    )

    toggle_text_button.click(
        fn=toggle_text_mode,
        inputs=None,
        outputs=[
            chat_input,
            audio_input,
            toggle_voice_button,
            toggle_text_button,
            submit_audio_button,
        ],
    )

    submit_audio_button.click(
        fn=gradio_audio_view,
        inputs=[chatbot, audio_input, auth_state, chat_state],
        outputs=[chatbot, auth_state, chat_state, session_list],
    )


# 启动应用
def start_gradio():
    # 可通过环境变量控制对外访问与端口/分享：
    #   GRADIO_HOST: 监听地址，默认 127.0.0.1；设置为 0.0.0.0 可被局域网访问
    #   GRADIO_PORT: 端口号，默认 10032
    #   GRADIO_SHARE: 是否开启 gradio 公网临时分享，true/false，默认 false
    raw_port = os.getenv("GRADIO_PORT", "10032")
    try:
        desired_port = int(raw_port)
    except ValueError:
        desired_port = None

    host = os.getenv("GRADIO_HOST", "127.0.0.1")
    share = os.getenv("GRADIO_SHARE", "false").lower() == "true"
    selected_port, port_was_busy = _find_available_port(host, desired_port)
    if port_was_busy:
        fallback_text = selected_port if selected_port is not None else "auto"
        print(f"[gradio] Desired port {desired_port} is busy, switching to {fallback_text}")

    demo.launch(server_port=selected_port, server_name=host, share=share)


if __name__ == "__main__":
    ensure_database()
    start_gradio()
