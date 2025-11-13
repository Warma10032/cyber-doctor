# predict_finetuned.py
from transformers import BertTokenizer, BertForSequenceClassification
import torch
import json
import os

# ===== 配置常量 =====
SAVED_MODEL_DIR = "./saved_model"  # 根据你的实际路径调整
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MAX_LEN = 128

# Load label list
try:
    with open(f"{SAVED_MODEL_DIR}/label_classes.json", "r", encoding="utf-8") as f:
        LABELS = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("label_classes.json not found. Please run train.py first.")

def get_major_category(label: str) -> str:
    """根据标签返回大类（示例，按需修改）"""
    category_map = {
        "糖尿病": "内分泌疾病",
        "高血压": "心血管疾病",
        "冠心病": "心血管疾病",
        "胃炎": "消化系统疾病",
        # ... 添加你的映射
    }
    return category_map.get(label, "其他")

class MedTagPredictor:
    def __init__(self, model_dir=SAVED_MODEL_DIR):
        self.tokenizer = BertTokenizer.from_pretrained(model_dir)
        self.model = BertForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()
        self.model.to(DEVICE)
        print(f"Model loaded successfully, running on {DEVICE}")

    def predict(self, text, top_k=3):
        if not text or not text.strip():
            return []
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=MAX_LEN
        ).to(DEVICE)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.sigmoid(outputs.logits).cpu().numpy()[0]

        topk_idx = probs.argsort()[-top_k:][::-1]
        results = [
            {"label": LABELS[i], "score": round(float(probs[i]), 4)}
            for i in topk_idx if probs[i] >= 0.05
        ]
        return results

    def predict_with_hierarchy(self, text, top_k=3):
        raw_preds = self.predict(text, top_k=top_k)
        enhanced = []
        for r in raw_preds:
            major = get_major_category(r['label'])
            enhanced.append({
                "label": r['label'],
                "score": r['score'],
                "category": major
            })
        return enhanced

    # ===== 新增：批量预测 =====
    def predict_batch(self, texts, top_k=3):
        return [self.predict(text, top_k) for text in texts]
