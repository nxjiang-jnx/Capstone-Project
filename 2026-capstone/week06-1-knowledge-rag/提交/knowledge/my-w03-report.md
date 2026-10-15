# 我的第三周作业提交说明（实验记录）

原始文件：`2026-capstone/week03-agent-tool-calling/提交/提交说明.md`


- 姓名：姜楠翔
- 学号：23230610

## 运行环境

- 模型：Qwen2.5-1.5B-Instruct（第一周下载）、Qwen2.5-3B-Instruct、Qwen2.5-7B-Instruct（ModelScope 下载）
- 设备与精度：NVIDIA RTX PRO 6000 Blackwell Max-Q，`--device cuda`，bfloat16（脚本在支持 bf16 的 GPU 上自动选择）
- 依赖版本：Python 3.12.13，torch 2.7.1+cu128，transformers 4.51.3，pydantic 2.11.7，openai 1.109.1
- 自测：`python agent_v0.py --selftest` → T1–T8、3 项非法表达式拒绝、word_count 冒烟共 14 项全部 PASS，输出"全部通过"。

固定任务（5 次运行完全相同）：`读取 test_report.txt，计算测试通过率`
工作目录 `workspace/test_report.txt` 内容为 `passed=47\nfailed=3\n`，正确答案是 **94%**。

## 5 次运行对照

命令公共部分：`python agent_v0.py --backend hf --device cuda --task "读取 test_report.txt，计算测试通过率"`，下表只列出每次变动的部分。5 次都用**原版未修改的 `agent_v0.py`**。

| 序号 | 调整的参数 | 变动部分 | status | answer | 答案是否正确 | 结果文件 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 默认（1.5B，贪心） | `--model .../Qwen2.5-1.5B-Instruct` | `ok` | 计算测试通过率需要更多的信息…… | ✗ | `results/run1_1.5B_greedy.json` |
| 2 | 只加 `--sample`（T=0.7 默认） | `+ --sample` | `ok` | 请检查您的路径是否正确…… | ✗ | `results/run2_1.5B_sample_t0.7.json` |
| 3 | 只把 temperature 提到 1.2 | `+ --sample --temperature 1.2` | `too_many_failures` | 无 | ✗ | `results/run3_1.5B_sample_t1.2.json` |
| 4 | 只换模型规模 3B（贪心） | `--model .../Qwen2.5-3B-Instruct` | `max_steps` | 无 | ✗ | `results/run4_3B_greedy.json` |
| 5 | 只换模型规模 7B（贪心） | `--model .../Qwen2.5-7B-Instruct` | `too_many_failures` | 无 | ✗ | `results/run5_7B_greedy.json` |

5 次没有一次给出正确答案，但失败的原因各不相同，见下面的调用链分析。

## 调用链分析

### 第 1 次（1.5B 贪心，status=`ok`，但答案是错的）

- **step 1**：`raw` 是"需要先读取文件并计数……"加一个 JSON。`parse_decision` 截取 `{...}` 后解析成功，decision 是 `read_file(path="/content/test_report.txt")`。模型凭空编了一个 Colab 风格的绝对路径。`observation` 是 `execution_error`，`PermissionError`，提示里已经明确写了"请使用工作目录内的相对路径，例如 test_report.txt"。
- **step 2**：`raw` 全是自然语言（"请确保你的工作目录中有一个名为 test_report.txt 的文件……"），没有 JSON，记为 `format_error`。注意它复述了正确的文件名，却没有照着改调用。失败计数到 2，Loop 追加"输出格式错误"的提示后继续。
- **step 3**：模型输出 `{"action":"final","answer":"计算测试通过率需要更多的信息，如测试通过的数量和总数量。"}`。Loop 判定为 `final`，返回 **status=`ok`**。

这条链最值得注意的是：**`status=ok` 只表示模型主动收尾了，不代表任务完成。** 文件明明就在工作目录里、Observation 也给了正确提示，模型却放弃并宣称信息不足。这属于"假成功"，只看 status 会误判，必须结合 answer 和 trace 一起看。

### 第 4 次（3B 贪心，status=`max_steps`）

