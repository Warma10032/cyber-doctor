# fetch_messages.py
import pymysql
from .config_loader import config

def get_db_connection():
    return pymysql.connect(
        host=config.get("DJANGO_DB_HOST"),
        user=config.get("DJANGO_DB_USER"),
        password=config.get("DJANGO_DB_PASSWORD"),
        database=config.get("DJANGO_DB_NAME"),
        port=config.get("DJANGO_DB_PORT"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def fetch_messages_by_uid(uid: str, limit: int = None) -> list:
    """
    查询指定用户的所有消息（含 message_id 和 message_text）
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT m.message_id, m.message_text
        FROM message m
        JOIN conversation c ON m.conversation_id = c.conversation_id
        WHERE c.uid = %s
        ORDER BY m.created_at ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query, (uid,))
        return cursor.fetchall()
