"""汇总 results/e2e/<模型>/summary.json，输出 results/e2e/summary.md。"""
import json
from pathlib import Path

E2E = Path(__file__).resolve().parent.parent / "results" / "e2e"
NAMES = {"ref": "参考实现（原版 agent_v1.py）", "mine-base": "我的基础版（第一轮）",
         "mine-nocheck": "+原问题兜底/软 scope/open 限制", "mine": "+回答校验（完整版）"}


def main():
    lines = ["| 模型 | 配置 | status=ok | 要点全部命中 | 要点覆盖率 | 检索到标准片段 | 含有效引用 | 含无效引用 | 编造网址 | 平均工具调用 | 平均耗时 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    per_q = {}
    for model_dir in sorted(p for p in E2E.iterdir() if p.is_dir()):
        rows = json.loads((model_dir / "summary.json").read_text(encoding="utf-8"))
        for system in NAMES:
            rs = [r for r in rows if r["system"] == system]
            if not rs:
                continue
            n = len(rs)
            got = sum(int(r["points"].split("/")[0]) for r in rs)
            total = sum(int(r["points"].split("/")[1]) for r in rs)
            lines.append(
                f"| {model_dir.name} | {NAMES[system]} | {sum(r['status'] == 'ok' for r in rs)}/{n} | "
                f"{sum(r['all_points'] for r in rs)}/{n} | {got / total:.0%} | {sum(r['retrieved_gold'] for r in rs)}/{n} | "
                f"{sum(r['has_valid_cite'] for r in rs)}/{n} | {sum(bool(r['invalid_cites']) for r in rs)}/{n} | "
                f"{sum(bool(r['urls']) for r in rs)}/{n} | {sum(r['tool_calls'] for r in rs) / n:.1f} | "
                f"{sum(r['total_s'] for r in rs) / n:.1f}s |")
            for r in rs:
                per_q.setdefault(r["qid"], {})[f"{model_dir.name}/{system}"] = (
                    f"{r['points']}{'' if r['status'] == 'ok' else ' ' + r['status']}"
                    f"{' 引✓' if r['has_valid_cite'] else ''}{' 引✗' if r['invalid_cites'] else ''}")
    cols = sorted({k for v in per_q.values() for k in v})
    lines += ["", "逐题（要点命中数；引✓=含有效引用，引✗=含无效引用）：", "",
              "| 题号 | " + " | ".join(cols) + " |", "| --- |" + " --- |" * len(cols)]
    for qid in sorted(per_q):
        lines.append(f"| {qid} | " + " | ".join(per_q[qid].get(c, "") for c in cols) + " |")
    text = "\n".join(lines) + "\n"
    (E2E / "summary.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
