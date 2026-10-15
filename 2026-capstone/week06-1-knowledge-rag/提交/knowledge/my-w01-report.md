# 我的第一周作业提交说明（实验记录）

原始文件：`2026-capstone/week01-llm-inference/提交/提交说明.md`


- 姓名：姜楠翔
- 学号：23230610

## 运行环境

- 模型：Qwen2.5-1.5B-Instruct（ModelScope 下载，本地加载）
- 设备：GPU，NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition（CUDA 12.8）
- 精度：bfloat16
- Python / PyTorch / Transformers 版本：Python 3.12.13 / PyTorch 2.7.1+cu128 / Transformers 4.51.3

## 运行命令

```bash
CUDA_VISIBLE_DEVICES=1 python qwen_inference.py --model ./models/Qwen2.5-1.5B-Instruct --device cuda --prompt "请用两句话解释什么是 KV cache，以及它为什么能加速大语言模型推理。" --max-new-tokens 128 --debug --output results/run.json > results/run.log 2>&1
```

## 推理结果

- 输入：请用两句话解释什么是 KV cache，以及它为什么能加速大语言模型推理。
- 输出：KV cache，即键值缓存，是一种存储和快速访问数据的方法。它通过将频繁访问的数据存储在内存中，从而减少对数据库的访问次数，提高数据处理的效率。在大语言模型的推理过程中，KV cache可以加速推理过程，因为它能快速访问和处理模型的参数，减少计算时间和资源消耗。
- 单次推理时间：3.622 秒（generation_seconds，完整预热一次后单次 `generate()`，含 Prefill 和 Decode）
- 实际生成 token 数：74（max_new_tokens=128，含 EOS；输入 token 数 48，约 20.4 tokens/s）
- Hidden states（Prefill 共 29 个状态 = 28 个 block + 1，数值为 `[0,-1,:8]`）：
  - `hidden_states[0]`（embedding）：shape `[1, 48, 1536]`，`[-0.03589, -0.04810, 0.01660, 0.00836, 0.00873, 0.03198, 0.01086, -0.01178]`
  - `hidden_states[1]`（第 1 个 block 后）：shape `[1, 48, 1536]`，`[0.24512, -0.17969, -0.09326, -0.03040, 0.24414, 0.08838, -0.10791, -0.07813]`
  - `hidden_states[28]`（最后一层，已过 final RMSNorm）：shape `[1, 48, 1536]`，`[0.31055, 2.0, 0.0, 1.58594, 2.3125, -0.39844, 0.0, -3.76563]`
  - Decode 一步后最后一层 hidden state：shape `[1, 1, 1536]`，`[0.63281, -1.92969, 3.75, 1.32031, -1.95313, 0.98828, 1.77344, -3.625]`
  - logits：shape `[1, 48, 151936]`；首层 K cache：`[1, 2, 48, 128]` → Decode 一步后 `[1, 2, 49, 128]`

## 提交文件

- 推理脚本：qwen_inference.py
- 运行结果：run.json（完整 JSON 结果）、run.log（完整终端日志）
