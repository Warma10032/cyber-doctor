# test_load_model.py
from transformers import BertTokenizer, BertForSequenceClassification

model_dir = "/Users/ycz/cyber-doctor/demo 2/saved_model"

try:
    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = BertForSequenceClassification.from_pretrained(model_dir)
    print("✅ 模型加载成功！")
except Exception as e:
    print(f"❌ 加载失败: {e}")