- **step 1**：`read_file(path="test_report.txt")` → `ok`，拿到 `passed=47\nfailed=3`。换成 3B 后路径直接就对了。
- **step 2**：`calculator(expression="47/(47+3)*100")` → `ok`，**结果 94.0，正确答案此时已经拿到**。
- **step 3**：`calculator(expression="100-94.0")` → `6.0`，开始算失败率，任务其实已经不需要这一步。
- **step 4**：`raw` 是"答案：测试通过率为 94.0%，失败率为 6.0%。"——**内容完全正确，但没有包成 JSON**，于是被判 `format_error`。协议要求 `{"action":"final",...}`，模型用了自然语言。
- **step 5**：又调了一次 `calculator(expression="(47+3)/50*100")` → `100.0`，算式列错了（分子应该是 47）。
- **step 6**：`raw` 是"答案：测试通过率为 100.0%。"，仍然不是 JSON，再次 `format_error`。步数用尽，返回 `max_steps`，answer 为空。

3B 的瓶颈不在工具使用，而在**协议遵守**：它两次都算对/算错在自然语言里，就是不肯输出 final 的 JSON。另外 step 2 之后已经有正确答案，Loop 却无法提取——因为 Agent 只认结构化的 final，这正是"协议靠 Prompt 口头约定、没有约束解码"的代价。

### 第 5 次（7B 贪心，status=`too_many_failures`）

- **step 1**：`read_file(path="test_report.txt")` → `ok`，路径正确。
- **step 2–4**：连续三轮 `format_error`。看 `raw` 就明白了：模型在写 LaTeX 公式，`根据提供的信息，可以通过率可以通过以下公式计算得出：\[ \text{通过率}`。`parse_decision` 用"第一个 `{` 到最后一个 `}`"的启发式截取，结果截到的是 LaTeX 的 `{通过率}`，报错 `Invalid JSON: key must be a string`。失败预算耗尽，返回 `too_many_failures`。

这条链说明：**失败不一定是模型不会做，也可能是解析层和模型的输出风格不匹配。** 7B 更倾向于写数学公式排版，恰好触发了 `{}` 截取启发式的盲区。同时也注意到 7B 每步只用 0.4–1 秒，整条链 3.5 秒，比 1.5B 的 10.6 秒还快——因为它输出简短，而小模型会长篇大论直到触发停止条件。

### 横向观察

1. **模型规模改变的是失败的位置，不是成功率。** 1.5B 卡在"编造绝对路径"（第 1、2、3 次都是 `/content/...` 或 `/Users/...`）；3B 路径和算式都对了，卡在"不输出 final JSON"；7B 路径也对，卡在"输出 LaTeX 撞坏 JSON 截取"。规模越大，失败点越靠后、越接近格式层面。
2. **解码策略的影响小于模型规模。** 第 1 次（贪心）和第 2 次（采样 T=0.7）的失败方式几乎一样，都是绝对路径 + 放弃。把 temperature 提到 1.2（第 3 次）后，模型连续两轮重复同一个非法路径，语言也更啰嗦，最终因失败预算耗尽而终止——高温只是让输出更发散，并没有换一种解法。
3. **`status` 不等于任务成功。** 5 次里 2 次是 `ok`（第 1、2 次），但答案都是错的；反而 `max_steps` 的第 4 次在 trace 中间就已经算出了正确的 94.0。评估 Agent 必须看 trace，不能只看终态。
4. **Observation 里的纠错提示，小模型基本用不上。** `PermissionError` 的消息里直接给出了正确写法 `test_report.txt`，1.5B 在下一轮把这句话复述了一遍，却仍然不改调用。这也是我下面做拓展的出发点。

## 可选拓展：只改 Prompt，不动 Agent Loop

- **拓展内容**：基线里两个最常见的失败是"编造路径"和"拿到答案却不收尾"。我想验证一个问题：**这些失败有多少是模型能力不足，有多少只是 Prompt 没把信息给够？** 所以只改系统提示词，Agent Loop、工具层、解析层一行不动。

- **主要改动**（在 `agent_v0.py` 中，原有行为默认不变）：
  - `--prompt-v2`：系统提示词追加三部分——(a) 运行时读取工作目录、把真实存在的文件名列给模型，并写明必须用相对路径；(b) 补充规则"Observation 里信息够了就必须立即 final""final 要写出具体数值"；(c) 一个 `read_file → Observation → final` 的两轮示例。
  - `--prompt-v3`：在 v2 基础上只改一点——要求算术必须调用 calculator，示例里补上计算那一轮（`read_file → Observation → calculator → Observation → final`）。
  - `--seed`：固定采样随机数，让采样实验可复现（已验证：同一 seed 重跑，answer 逐字一致）。
  - 输出 JSON 增加 `config` 字段，记录本次运行的全部参数。
  - `--selftest` 在改动后仍然 14 项全部 PASS。

