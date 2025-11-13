# tag_user_messages.py
import os
import sys
import json
import pymysql
from .fetch_messages import fetch_messages_by_uid
from .predict_finetuned import MedTagPredictor
from .config_loader import config

# 添加项目根目录到 Python 路径（确保能导入 config）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_connection():
    return pymysql.connect(
        host=config.get("DJANGO_DB_HOST"),
        user=config.get("DJANGO_DB_USER"),
        password=config.get("DJANGO_DB_PASSWORD"),
        database=config.get("DJANGO_DB_NAME"),
        port=config.get("DJANGO_DB_PORT"),
        charset='utf8mb4'
    )

def clear_old_labels_for_user(uid: str):
    """清理该用户旧的标签（避免重复）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 获取该用户所有 message_id
        cursor.execute("""
            SELECT m.message_id 
            FROM message m
            JOIN conversation c ON m.conversation_id = c.conversation_id
            WHERE c.uid = %s
        """, (uid,))
        message_ids = [row[0] for row in cursor.fetchall()]
        
        if message_ids:
            # 删除旧标签
            cursor.execute(
                "DELETE FROM message_label WHERE message_id IN %s",
                (tuple(message_ids),)
            )
            conn.commit()
            print(f"🧹 Cleared {cursor.rowcount} old labels for user {uid}")

def save_labels_to_db(message_labels: list):
    """批量插入新标签"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO message_label (message_id, label, score)
        VALUES (%s, %s, %s)
        """
        records = []
        for item in message_labels:
            for label_info in item["labels"]:
                records.append((
                    item["message_id"],
                    label_info["label"],
                    label_info["score"]
                ))
        
        if records:
            cursor.executemany(insert_query, records)
            conn.commit()
            print(f"✅ Inserted {len(records)} new labels into message_label table.")
        else:
            print("⚠️ No labels to insert.")

def main():
    # 从命令行获取 uid，或使用默认值
    uid = sys.argv[1] if len(sys.argv) > 1 else "test_user_uid"
    
    print(f"🚀 Starting tagging for user: {uid}")
    
    # 1. 清理旧标签
    clear_old_labels_for_user(uid)
    
    # 2. 获取消息
    messages = fetch_messages_by_uid(uid, limit=100)
    print(f"📥 Fetched {len(messages)} messages.")
    
    if not messages:
        print("❌ No messages found for this user.")
        return
    
    # 3. BERT 预测
    predictor = MedTagPredictor()
    texts = [msg["message_text"] for msg in messages]
    predictions = predictor.predict_batch(texts, top_k=3)
    
    # 4. 构建结果
    output = []
    for msg, preds in zip(messages, predictions):
        output.append({
            "message_id": msg["message_id"],
            "message_text": msg["message_text"],
            "labels": preds
        })
    
    # 5. 保存 JSON
    os.makedirs("results", exist_ok=True)
    json_path = f"results/user_{uid}_tags.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 Results saved to {json_path}")
    
    # 6. 写入数据库
    save_labels_to_db(output)
    
    print("\n🎉 Tagging completed successfully!")

if __name__ == "__main__":
    main()
