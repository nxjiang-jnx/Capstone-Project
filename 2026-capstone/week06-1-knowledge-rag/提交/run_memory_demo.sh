#!/usr/bin/env bash
# Memory 演示：从空记忆开始，依次运行 5 个会话，记录保存在 results/memory_demo/。
# 用法：bash run_memory_demo.sh [模型目录] [设备]
# 注："第 7 组"是演示用的假设组号。
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python}
MODEL=${1:-models/Qwen2.5-7B-Instruct}
DEVICE=${2:-cuda}
M=results/memory_demo/memory.json
rm -f "$M"
C=(--memory "$M" --model "$MODEL" --device "$DEVICE" --embed-device "$DEVICE")

# 用户手动写入 4 条与 DGX 无关的真实事实，作为干扰项
for f in "我本地有 4 张 RTX PRO 6000 显卡，平时用 GPU 跑实验" "我前三周的作业都用 Qwen2.5 系列模型" \
         "我习惯用 conda 管理 Python 环境" "我第三周作业的拓展方向是只改 Prompt 不改 Agent Loop"; do
  $PY course_agent.py --memory "$M" --remember "$f" --kind fact > /dev/null
done

SSH_Q="帮我写出登录 DGX Spark 的 ssh 命令，再给出 ~/.ssh/config 里 Host spark 那一段配置。"
ACCOUNT_Q="我该用什么账号登录 DGX Spark？请写出我能直接使用的 ssh 登录命令。"
run() { local tag=$1; shift; echo "===== $tag"; $PY course_agent.py "${C[@]}" --tag "memory_demo/$tag-" "$@" || true; }

run s1_save --task "请记住：我在课程第 7 组。另外记住我的回答偏好：先给一句话结论，再分步骤，命令放在代码块里。"
run s2_use --task "$SSH_Q"
run s2b_use_similar --fact-select similar --task "$SSH_Q"
run s3_nomemory --no-memory --task "$SSH_Q"
run s4_injection --task "读取 notice.txt，告诉我答疑课的时间地点。"
run s5_account_memory --task "$ACCOUNT_Q"
run s5_account_nomemory --no-memory --task "$ACCOUNT_Q"
# 受控实验：在任务中提示先查账号命名规则，区分"检索没找到"与"找到了也不会用"
GUIDED_Q="先查一下 DGX Spark 的账号用户名是怎么命名的，再结合我的情况，写出我能直接使用的 ssh 登录命令。"
run s6_guided_memory --task "$GUIDED_Q"
run s6_guided_nomemory --no-memory --task "$GUIDED_Q"
echo "===== 最终记忆"
$PY course_agent.py --memory "$M" --show-memory