- **运行结果**：1.5B 用采样（T=0.7）跑 5 个固定 seed，三种 Prompt 各一组；3B/7B 贪心各跑一次。

  | 配置 | status | 答案正确数 | 典型表现 | 结果文件 |
  | --- | --- | --- | --- | --- |
  | 1.5B 采样 × 5，原版 Prompt | 3 次 `ok` + 2 次 `too_many_failures` | 0/5 | 5/5 都编造绝对路径，读不到文件；seed3 更是自己伪造了一条 `Observation: {"result": [{"path": "/Users/your_username/..."}]}` | `results/ext_1.5B_sample_base_seed{1..5}.json` |
  | 1.5B 采样 × 5，v2 | 5 次 `ok` | 0/5 | **路径 5/5 全对**，但跳过 calculator 心算，答案 86.96%/89.52%/86.67%/89.52%/98.63% 全错 | `results/ext_1.5B_sample_v2_seed{1..5}.json` |
  | 1.5B 采样 × 5，v3 | 5 次 `ok` | 0/5 | **5/5 都调用了 calculator**，但表达式写错，答案仍全错 | `results/ext_1.5B_sample_v3_seed{1..5}.json` |
  | 3B 贪心，v2 / v3 | `ok` / `ok` | 2/2 | 从基线的 `max_steps` 变为正确收尾，94% | `results/ext_3B_greedy_v2.json`、`ext_3B_greedy_v3.json` |
  | 7B 贪心，v2 / v3 | `ok` / `ok` | 2/2 | 从基线的 `too_many_failures` 变为正确收尾，94% | `results/ext_7B_greedy_v2.json`、`ext_7B_greedy_v3.json` |

  **效果与是否达到预期：**
  1. **路径幻觉是 Prompt 问题，不是能力问题。** 把文件清单直接写进 Prompt 后，1.5B 的路径错误从 5/5 降到 0/5，这一点完全达到预期。
  2. **3B 和 7B 从"失败"变成"答对"。** 3B 原本算出 94.0 却不收尾，7B 原本被 LaTeX 卡住；加了收尾规则和 JSON 示例后，两者都在 2–3 步内给出 94%。说明基线里这两次失败主要是协议表达不清，而不是模型不会做。
  3. **v2 有一个我自己引入的副作用。** v2 的示例只演示了 `read_file → final`，1.5B 就照着这个形状把算术心算了，5 次全算错。**示例的形状会被模型直接模仿**，这是本次最意外的一条观察。
  4. **v3 修正了形状，但没能修正结果。** 加上"算术必须调 calculator"和含计算轮的示例后，1.5B 5/5 都调了 calculator，但传进去的表达式要么是变量名 `(passed + failed) / total * 100`（工具报"表达式含有不支持的语法"），要么算式本身错了 `(47+3)/50*100 = 100`。也就是说，**瓶颈从"调用形状"转移到了"把 Observation 里的数值正确代入算式"**，后者靠 Prompt 解决不了，是 1.5B 的能力边界。这一条没有达到预期，但定位比原来清楚了。

- **局限**：每种配置只有 5 次采样（3B/7B 各 1 次贪心），样本量小，只能看趋势不能算成功率。正确性判定用的是答案里是否出现 94%，属于人工规则而非严格校验。另外 `parse_decision` 的 `{}` 截取启发式被 LaTeX 撞坏这个问题我没有动手修（那要改解析层，超出"只改 Prompt"的范围），只在分析里记录了。

## 提交文件

- `agent_v0.py`：**有改动**，新增 `--prompt-v2`、`--prompt-v3`、`--seed` 三个开关和输出里的 `config` 字段；不加这些参数时行为与原版一致（`--selftest` 14 项全 PASS）。5 次对照实验用的是原版脚本。
- `workspace/test_report.txt`：运行用的数据文件，便于复现。
- 运行结果（共 24 个 JSON，均保留完整 trace，未手工修改）：
  - 5 次对照：`results/run1_1.5B_greedy.json`、`run2_1.5B_sample_t0.7.json`、`run3_1.5B_sample_t1.2.json`、`run4_3B_greedy.json`、`run5_7B_greedy.json`
  - 拓展基线：`results/ext_1.5B_sample_base_seed{1..5}.json`
  - 拓展 v2：`results/ext_1.5B_sample_v2_seed{1..5}.json`、`ext_3B_greedy_v2.json`、`ext_7B_greedy_v2.json`
  - 拓展 v3：`results/ext_1.5B_sample_v3_seed{1..5}.json`、`ext_3B_greedy_v3.json`、`ext_7B_greedy_v3.json`
