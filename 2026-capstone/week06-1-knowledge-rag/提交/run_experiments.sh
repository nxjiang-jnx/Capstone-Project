#!/usr/bin/env bash
# 复现 README 中的全部实验（需要 models/ 下的 Qwen2.5-3B/7B-Instruct 与 bge-small-zh-v1.5）。
# 用法：bash run_experiments.sh [设备]   例如 bash run_experiments.sh cuda
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python}
DEV=${1:-cuda}

echo "### 1. 自检（不加载模型）"
$PY course_agent.py --selftest

echo "### 2. 检索评测（只用 BGE）"
$PY eval/eval_retrieval.py --embed-device "$DEV"

echo "### 3. 端到端对比：参考实现 vs 我的版本（3B、7B）"
$PY eval/run_e2e.py --model models/Qwen2.5-3B-Instruct --device "$DEV"
$PY eval/run_e2e.py --model models/Qwen2.5-7B-Instruct --device "$DEV"
$PY eval/summarize_e2e.py

echo "### 4. Memory 演示（7B）"
PYTHON=$PY bash run_memory_demo.sh models/Qwen2.5-7B-Instruct "$DEV"

echo "### 5. 参考代码的玩具任务，用我的 Agent 运行（3B）"
$PY course_agent.py --memory results/ref_toy/ref_preferences.json --knowledge ../code/knowledge \
  --workdir ../code/workspace --model models/Qwen2.5-3B-Instruct --device "$DEV" --embed-device "$DEV" \
  --tag ref_toy/mine_example_3B- --task "请读取 task.txt 中的启动报错，查询知识库，给出处理步骤、日志位置和资料来源。" || true

echo "### 6. 综合示例任务 workspace/example_task.txt（3B、7B）"
for m in 3B 7B; do
  $PY course_agent.py --memory results/example/memory.json --model models/Qwen2.5-$m-Instruct --device "$DEV" \
    --embed-device "$DEV" --tag example/example_$m- --example || true
done
