"""
RAG 系统评测脚本
用法: python -m backend.evaluate
"""
import asyncio
import json
import httpx
from pathlib import Path

from .settings import DATA_DIR

API_BASE = "http://127.0.0.1:8000"

async def evaluate_retrieval(test_cases_path: str = str(DATA_DIR / "eval_test_cases.json")):
    test_cases = json.loads(Path(test_cases_path).read_text(encoding="utf-8"))

    precision_scores = []
    recall_scores = []
    f1_scores = []

    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        for case in test_cases:
            question = case["question"]
            relevant = set(case["relevant_chunks"])

            # 调用检索接口
            resp = await client.post("/retrieve", json={"question": question, "top_k": 3})
            if resp.status_code != 200:
                print(f"Error retrieving: {resp.text}")
                continue
            results = resp.json()["results"]

            # 假设每个结果都有 metadata.chunk_id，我们提取它们
            retrieved_ids = set()
            for r in results:
                # chunk_id 存储在 metadata 中，注意它可能是字符串
                cid = r["metadata"].get("chunk_id", None)
                if cid is not None:
                    retrieved_ids.add(int(cid))   # Chroma metadata 会存成字符串，需要转换

            # 计算 precision / recall
            true_positive = len(retrieved_ids & relevant)
            precision = true_positive / len(retrieved_ids) if retrieved_ids else 0.0
            recall = true_positive / len(relevant) if relevant else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            precision_scores.append(precision)
            recall_scores.append(recall)
            f1_scores.append(f1)

            print(f"\n问题: {question}")
            print(f"  相关chunks: {relevant}")
            print(f"  检索到: {retrieved_ids}")
            print(f"  Precision={precision:.2f}, Recall={recall:.2f}, F1={f1:.2f}")

    avg_prec = sum(precision_scores) / len(precision_scores) if precision_scores else 0
    avg_rec = sum(recall_scores) / len(recall_scores) if recall_scores else 0
    avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0

    print("\n=== 检索质量报告 ===")
    print(f"平均 Precision: {avg_prec:.2f}")
    print(f"平均 Recall:    {avg_rec:.2f}")
    print(f"平均 F1:        {avg_f1:.2f}")

async def evaluate_answer_quality(test_cases_path: str = str(DATA_DIR / "eval_test_cases.json")):
    """
    评估生成答案的忠实度（简化版）：检查答案中是否包含引用编号，以及是否包含‘资料库中未找到’这类词语。
    更完整的评估需要 LLM-as-a-Judge，我们放到以后。
    """
    test_cases = json.loads(Path(test_cases_path).read_text(encoding="utf-8"))

    async with httpx.AsyncClient(base_url=API_BASE, timeout=60.0) as client:
        for case in test_cases:
            question = case["question"]
            resp = await client.post("/ask", json={"question": question, "top_k": 3})
            if resp.status_code != 200:
                print(f"Error asking: {resp.text}")
                continue
            data = resp.json()
            answer = data["answer"]
            # 简单检查：
            has_citation = "根据[" in answer or "[1]" in answer
            is_not_found = "未找到" in answer or "抱歉" in answer
            print(f"\n问题: {question}")
            print(f"  答案: {answer[:100]}...")
            print(f"  包含引用: {has_citation}")
            print(f"  知识库未找到: {is_not_found}")

async def main():
    print("开始评测检索质量...")
    await evaluate_retrieval()
    print("\n开始评测生成答案...")
    await evaluate_answer_quality()

if __name__ == "__main__":
    asyncio.run(main())