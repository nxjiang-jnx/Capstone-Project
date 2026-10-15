"""端到端对比：同一模型、同一组问题，比较三种 Agent 配置。

- ref：课程原版 code/agent_v1.py（未修改，直接 import），只把 --knowledge 换成本作业的课程知识库；
- mine-base：course_agent.py 的基础版：结构化切分 + 混合检索 top4 + 5 个工具，但检索不附加原问题、
  scope 严格过滤、open_source 不设限制、不做引用校验（相当于第一轮实现）；
- mine-nocheck：在 mine-base 上加入原问题兜底、软 scope、open_source 限制，仍不做引用校验；
- mine：course_agent.py 默认配置，再加上回答校验（引用 + 行动声明），不通过时最多重答 2 次。
为排除 Memory 的影响，三者都不注入记忆。模型只加载一次，三种配置共用，贪心解码。

打分（自动，人工复核见 README）：
- 要点：回答是否包含 questions.json 中每一条 must 正则；
- 引用：回答里出现的片段 id 是否都在本次工具返回中（有效），以及是否至少有一个有效引用。
用法：python eval/run_e2e.py --model models/Qwen2.5-7B-Instruct --device cuda:0
"""
import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUBMIT = HERE.parent
sys.path.insert(0, str(SUBMIT))
import course_agent as mine  # noqa: E402

REF_PATH = SUBMIT.parent / "code" / "agent_v1.py"


def load_ref():
    spec = importlib.util.spec_from_file_location("ref_agent_v1", REF_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_llm(tokenizer, model, device, schemas, max_tokens=768):
    import torch

    def llm(messages):
        prompt = tokenizer.apply_chat_template(messages, tools=schemas, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(device)
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False,
                                 temperature=None, top_p=None, top_k=None)
        return tokenizer.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return llm


def returned_chunks(result):
    """本次运行中检索/阅读工具实际返回过的片段（两种实现的返回格式都含 id 和 text）。"""
    for record in result["trace"]:
        for obs in record.get("observations", []):
            res = obs["result"]
            for hit in res if isinstance(res, list) else [res]:
                if isinstance(hit, dict) and "id" in hit and "text" in hit:
                    yield hit


def score(result, question):
    answer = result.get("answer") or ""
    chunks = list(returned_chunks(result))
    seen = {c["id"] for c in chunks}
    cited = list(dict.fromkeys(mine.CITE_RE.findall(answer)))
    valid = [c for c in cited if c in seen]
    gold_hit = any(c["id"].split("#")[0].removesuffix(".md") == src and re.search(pattern, c["text"])
                   for c in chunks for src, pattern in question["gold"])
    must = [bool(re.search(p, answer)) for p in question["must"]]
    return {"status": result["status"], "points": f"{sum(must)}/{len(must)}", "all_points": all(must),
            "cited": cited, "invalid_cites": [c for c in cited if c not in seen],
            "has_valid_cite": bool(valid), "urls": re.findall(r"https?://\S+", answer),
            "retrieved_gold": gold_hit,
            "tool_calls": sum(len(r.get("tool_calls") or []) for r in result["trace"]),
            "steps": len(result["trace"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--systems", default="ref,mine-base,mine-nocheck,mine")
    parser.add_argument("--only", default="", help="逗号分隔的题号，默认全部 e2e 题")
    args = parser.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    questions = [q for q in json.loads((HERE / "questions.json").read_text(encoding="utf-8")) if q.get("e2e")]
    if args.only:
        questions = [q for q in questions if q["id"] in args.only.split(",")]
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True,
                                                 torch_dtype=torch.bfloat16).to(args.device).eval()
    ref = load_ref()
    bge = str(SUBMIT / "models/bge-small-zh-v1.5")
    ref_kb = ref.KnowledgeBase(SUBMIT / "knowledge", bge)
    encoder = mine.Encoder(bge, args.device)
    my_kb = mine.KnowledgeBase(SUBMIT / "knowledge", lambda: encoder)
    llms = {"ref": make_llm(tokenizer, model, args.device, ref.TOOL_SCHEMAS),
            "mine": make_llm(tokenizer, model, args.device, mine.TOOL_SCHEMAS)}
    tag = Path(args.model).name.replace("Qwen2.5-", "").replace("-Instruct", "")
    out_dir = SUBMIT / "results" / "e2e" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for q in questions:
        for system in args.systems.split(","):
            started = time.perf_counter()
            if system == "ref":
                result = ref.run_agent(q["question"], llms["ref"], ref.make_tools(ref_kb, ref.ROOT / "workspace"), [])
            else:
                base = system == "mine-base"
                tools = mine.make_tools(my_kb, SUBMIT / "workspace", mine.Memory(out_dir / "unused_memory.json"),
                                        q["question"], task_query=not base, soft_scope=not base)
                result = mine.run_agent(q["question"], llms["mine"], tools, [], [], open_guard=not base,
                                        cite_retries=2 if system == "mine" else 0)
            result["total_s"] = round(time.perf_counter() - started, 2)
            result["model"] = args.model
            result["system"] = system
            result.pop("messages", None)
            s = score(result, q)
            result["score"] = s
            (out_dir / f"{q['id']}_{system}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                             encoding="utf-8")
            summary.append({"qid": q["id"], "system": system, **s, "total_s": result["total_s"]})
            print(f"{tag} {q['id']} {system:13s} {s['status']:9s} 要点 {s['points']} 有效引用 {s['has_valid_cite']}"
                  f" 无效 {s['invalid_cites']} {result['total_s']}s", flush=True)
    # 只重跑部分题目时，与已有汇总合并
    old = out_dir / "summary.json"
    if old.exists() and (args.only or args.systems != parser.get_default("systems")):
        done = {(r["qid"], r["system"]) for r in summary}
        summary = [r for r in json.loads(old.read_text(encoding="utf-8"))
                   if (r["qid"], r["system"]) not in done] + summary
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
