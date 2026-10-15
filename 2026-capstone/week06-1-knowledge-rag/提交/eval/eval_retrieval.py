"""检索评测：不加载回答模型，只比较切分方式 × 检索方式在 questions.json 上的命中情况。

命中：top-k 中某个片段来自标注的资料，且原文匹配标注的正则（标题不参与匹配，保证两种切分公平）。
用法（在 提交/ 目录下）：python eval/eval_retrieval.py [--embed-device cuda]
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from course_agent import Encoder, KnowledgeBase  # noqa: E402

CONFIGS = [  # (名称, 切分, 检索)
    ("参考实现：字符窗口 240 + 向量", "window", "vector"),
    ("字符窗口 240 + 混合", "window", "hybrid"),
    ("标题/页切分 + 向量", "section", "vector"),
    ("标题/页切分 + BM25", "section", "bm25"),
    ("标题/页切分 + 混合(RRF)", "section", "hybrid"),
]


def is_gold(chunk, gold):
    return any(chunk["source"] == src and re.search(pattern, chunk["text"]) for src, pattern in gold)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed-device", default="cpu")
    parser.add_argument("--embedding-model", default=str(HERE.parent / "models/bge-small-zh-v1.5"))
    parser.add_argument("--out", type=Path, default=HERE.parent / "results/retrieval_eval")
    args = parser.parse_args()
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    encoder = Encoder(args.embedding_model, args.embed_device)
    rows, details = [], {}
    for name, chunker, mode in CONFIGS:
        kb = KnowledgeBase(HERE.parent / "knowledge", lambda: encoder, chunker=chunker, mode=mode)
        unreachable = [q["id"] for q in questions if not any(is_gold(c, q["gold"]) for c in kb.chunks)]
        ranks, per_q = [], {}
        for q in questions:
            ranked = kb.rank(q["question"])[:10]
            rank = next((r for r, (i, _) in enumerate(ranked, 1) if is_gold(kb.chunks[i], q["gold"])), None)
            ranks.append(rank)
            per_q[q["id"]] = {"rank": rank, "top2": [kb.chunks[i]["id"] for i, _ in ranked[:2]]}
        n = len(questions)
        hit = lambda k: sum(r is not None and r <= k for r in ranks) / n
        avg_len = sum(len(c["text"]) for c in kb.chunks) / len(kb.chunks)
        rows.append({"config": name, "chunks": len(kb.chunks), "avg_chars": round(avg_len),
                     "hit@1": hit(1), "hit@2": hit(2), "hit@4": hit(4),
                     "mrr@10": sum(1 / r for r in ranks if r) / n, "unreachable": unreachable})
        details[name] = per_q
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps({"summary": rows, "per_question": details},
                                                        ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["| 配置 | 片段数 | 平均字数 | Hit@1 | Hit@2 | Hit@4 | MRR@10 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['config']} | {r['chunks']} | {r['avg_chars']} | {r['hit@1']:.2f} | {r['hit@2']:.2f} | "
                     f"{r['hit@4']:.2f} | {r['mrr@10']:.3f} |")
    lines.append(f"\n共 {len(questions)} 题。")
    for r in rows:
        if r["unreachable"]:
            lines.append(f"- {r['config']}：{r['unreachable']} 的标准片段被切断，任何检索都无法命中")
    table = "\n".join(lines)
    args.out.with_suffix(".md").write_text(table + "\n", encoding="utf-8")
    print(table)
    # 逐题名次，便于定位失败
    print("\n逐题名次（None = top10 未命中）：")
    for q in questions:
        print(q["id"], q["type"], [details[name][q["id"]]["rank"] for name, _, _ in CONFIGS], q["question"])


if __name__ == "__main__":
    main()
