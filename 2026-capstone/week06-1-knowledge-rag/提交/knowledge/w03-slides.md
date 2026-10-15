# 第三周课件：Minimal Agent 与 Tool Calling

原始文件：`minimal-agent-and-tool-calling.pptx`

## 第 1 页 Minimal Agent 与 Tool Calling

Agent Loop、Observation、Function Schema 与工具执行 2026 秋季

## 第 2 页 本次课程内容

第1次课 · Minimal Agent
第2次课 · Tool Calling
从 LLM App 到 Agent
为什么需要循环；模型决策、应用执行；ReAct
Agent Loop
状态、Observation、停止条件；最小循环代码
Tool Calling 与 Schema
工具调用的演进与往返；name / description / parameters
校验、执行与结果回传
四道关卡；安全执行；错误反馈与自我修正
Agent v0：集成与任务
四个稳定接口，承接两次课的收尾

## 第 3 页 本周在 16 周项目中的位置

第3周：把“会回答”的 LLM App，推进为“能行动”的 Agent v0
参考：顶点课程 16 周课程安排；2026 秋季顶点课程介绍 2.4
LLM App 第2周 Prompt · API Structured Output
Agent v0 第3周 · 本周 Agent Loop Tool Calling
Agent v1 第5–6周 Memory · Tools 知识库 RAG
Private Agent 第6–8周 DGX Spark · vLLM 中期验收
Agent v2 第10–11周 Planning 评估与 Trace
优化与答辩 第12–16周 系统优化 综合评估
Agent v0 是所有后续能力的挂载点。 本周定下的四个接口——llm(messages)、TOOLS 注册表、messages 状态、trace 记录——之后的 Memory、RAG、Planning、vLLM 与评估都只是往里“挂”，基本不再推翻。

## 第 4 页 本周目标：Agent v0

理解机制，掌握做法，交付一个跑通闭环的最小 Agent
参考：顶点课程 16 周课程安排：第3周课后作业/项目推进
理解
Agent 与一次性 LLM App 的区别 循环、状态、Observation、停止条件为什么这样设计 决策在模型、执行在应用的责任边界
掌握
Function Schema 三要素与参数校验 工具执行的安全边界与异常隔离 结果回传：让模型看见工具结果
完成
agent_v0.py：可运行、自测全部通过 ≥2 个工具，含 1 个贴近你们项目场景的工具 带调用链的运行记录，能定位失败原因
本周的主线：Agent的一次完整执行
模型 决定下一步
工具 被应用执行
Observation 结果回到模型
最终回答 满足停止条件

## 第 5 页 1 从 LLM App 到 Agent：本节导读

先回答五个问题：学什么、怎么学、抓什么、难在哪、怎么解
目标
说清 Agent 与一次性 LLM App 的区别，知道什么样的任务需要 Agent。
方法
对比“单次调用”与“循环调用”；用 ReAct 轨迹观察模型、工具、环境如何交替。
重点
Agent = 模型 + 循环 + 工具 + 状态；决策在模型，执行在应用。
难点
“模型调用了工具”是错觉：模型只产出文本，动作由应用解析、校验并执行。
思路
从一个 LLM App 做不到的任务出发，逐步补上循环、工具与状态。

## 第 6 页 1.1 LLM 与 Agent：同一个问题，两种工作方式

LLM 答一次就结束；Agent 边做边看，直到完成
参考：Anthropic: Building effective agents；Minimum Agent Lab 的对比方式
普通 LLM · 生成一个答案
用户问题
Prompt
LLM
回答
结束
问题：“agent.py 实现了什么功能？”　典型表现（示意）：说“我看不到这个文件”，或只凭文件名瞎猜
LLM 负责生成 回答结束，任务通常也就停止了
Agent · 持续推进目标
目标
决策
行动
观察
未完成：带着观察回到决策
第 1 轮：read_file(agent.py) → 读到 run_agent()、execute() 等约 40 行代码 第 2 轮：据代码回答：“实现了最小 Agent 循环：调模型、执行工具、回传结果”
Agent 负责让任务向前推进 读取反馈，决定下一步，必要时重复

## 第 7 页 1.2 单次调用的边界

一次 LLM 调用只能“说”，不能“查”，也不能“算”
参考：第2周 LLM Application；Lilian Weng: LLM Powered Autonomous Agents
任务
读取 test_report.txt，计算测试通过率
模型（单次调用）
典型表现（示意） “我无法访问文件”  或  编造一个数字
单次调用做不到的三类事
获取外部信息
文件、网页、数据库不在模型的输入里；知识也有截止时间。
精确计算与执行
模型按概率生成文字，大数乘法、运行代码都不可靠。
多步依赖
下一步做什么，取决于上一步查到了什么，无法提前写死。
共同点：需要行动，并把行动的结果再交给模型。

## 第 8 页 1.3 来龙去脉：从“会说”到“会做”

每一步，都在回答上一步留下的问题
参考：Yao et al. ReAct 2022；OpenAI、Anthropic 官方发布（见备注）
2022-10
ReAct
解决了什么
让模型“想一步、做一步、看一步”，推理与行动交替
留下的问题
动作靠在文本里找，格式脆弱
2023-06
函数调用
模型按声明输出结构化调用：工具名 + 参数
每个工具都要各自适配
2024-11
MCP
用统一协议发现并调用外部工具与数据
什么时候真的需要 Agent？
2024-12
Building effective agents
区分 Workflow 与 Agent，从简单、可组合的做起
循环与校验仍要自己写好
2025-03
Responses API 与 Agents SDK
官方封装循环、内置工具与多 Agent 编排
出问题时仍要看懂循环内部
本课把这条脉络里最核心的部分——循环 + 工具调用——自己写一遍：先懂原理，再用框架，出问题时才看得懂。

## 第 9 页 1.4 Agent = 模型 + 循环 + 工具 + 状态

把一次调用改成“决策—执行—观察”的循环
参考：Anthropic: Building effective agents；ReAct
LLM App（第2周）
用户
模型
回答
Agent
用户任务
最终回答
工具
Action 工具调用请求
Observation 执行结果
状态：messages（任务、决策、Observation 逐轮追加）
读入当前状态，决定“下一步”：调用工具，或给出最终回答
循环
反复推进，直到满足停止条件；没有循环就退化为单次问答
模型可以请求的外部能力；没有工具，模型只能想、不能做
状态
跨轮次保留的信息；没有状态，模型记不住上一轮
差别不在模型本身，而在模型外面的这一圈。

## 第 10 页 1.5 决策权与执行权

模型只“提出”动作，应用负责“执行”动作
参考：OpenAI: Function calling；Anthropic: Building effective agents
模型侧：只产出文本
读取 messages 中的全部状态 输出一个决策：工具名 + 参数，或最终回答 不能访问文件、网络和系统
应用侧：Agent 代码
解析决策、校验参数、检查权限 真正执行工具，隔离异常 把 Observation 写回状态；决定何时停止
决策
Observation
模型的输出（此刻文件还没有被读取）：
{"action": "tool", "name": "read_file", "arguments": {"path": "test_report.txt"}}
责任落在应用：安全（权限、沙箱）、可靠（校验、异常）、可控（步数、预算）——正是后面几节的内容。

## 第 11 页 1.6 流程演示：一个任务，从输入到完成

跟着一个任务走完整个闭环，看清谁在做什么
参考：配套 agent_v0.py
01 用户输入
读取 test_report.txt，计算测试通过率
02 模型决策
{"action": "tool", "name": "read_file", "arguments": {"path": "test_report.txt"}}
03 应用执行工具
execute → {"status": "ok", "result": "passed=47\nfailed=3\n"}
04 Observation 回传
Observation: {"status": "ok", "result": "passed=47\nfailed=3\n"}
05 模型决策
{"action": "tool", "name": "calculator", "arguments": {"expression": "47/(47+3)*100"}}
06 执行并回传
Observation: {"status": "ok", "result": 94.0}
07 最终回答
{"action": "final", "answer": "测试通过率为 94%"}
深蓝＝模型　青绿＝应用与工具　琥珀＝写回 messages　灰＝用户。模型只产生文本，动作都由应用执行。

## 第 12 页 1.7 ReAct：推理与行动交替

每次行动的结果，都进入下一步的判断
参考：Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. ICLR 2023, Fig. 1
CoT（只推理）
推理链看似合理，事实可能是编的。
Act-only（只行动）
有行动，但不会据结果调整。
ReAct（交替）
每步 Observation 修正下一步。
图中 Act = 我们的工具调用，Obs = Observation。Agent v0 不要求模型写出内部推理，只记录可观察的决策、参数与结果。

## 第 13 页 1.8 术语对照：论文里的词与代码里的词

同一件事有几套叫法，对上号，查资料才不迷路
参考：ReAct；OpenAI Function calling；Anthropic: Building effective agents
概念 | 论文 / 文档里常叫 | 本课代码里叫 | 在循环的哪一步
推理 | Thought, Reasoning | 不单独记录；只保留可观察的决策 | ② 模型决策
行动 | Action, tool call, function call | 决策 {"action":"tool",…} → ToolCall | ③ 解析 → ④ 执行
观察 | Observation, tool result | Observation: 消息；execute 返回的字典 | ⑤ 写回 messages
运行时 | Runtime, harness, orchestrator | run_agent() | 整个循环
上下文 | Context, conversation, history | messages 列表 | 每轮发给模型
工具声明 | Tool schema, function definition | Tool（函数 + 参数模型 + 描述） | ① 组装
停止条件 | Stop condition, max turns | max_steps、max_failures、no_progress | ⑥ 检查
遇到陌生词，先问两件事：它对应循环的哪一步？由模型还是应用负责？

## 第 14 页 1.9 Workflow 还是 Agent

路径能提前写死时，用 Workflow 更稳；路径未知时才需要 Agent
参考：Anthropic: Building effective agents
维度 | Workflow（预设路径） | Agent（动态决策）
控制流 | 代码写死：A → B → C | 模型逐步决定下一步
适用 | 步骤固定、可枚举 | 步骤事先未知，依赖中间结果
成本与延迟 | 低，可预测 | 多轮调用，随步数增长
可靠性 | 高，行为可穷举测试 | 需要停止条件、校验与评估兜底
例子 | 拉代码 → 跑测试 → 生成报告 | 读报错 → 定位文件 → 改代码 → 再跑测试
顶点场景（资料与数据分析助手）属于右边：所以要用 Agent，同时给它加边界——这就是停止条件与参数校验存在的原因。

## 第 15 页 1.10 小练习：下面哪个是 Agent？

四个系统，哪一个满足“决策 + 行动 + 观察 + 循环”？
参考：参考 Minimum Agent Lab 的“什么是 Agent”小测方式
A
问答机器人
用户问“什么是死锁？”，模型结合系统提示词回答一次，对话结束。
B
CI 流水线
程序按固定顺序：拉取代码 → 运行测试 → 让模型把失败日志总结成一段报告。
C
调试助手
模型先读报错日志，自己决定打开哪个文件、是否运行测试；看到结果后，再决定是否继续排查。
D
代码库问答
每次都固定检索 3 个相关代码片段，拼进 Prompt，模型据此回答一次。
先投票，再说理由：你判断的依据是什么？

## 第 16 页 1.11 用五个问题拆开看任何一个系统

上一页的答案：谁决定路径，是区分的关键
参考：Anthropic: Building effective agents（Workflow 与 Agent）
五个问题 | A 问答机器人 | B CI 流水线 | C 调试助手 | D 代码库问答
1 能调用工具吗？ | 否 | 是（固定命令） | 是（自选） | 是（检索）
2 谁决定用哪个工具？ | — | 程序员写死 | 模型 | 程序员写死
3 结果影响下一步吗？ | 否 | 否 | 是 | 否
4 会循环吗？ | 否 | 否，顺序执行 | 是 | 否
5 怎么结束？ | 答完即止 | 最后一步跑完 | 目标达成或触发停止条件 | 答完即止
结论 | 单次调用 | Workflow | Agent | Workflow（管道）
程序员写死路径 → Workflow；模型根据 Observation 选择路径 → Agent。决策权交给模型，就必须有停止条件、校验与权限兜底。

## 第 17 页 2 Agent Loop：本节导读

先用脚本化模型把循环逻辑测对，再换真实模型看行为
目标
写出一个能跑通、能停止的最小 Agent Loop，并能说出每一行对应哪个要素。
方法
拆成四个部件——决策表示、状态、Observation、停止条件。
重点
messages 如何逐轮增长；Observation 必须回传；循环必须有出口。
难点
模型行为不可控：格式错、不收敛、重复调用。循环要把这些“意外”变成可处理的分支。
思路
先用脚本化模型确定地测试循环逻辑，再换真实模型观察差异。

## 第 18 页 2.1 一轮循环做什么

一轮 = 一次模型调用 + 至多一次工具执行
参考：ReAct；Anthropic: Building effective agents
① 组装 messages
② 调用模型 llm(messages)
③ 解析决策 parse_decision
action?
返回 最终回答
final
tool
④ 校验并执行工具 execute(...)
⑤ Observation 写回 messages
⑥ 停止条件检查
未触发 下一轮
返回“未完成”+ 原因
触发
messages 是各步骤之间传递的唯一载体；步数、失败次数等运行元数据留在应用里，不发给模型。

## 第 19 页 2.2 决策的表示：只允许两种

让循环“读得懂”模型：一个 action 字段区分两类决策
参考：第2周 Structured Output；Pydantic: Models
class ToolCall(BaseModel): action: Literal["tool"] name: str arguments: dict[str, Any] = {}  class Final(BaseModel): action: Literal["final"] answer: str  Decision = Annotated[Union[ToolCall, Final], Field(discriminator="action")] d = TypeAdapter(Decision).validate_json(text)
模型每一轮的输出（二选一）
{"action": "tool", "name": "calculator", "arguments": {"expression": "47/(47+3)*100"}}
{"action": "final", "answer": "94%"}
一次校验：既判定类型，又检查字段 解析容错：截取第一个 { 到最后一个 } 格式非法 → 计入失败预算，不崩溃
第2周“Prompt 约定 + 客户端校验”的直接应用；与原生 tool_calls 的对应关系见第 37 页。

## 第 20 页 2.3 状态：下一轮模型能看到什么

状态 = 下一轮模型能看到的全部信息，加上应用自己的运行元数据
参考：第2周 3.5 无状态请求与有状态应用；OpenAI: Conversation state
内容 | 作用 | 谁写入 | 示例
system 消息 | 角色、工具说明、输出格式 | 应用（一次） | build_system_prompt()
user 任务 | 要完成的任务 | 用户 | 读取 test_report.txt，计算测试通过率
assistant 决策 | 模型上一轮说了什么 | 模型（原样保存） | {"action":"tool",…}
Observation | 工具的结果或错误 | 应用 | Observation: {"status":"ok",…}
运行元数据 | 步数、失败次数、trace | 应用（不发给模型） | step=2, failures=0
模型没有记忆（请求无状态）：状态在应用里，每一轮把 messages 全量重发。前四行模型可见，最后一行只留在应用里。

## 第 21 页 2.4 messages 在循环中如何增长

每轮都把完整 messages 重新发给模型，历史随步数线性增长
参考：第1周 Prefill / Decode；第2周 无状态请求
第 1 次调用模型
system：角色 + 工具说明 + 格式
user：读取 test_report.txt，计算测试通过率
第 2 次调用模型
system
user：读取 test_report.txt，计算…
assistant：read_file(test_report.txt)
Observation：passed=47, failed=3
第 3 次调用模型
assistant：calculator(47/(47+3)*100)
Observation：94.0
每轮输入更长 →  延迟与成本随步数增长；Observation 要控制长度；步数必须有上限
后续如何处理增长：会在后续课程上下文压缩与缓存复用中提到。

## 第 22 页 2.5 Observation：把结果交回模型

闭环里最容易被漏掉的一环：成功与失败都要回传
参考：OpenAI: Function calling；Anthropic: Building effective agents
obs = execute(decision.name, decision.arguments) messages.append({ "role": "user", "content": "Observation: " + json.dumps(obs, ensure_ascii=False)})
Observation 的两种形态
Observation: {"status": "ok", "result": 94.0}
Observation: {"status": "error", "type": "invalid_arguments", "message": "expression: Field required; expr: Extra inputs are not permitted"}
没有回传 →
模型下一轮看不到结果 → 重复同一个调用，或凭空猜一个答案
回传 →
下一轮基于事实继续 错误也回传：模型才有机会自己修正 结构固定：status + result / type + message
选做：删掉回传这一行，用真实模型观察行为变化。

## 第 23 页 2.6 Observation 的设计原则

写给模型看：结构固定、长度受控、错误可纠正
参考：Anthropic: Building effective agents（agent-computer interface）
原则 | 差的写法 | 好的写法
结构固定 | 有时返回数字，有时返回一句话 | 统一为 {status, result} 或 {status, type, message}
长度受控 | 50 KB 文件原样塞回上下文 | 截断到上限，并注明“已截断”
错误可纠正 | 只返回 “Error”，或 500 行堆栈 | 指出哪个字段错；未知工具时列出可用工具
最小披露 | 返回绝对路径、环境变量 | 只返回完成任务所需的字段
Observation 就是模型的“界面”：像设计 UI 一样设计它。observation_text() 里的长度上限（MAX_OBS_CHARS）就是第二条的实现。

## 第 24 页 2.7 停止条件：循环必须有出口

成功出口只有一个，失败出口要有多个，并且都带原因
参考：Anthropic: Building effective agents
出口 | 触发条件 | 返回 | 防止的问题
final（成功） | 模型输出 final | status=ok + 回答 | —
步数上限 | 步数 ≥ max_steps | max_steps + 调用链 | 无限循环、费用失控
失败预算 | 连续错误 > max_failures | too_many_failures + 最后错误 | 模型持续犯同一类错
无进展 | 同一调用重复 ≥ 3 次 | no_progress + 重复的调用 | 卡住反复试
失败不是异常，而是一种带原因的结果：{status, answer, steps, trace}。调用者靠 status 区分成功与受控失败，靠 trace 定位卡在哪一步。

## 第 25 页 2.8 循环里的分支：下一步去哪

每种情形下，状态怎么变、循环往哪走
参考：配套 agent_v0.py
情形 | 触发条件 | 对 messages | failures | 下一步
模型给出 final | 解析成功，action=final | 不追加 | 不变 | 返回 status=ok
工具调用成功 | execute 返回 status=ok | 追加结果 Observation | 清零 | 进入下一轮
工具调用失败 | execute 返回 status=error | 追加错误 Observation | +1 | 未超预算：下一轮
输出格式错误 | parse_decision 抛 ValueError | 追加“格式错误”提示 | +1 | 未超预算：下一轮
失败超预算 | failures > max_failures | 已追加 | 已 +1 | too_many_failures
同一调用重复 3 次 | name 与 arguments 都相同 | 已追加 | 不变 | no_progress
用完步数 | step 超过 max_steps | — | — | max_steps
判断顺序固定：先 final → 再执行 → 再记 failures → 再查预算 → 最后查重复。每个分支都以“返回结果”结束，不靠抛异常跳出循环。

## 第 26 页 2.9 常见失败模式

Agent 的失败大多发生在循环的边缘，而不是某一次生成
参考：Anthropic: Building effective agents；BFCL
现象 | 常见原因 | 循环里的防护
输出不是合法 JSON，或多写解释 | 小模型格式遵循弱；Prompt 不够明确 | 解析容错 + 纠错 Observation + 失败预算
调用不存在的工具 | 幻觉；工具名记错 | unknown_tool 并列出可用工具
参数缺失或类型错 | Schema 描述不清 | 校验并定位到字段，交还模型修正
反复调用同一个工具 | 没看到或没理解 Observation | 无进展检测；确认 Observation 已回传
没查就直接 final | 过度自信；Prompt 未强调先取事实 | Prompt 要求；用固定任务集抽查
上下文越来越长 | Observation 过长；步数多 | 截断、步数上限；后续用 Memory / 压缩
“常见原因”为经验性归纳，请用自己的运行记录验证。

## 第 27 页 2.10 最小 Agent Loop：四个部件合成一段代码

约 40 行完整实现（这里是删去日志与 trace 后的骨架）
参考：本课配套 agent_v0.py
def run_agent(task, llm, max_steps=6, max_failures=2): messages = [system_prompt(), user(task)]        # ① 状态 failures = 0 for step in range(1, max_steps + 1): raw = llm(messages)                         # ② 调用模型 messages.append(assistant(raw)) try: d = parse_decision(raw)                 # ② 解析决策 except ValueError: failures += 1 obs = error_obs('格式错误') else: if d.action == 'final': return done(d.answer)               # ④ 成功停止 obs = execute(d.name, d.arguments)      # ③ 执行 failures = 0 if ok(obs) else failures + 1 messages.append(observation(obs))           # ③ 回传 if failures > max_failures: return stop('too_many_failures')        # ④ 失败预算 return stop('max_steps')                        # ④ 步数上限
状态
messages 初始为 system + user；之后只追加，不改写
调用与解析
模型输出先原样入列，再解析；格式错误走失败预算
执行与 Observation
execute 永远返回 dict；结果一定写回 messages
停止
final 成功返回；失败预算、步数上限受控退出

## 第 28 页 2.11 跟着代码走一遍：变量如何变化

一个例子：错一次、改对、给出回答
参考：配套 agent_v0.py
步 | 调用模型前 messages | 模型输出（决策） | execute 的结果 | failures | 循环动作
1 | 2 条（system + user） | calculator {"expr": "1+1"} | invalid_arguments | 0 → 1 | 追加错误 Observation，继续
2 | 4 条 | calculator {"expression": "1+1"} | ok，result = 2 | 1 → 0 | 追加结果 Observation，继续
3 | 6 条 | final "2" | 不执行工具 | 0 | 返回 status=ok，answer = "2"
messages　模型能看到的一切
每轮追加 2 条：assistant 原文 + Observation；final 只追加 1 条。
failures　连续失败计数
失败 +1，成功清零；超过 max_failures 就停，并带上原因。
seen　调用出现次数
以“工具名 + 参数”为键计数；同一调用累计 3 次判为无进展。

## 第 29 页 2.12 从第一天就记录调用链（Trace）

调试、评估都靠它
参考：第4周任务集与判定；第11周 Agent 评估与 Trace
{"task": "读取 test_report.txt，计算测试通过率", "status": "ok", "answer": "94%", "steps": 3, "trace": [ {"step": 1, "decision": {"action": "tool", "name": "read_file", "arguments": {"path": "test_report.txt"}}, "observation": {"status": "ok", "result": "passed=47\nfailed=3\n"}}, {"step": 2, "decision": {"action": "tool", "name": "calculator", "arguments": {"expression": "47/(47+3)*100"}}, "observation": {"status": "ok", "result": 94.0}}, {"step": 3, "decision": {"action": "final"}}]}  # 另含每步的 raw（模型原文）与 latency_s（耗时）
每一步记录什么
decision：工具名、参数或 final observation：status、result / type、message raw、latency_s：模型原文与耗时 失败：error 记录格式错误
之后谁会用它
第4周：任务集与成功判定 第7周：延迟与 Serving 基线 第11周：评估与失败分析

## 第 30 页 第1次课小结与过渡

本次课三句话
Agent = 循环 + 工具 + 状态；决策在模型，执行在应用。
循环靠 messages 与 Observation 推进，靠停止条件保证可控。
失败是常态：格式错、参数错、执行错，都要变成可处理的分支。
留给第2次课的三个问题
模型怎么“知道”有哪些工具、参数怎么写？
→ Function Schema（第3节）
模型给的 arguments 可信吗？
→ 参数校验（第4节）
工具怎么安全地执行，并把结果交回去？
→ 执行与回传（第4节）

## 第 31 页 本周任务：Agent v0 —— 调参对比与调用链分析

从写循环、写工具，到用真实模型跑通、看懂调用链
参考：assignment.md；README.md
任务
跑通 agent_v0.py：--selftest 全部 PASS 固定同一个任务，每次只调一项运行参数，连续跑 5 次（贪心/采样、temperature/top-p/top-k、模型规模…） 调用链分析：选 ≥2 条代表性 trace 逐步说明，横向对比 5 次的 status （可选加分）自选一项方法拓展：加生成停止条件 / 改 Prompt / 加新工具
提交内容
results/*.json：5 次运行，保留完整 trace 与模型原文，不要手工修改 report.md：按模板填写环境、5 次对照表、调用链分析 如做了拓展：改动后的 agent_v0.py（或改动说明）+ 对应运行结果
评分不看成功率：真实模型能不能跑对不是重点，评分主要看参数调整是否合理、trace 分析是否清晰。
截止时间与提交入口以课程通知为准。5 次运行请固定同一个任务，每次只改一项参数。

## 第 32 页 先看目标：这周要做什么

把前两次课讲过的循环和工具，合成一份能直接运行的实现
参考：agent_v0.py
目标：跑通“模型 → 工具 → Observation → 最终回答”这条完整闭环 范围：Agent Loop（run_agent）+ 三个工具（calculator/read_file/word_count）+ 三种模型后端 接下来按右边这张图，从①到⑥逐步说明每一步对应的代码与设计
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 33 页 ① 组装 messages：初始状态从哪来

system 里放协议约定和工具列表，user 里放这次的任务
参考：agent_v0.py
messages = [{"role": "system", "content": build_system_prompt()}, {"role": "user", "content": task}] trace, failures, seen = [], 0, Counter()  def build_system_prompt() -> str: specs = [{...} for n, t in TOOLS.items()] # specs 是每个工具的 JSON Schema return SYSTEM_TEMPLATE.replace("{tools}", ...)
工具列表由 TOOLS 注册表自动导出 JSON Schema，不是手写的 system 约定：模型每轮只能输出 tool 或 final 之一 messages 只增不改——历史必须保持完整
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 34 页 ② 调用模型：llm(messages) -> str

循环只依赖这一个接口，模型和服务换成什么都不影响循环本身
参考：agent_v0.py
raw = llm(messages) messages.append({"role": "assistant", "content": raw})
llm(messages) 是循环与模型之间唯一的接口 三种实现：ScriptedLLM／make_hf_llm／make_openai_llm 换模型或换服务只改这一层，循环本身不变
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 35 页 ③ 解析决策：两种合法输出

模型的原文先解析成结构化决策，再按 action 字段分流
参考：agent_v0.py
class ToolCall(BaseModel): action: Literal["tool"]; name: str; arguments: dict = {} class Final(BaseModel): action: Literal["final"]; answer: str  decision = parse_decision(raw) if decision.action == "final": return finish("ok", decision.answer)
ToolCall／Final 按 action 字段判别，自动选校验规则 解析失败是常态：计入失败预算，纠错提示回传给模型 final 直接结束循环；tool 才进入下一步真正执行
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 36 页 ④ 校验并执行：四道关卡

execute() 永远返回一个 dict，不向循环抛异常
参考：agent_v0.py
def execute(name, arguments): tool = TOOLS.get(name) if tool is None: return _err("unknown_tool", ...) try: args = tool.args.model_validate(arguments) except ValidationError as exc: return _err("invalid_arguments", ...) try: result = tool.fn(**args.model_dump()) return {"status": "ok", "result": result} except Exception as exc: return _err("execution_error", ...)
参数校验复用同一份 Pydantic 模型：一处定义，两处使用 工具不存在／参数错／执行异常，统一变成 error Observation 安全边界：read_file 路径沙箱、calculator 不用 eval
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 37 页 ⑤ Observation：结果怎么回到模型

工具真正做了什么，模型只能通过这段文字看到
参考：agent_v0.py
def observation_text(obs): text = "Observation: " + json.dumps(obs, ...) return text if len(text) <= MAX_OBS_CHARS \ else text[:MAX_OBS_CHARS] + "…(已截断)"  messages.append({"role": "user", "content": observation_text(obs)})
成功或报错都统一写回 messages，模型才能自我修正 MAX_OBS_CHARS 截断：工具输出不可控，避免撑爆上下文 写回之后，新一轮从②调用模型重新开始
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 38 页 ⑥ 停止条件：循环必须有出口

决策权在模型，所以必须由应用兜住模型的不可控
参考：agent_v0.py
failures = failures + 1 if obs["status"] == "error" else 0 if failures > max_failures: return finish("too_many_failures")  seen[(name, json.dumps(arguments, sort_keys=True))] += 1 if max(seen.values()) >= 3: return finish("no_progress")  # 步数用完仍未 final： return finish("max_steps")
四种 status：ok／max_steps／too_many_failures／no_progress 这四个出口就是 trace 里 status 字段的全部取值 都未触发就回到①，带着新 messages 进入下一轮
① 组装 messages
② 调用模型
③ 解析决策
④ 校验并执行
⑤ 回传 Observation
⑥ 停止条件检查
↓
tool ↓
final → 结束，返回最终回答
未触发停止条件 → 回到 ①，进入下一轮

## 第 39 页 调用链示例：一次真实运行的 trace

以作业默认任务为例，看 trace 里的每一步长什么样
参考：agent_v0.py 的 selftest T2；assignment.md
步 | 模型决策（raw） | 执行结果（Observation）
步 1 · read_file | {"action": "tool", "name": "read_file", "arguments": {"path": "test_report.txt"}} | Observation: {"status": "ok", "result": "passed=47\nfailed=3\n"}
步 2 · calculator | {"action": "tool", "name": "calculator", "arguments": {"expression": "47/(47+3)*100"}} | Observation: {"status": "ok", "result": 94.0}
步 3 · final | {"action": "final", "answer": "94%"} | 不执行工具，循环在这一步直接结束，status=ok
trace 里每一步还存了 latency_s；出问题先看卡在哪一步，再对照 raw/decision/observation 三者定位原因。

## 第 40 页 开始之前：几个注意事项

README 和作业里已经写过，这里再强调一遍，跑之前心里有数
参考：README.md；assignment.md
事项 | 具体来说 | 建议做法
小模型不好使 | 输出格式不稳定，甚至会编造工具调用结果 | 用调用链定位卡在哪一步，再判断是模型能力、Prompt 还是解码策略的问题
成功率不计分 | 真实模型的成功率不作为评分依据 | 评分主要看参数调整是否合理、trace 分析是否清晰
每次只改一项参数 | 5 次运行要能横向比较 | 固定同一个任务，一次只调一个变量（贪心/采样、temperature/top-p/top-k、模型规模）
工具有安全边界 | read_file 只能读工作目录内文件；calculator 不用 eval | 越权路径、非法表达式会被拒绝，属于预期行为，不是 bug
意外结果也要记录 | 可选拓展不要求做全套 | 达不到预期也如实记录改了什么、为什么、跑出什么效果
这几条原话来自 README.md 和assignment.md，动手前再读一遍这两个文件更保险。

## 第 41 页 3 Tool Calling 与 Function Schema：本节导读

先回答五个问题：学什么、怎么学、抓什么、难在哪、怎么解
目标
让模型“知道有什么工具、怎么调用”，让应用能稳定读懂它的调用请求。
方法
从演进脉络理解 Tool Calling；拆开一次调用的往返；拆解 Function Schema 的三要素。
重点
name / description / parameters 各自给谁看；同一份 Schema 既服务模型、也服务校验。
难点
description 与参数说明写不好，模型会选错工具、填错参数；本地小模型对此更敏感。
思路
用 Pydantic 一处定义参数：导出 Schema 给模型，复用同一份做校验；工具设计少而精。

## 第 42 页 3.1 一次工具调用涉及哪些部件

这些部件各在循环的哪一步起作用
参考：配套 agent_v0.py
① 组装 messages
build_system_prompt()
读 TOOLS，把每个工具的 name、description、参数 Schema 写进 system 消息  时机：循环开始前，一次 本课：第 3 节
② 调用模型
llm(messages)
唯一的模型接口：进去是 messages，出来是一段文本  时机：每轮一次 输出不可信，可能不合格
③ 解析决策
parse_decision(raw)
把文本变成 ToolCall（要调工具）或 Final（给回答）  时机：每轮，模型之后 失败：格式错误
④ 校验并执行
execute(name, args)
查表、校验参数、执行工具，统一成 Observation 字典  时机：仅当决策是 tool 永不抛异常：第 4 节
⑤ 写回 messages
observation_text(obs)
把字典转成文本，超长截断，作为 user 消息追加  时机：execute 之后 下一轮模型才看得到
TOOLS 注册表：工具名 → （函数，参数模型，描述）。① 读它生成给模型的声明，④ 读它查表、校验、执行——同一份定义，两处使用
绿色是本周新增的两处：声明（①） 与 执行（④）；蓝色是第 1 次课的循环骨架；深蓝是模型本身。

## 第 43 页 3.2 一个工具 = 声明 + 实现 + 注册

同一份定义：给模型看，也给应用用
参考：配套 agent_v0.py
@dataclass class Tool: fn: Callable            # 实现：真正干活的函数 args: type[BaseModel]   # 声明：参数模型（Pydantic） description: str        # 声明：写给模型的说明  TOOLS: dict[str, Tool] = { "calculator": Tool(calculator, CalculatorArgs, "计算算术表达式，返回数值结果。"), "read_file": Tool(read_file, ReadFileArgs, "读取工作目录内的文本文件，返回文件内容。"), }
声明：给模型看　→ build_system_prompt()
description 与参数模型导出的 Schema，一起写进 system 消息，模型据此决定“选哪个工具、填什么参数”。
实现：给应用用　→ execute()
按工具名查到 Tool；用 args 校验模型给的 arguments；校验通过才调用 fn。
读的是同一条注册项
新增一个工具 = 写函数 + 写参数模型 + 注册一行；Agent Loop（智能体循环）一行不用改。

## 第 44 页 3.3 工具调用的演进

从“在文本里找动作”到“协议化的调用请求”
参考：ReAct；OpenAI: Function calling；Qwen: Function Calling；Model Context Protocol
① 自由文本 + 正则
做法
提示模型写 Action: Search[xxx]，用正则抽取。
代价
格式脆弱；参数无法校验。
② Prompt 约定 JSON
system 中声明工具与 JSON 格式，客户端解析并校验。第2周 · 本课 v0
依赖模型遵循格式；解析与容错要自己写。
③ 原生 Function Calling
请求带 tools，响应返回结构化 tool_calls；服务端按模型的工具模板解析。
需要模型与服务支持（如 vLLM 的 tool parser）。
④ 标准化接入（MCP）
工具由独立服务提供，统一的发现与调用协议。第5周概念
多一层进程与协议；权限要单独管理。
本课用 ② 讲清原理（对任何模型都成立）；③ 与 ② 一一对应（第 37 页）；换到 vLLM 服务后可切换，循环不变。

## 第 45 页 3.4 一次工具调用的完整往返

应用、模型、工具三方，谁在什么时候做什么
参考：OpenAI: Function calling
应用（Agent Loop）
模型
工具
循环：② – ⑥ 重复，直到 final 或停止条件
① messages + 工具声明（Schema）
② 决策：name + arguments（一段文本）
③ 解析 · 校验 · 权限检查
④ 执行 fn(**args)
⑤ 结果 / 异常
⑥ Observation 写回 messages，再次调用
⑦ final：最终回答

## 第 46 页 3.5 往返里的每一步对应哪段代码

把往返图翻译成代码：谁做、调用什么、错了怎么办
参考：配套 agent_v0.py
步 | 谁做 | 做什么 | 对应代码 | 这一步出错时
① | 应用 | 把 messages（含工具声明）发给模型 | raw = llm(messages) | —
② | 模型 | 输出决策：一段文本 | raw（原文原样存进 messages） | 格式错误
③ | 应用 | 解析成决策；查表；校验参数 | parse_decision；execute 里的 TOOLS.get、model_validate | unknown_tool invalid_arguments
④ | 应用→工具 | 调用工具函数（权限检查在函数内） | tool.fn(**args.model_dump()) | execution_error
⑤ | 工具→应用 | 返回结果或抛出异常 | return / except Exception | 异常被转成 Observation
⑥ | 应用 | 转成 Observation，追加到 messages | observation_text(obs) 与 messages.append(...) | 过长则截断
⑦ | 模型 / 应用 | 再次决策，或 final；应用检查停止条件 | 回到 ②；Final 则返回 | max_steps too_many_failures

## 第 47 页 3.6 协议不同，循环相同

Prompt 约定与原生 tool_calls：声明、输出、解析、回传四处对应
参考：OpenAI: Function calling；vLLM: Tool Calling；Qwen: Function Calling
 | Prompt 约定（本课 v0） | 原生 tool_calls（API / vLLM）
声明工具 | 写进 system prompt 的文本 | 请求参数 tools（JSON Schema）
模型输出 | content 中的 JSON 文本 | tool_calls[i].function（name / arguments）
谁来解析 | 应用（parse_decision） | 服务端解析为结构化字段；应用仍要校验
结果回传 | user 消息：Observation: … | role=tool + tool_call_id
适用 | 任何模型，可读性强 | 需模型与服务端支持工具模板
for call in msg.tool_calls or []: args = json.loads(call.function.arguments)    # 注意：arguments 是 JSON 字符串 obs = execute(call.function.name, args) messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(obs)})

## 第 48 页 3.7 Function Schema 的三要素

name 给应用分发，description 给模型决策，parameters 给模型填参、给应用校验
参考：OpenAI: Function calling；JSON Schema
{"type": "function", "function": { "name": "calculator", "description": "计算算术表达式，返回数值结果。", "parameters": { "type": "object", "properties": {"expression": { "description": "算术表达式，只含数字、+ - * / 与括号", "minLength": 1, "type": "string"}}, "required": ["expression"], "additionalProperties": false}}}  # 由 Pydantic 自动导出（已省略 title 字段）
name
给应用
dispatch 的键；唯一、稳定、含义清楚。
description
给模型
“接口文档”：做什么、何时用、边界在哪。
parameters
给模型 + 应用
JSON Schema：模型据此填参数；应用据此校验。

## 第 49 页 3.8 description：写给模型的接口文档

写清“做什么、何时用、边界在哪”，模型才会选对
参考：Anthropic: Building effective agents（agent-computer interface）
位置 | 差 | 好
calculator 的描述 | 计算器 | 计算算术表达式（+ - * / 与括号），返回数值。需要精确计算时使用；不用于单位换算或执行代码。
read_file 的描述 | 读文件 | 读取工作目录内的文本文件并返回内容。path 为相对路径；目录外的文件会被拒绝。
参数 expression | expr | 算术表达式，例如 1024*1024；不含等号和单位。
写法要点
说明何时用、何时不用，并给一个示例值 工具多时，靠 description 拉开彼此的边界 效果只能靠固定任务集实测，没有理论标准（第4周任务集）

## 第 50 页 3.9 parameters：只需掌握五个关键字

type / properties / required / enum / additionalProperties
参考：Understanding JSON Schema；第2周 3.1–3.5
关键字 | 作用
type | 值的类型：string / integer / …
properties | 每个参数的类型与说明
required | 哪些参数必须出现
enum | 限定取值范围
additionalProperties | 是否允许多余参数（推荐 false）
其余关键字（pattern、anyOf、$ref…）遇到再查，课上不展开。
示例：path 必填；sort 可选，name 或 size
arguments | 结果 | 原因
{"path": "src"} | 合法 | —
{} | 缺参数 | 缺少必填的 path
{"path": "src", "sort": "date"} | 取值错 | sort 不在 enum 中
{"path": "src", "depth": 1} | 多余字段 | additionalProperties: false
{"path": 123} | 类型错 | path 应为 string

## 第 51 页 3.10 Pydantic：一处定义，两处使用

同一个参数模型：导出 Schema 给模型，也用来校验模型给出的 arguments
参考：Pydantic: Models；第2周 3.8
class CalculatorArgs(BaseModel): model_config = ConfigDict(extra="forbid", strict=True) expression: str = Field( min_length=1, description="算术表达式，只含数字、+ - * / 与括号")  # ① 给模型：导出 JSON Schema，放进工具声明 schema = CalculatorArgs.model_json_schema()  # ② 校验：模型给出的 arguments 必须通过同一份定义 #    不合法则抛出 ValidationError args = CalculatorArgs.model_validate(arguments)
为什么这样做
定义只有一份：Schema 与校验不会漂移 extra="forbid" ↔ additionalProperties: false strict=True：禁止 "12"→12 这类隐式转换 Field(description=…) 直接进入 Schema，模型可读
校验失败时 Pydantic 给出的信息（能定位到字段，直接回传给模型）：
expression: Field required unit: Extra inputs are not permitted

## 第 52 页 3.11 Schema 最终去了哪里

Schema 写进 system 消息，模型才“知道”有哪些工具
参考：配套 agent_v0.py
你是一个可以使用工具的助手。 可用工具（name、description 与参数的 JSON Schema）： [{"name": "calculator", "description": "计算算术表达式…" "parameters": {"properties": {"expression": {…}}, …}}, {"name": "read_file", …}]»  每一轮只输出一个 JSON 对象，不要输出其他文字： - 需要调用工具：{"action":"tool","name":"<工具名>","arguments":{...}} - 可以给出回答：{"action":"final","answer":"<最终回答>"} 工具的执行结果会以 "Observation: ..." 的形式返回。 拿到足够信息后再给出 final。
以上为 SYSTEM_TEMPLATE；红色处由 build_system_prompt() 生成，此处折叠。
红色部分
由 TOOLS 自动生成：每个工具的 name、description 与参数 Schema。
其余部分
输出协议：模型只能说 tool 或 final，Observation 怎样返回。
位置
messages[0]，role 为 system；每个任务生成一次，之后每轮随 messages 一起发给模型。
原生 tool calling：换位置，循环不变

## 第 53 页 3.12 工具设计：少而精、职责单一、参数强类型

工具是给模型用的接口：像设计接口一样设计工具
参考：Anthropic: Building effective agents（poka-yoke your tools）
原则 | 怎么做 | 为什么
少而精 | 先用 3–5 个工具覆盖任务 | 工具越多，选错概率越高，提示越长（小模型更明显）
职责单一 | 一个工具只做一件事 | description 边界清晰，模型不用猜
参数少且强类型 | 能用 enum 就不用自由文本；路径用相对路径 | 减少填错空间（防呆：让错误更难发生）
返回可读 | 结构化、简短、带 status | Observation 直接进入上下文
标注副作用 | 只读工具与写入工具分开；写入前确认 | 安全边界在应用，不在模型
v0 建议只接入只读工具（calculator、read_file 及你的自选工具）。

## 第 54 页 4 参数校验、工具执行与结果回传：本节导读

先回答五个问题：学什么、怎么学、抓什么、难在哪、怎么解
目标
让模型给出的每一次调用都先被检查、再被执行，结果可靠地回到模型手里。
方法
把“arguments → Observation”拆成四道关卡：工具存在？参数合法？允许执行？执行成功？
重点
校验与执行的失败都转成 Observation，让模型有机会自我修正，而不是让程序崩溃。
难点
安全边界（不 eval、限制路径）；分清“参数合法 / 执行成功 / 结果正确”三个层次。
思路
execute() 永远返回结构化结果；用 selftest 覆盖未知工具、缺参数、除零、越权四类失败。

## 第 55 页 4.1 execute()：应用侧的统一入口

循环第④步：把模型的“请求”变成可靠的结果
参考：配套 agent_v0.py
① 组装 messages
② 调用模型  llm(messages)
③ 解析决策  parse_decision
④ 校验并执行  execute(name, arguments)
⑤ Observation 写回 messages
⑥ 停止条件检查，回到 ②
输入（来自模型，不可信）
name：工具名字符串；arguments：参数字典。可能不存在、缺字段、多字段、类型不对。
输出（永远是 dict）
成功 {"status":"ok","result":…}；失败 {"status":"error","type":…,"message":…}。
边界（它不做什么）
不修改 messages；不决定继续还是停止；不向循环抛异常。
分工：run_agent 决定“做什么、何时停”，execute 只回答“这次调用能不能做、结果是什么”。

## 第 56 页 4.2 从 arguments 到执行：四道关卡

模型给的参数不可信：逐关检查，每关失败都有明确的类型
参考：OpenAI: Function calling；Pydantic: Models
① 工具存在？
TOOLS.get(name)
unknown_tool
② 参数合法？
Pydantic：类型 · 必填 · 多余 · 取值
invalid_arguments
③ 允许执行？
路径在工作目录内；表达式在白名单内
permission / execution_error
④ 执行成功？
try/except；必要时超时
execution_error
每道关卡失败 → 转成错误 Observation 回传（不抛异常、不崩溃）
三个不同的层次
参数合法 关卡 ①②③
执行成功 关卡 ④
结果正确 任务集评估（第4/11周）
前两层由 execute() 负责；“结果是否正确”靠任务集评估，校验解决不了。

## 第 57 页 4.3 走查：一次成功的调用

跟着数据走：从模型原文到 Observation
参考：配套 agent_v0.py
模型原文  raw
{"action": "tool", "name": "calculator", "arguments": {"expression": "47/(47+3)*100"}}
parse_decision(raw)
ToolCall(action='tool', name='calculator', arguments={'expression': '47/(47+3)*100'})
关卡①② 查表·校验
TOOLS.get("calculator")   → 命中 CalculatorArgs.model_validate({'expression': '47/(47+3)*100'})   → 通过
关卡③④ 权限·执行
calculator(expression='47/(47+3)*100')   → 94.0 execute 返回：{'status': 'ok', 'result': 94.0}
observation_text(obs)
Observation: {"status": "ok", "result": 94.0} # 追加到 messages：{"role": "user", "content": …}
四道关卡全部通过，模型下一轮看到的只有最后一行。

## 第 58 页 4.4 走查：一次失败的调用

同一条路，在第二关被拦下
参考：配套 agent_v0.py
模型原文  raw
{"action": "tool", "name": "calculator", "arguments": {"expr": "1+1"}}
parse_decision(raw)
ToolCall(action='tool', name='calculator', arguments={'expr': '1+1'}) # 格式合法：这一层不检查参数名
关卡① 查表
TOOLS.get("calculator")   → 命中
关卡② 校验（失败）
CalculatorArgs.model_validate({'expr': '1+1'})   → 失败 expression: Field required；expr: Extra inputs are not permitted
execute 返回
{'status': 'error', 'type': 'invalid_arguments', 'message': 'expression: Field required; expr: Extra inputs are not permitted'} # tool.fn 没有被调用
回传，进入下一轮
Observation: {"status": "error", "type": "invalid_arguments", "message": "expression: Field required; expr: Extra inputs are not permitted"} # failures = 1（≤ max_failures），继续循环
错误写明“缺哪个字段、多了哪个字段”，模型下一轮才改得对。

## 第 59 页 4.5 失败类型与回传给模型的信息

错误信息要定位到字段、给出可选项，模型才修得动
参考：Pydantic: Error Handling；agent_v0.py 的真实输出
类型 | 触发示例 | 回传给模型的 message
unknown_tool | 调用 run_tests(target=…) | 未知工具 'run_tests'，可用工具：['calculator', 'read_file']
invalid_arguments 缺必填字段 | calculator，参数 {} | expression: Field required
invalid_arguments 多余字段 | calculator，参数 {"expression": "1+1", "unit": "cm"} | unit: Extra inputs are not permitted
invalid_arguments 类型错误 | calculator，参数 {"expression": 12} | expression: Input should be a valid string
execution_error 执行异常 | calculator(“1/0”) | ZeroDivisionError: division by zero
execution_error 越权 | read_file("../.env") | PermissionError: 只允许读取工作目录内的文件

## 第 60 页 4.6 两层检查：parse_decision 与 execute

同样是“模型说错了”，错在哪层由哪层处理
参考：配套 agent_v0.py
模型原文 raw
层 1  parse_decision 是合法的决策吗？
ToolCall
层 2  execute 这次调用能做吗？
dict
Observation 追加到 messages
format_error
unknown_tool invalid_arguments execution_error
层 | 检查什么 | 依据 | 回传给模型的提示
1 parse_decision | 有 JSON 对象；action 是 tool 或 final；字段齐全 | Decision 模型，与具体工具无关 | “输出格式错误，请只输出一个符合要求的 JSON 对象。”
2 execute | 工具已注册；参数符合该工具的 Schema；执行成功 | TOOLS 与各工具的参数模型 | 指到字段的 message，如 expression: Field required
例：模型只回了一句“好的，我来算一下”，层 1 抛出 ValueError: 输出中没有 JSON 对象，记为格式错误。

## 第 61 页 4.7 execute()：校验、执行、异常隔离

永远返回 dict，不向循环抛异常
参考：本课配套 agent_v0.py
def execute(name: str, arguments: dict) -> dict: tool = TOOLS.get(name) if tool is None: names = list(TOOLS) return _err("unknown_tool", f"未知工具 {name!r}，可用工具：{names}") try: args = tool.args.model_validate(arguments) except ValidationError as exc: msg = "; ".join(_fmt(e) for e in exc.errors()) return _err("invalid_arguments", msg) try: result = tool.fn(**args.model_dump()) return {"status": "ok", "result": result} except Exception as exc:                  # 工具失败不能打断循环 return _err("execution_error", f"{type(exc).__name__}: {exc}")
查表
工具名不在 TOOLS → unknown_tool，并列出可用工具
校验
同一份参数模型校验；用 loc 定位字段
执行
工具是外部代码：任何异常都转成 execution_error

## 第 62 页 4.8 安全执行：模型的输出是不可信输入

用白名单语法树，而不是 eval；路径先规范化再比较
参考：Python: ast；OWASP 输入校验原则
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}  def calculator(expression: str): # 不使用 eval：只放行“数字、四则运算、负号”这几类语法树节点。 def ev(n): t = type(n) if t is ast.Constant and type(n.value) in (int, float): return n.value if t is ast.BinOp and type(n.op) in _BIN: return _BIN[type(n.op)](ev(n.left), ev(n.right)) if t is ast.UnaryOp and type(n.op) is ast.USub: return -ev(n.operand) raise ValueError("表达式含有不支持的语法") return ev(ast.parse(expression, mode="eval").body)
若用 eval
模型输出 __import__('os')… 就会在你的机器上执行任意代码。
白名单语法树
只放行：数字、+ - * /、负号 函数调用、属性、** 一律拒绝 拒绝 → 错误 Observation
read_file 同理：resolve() 后用 is_relative_to(工作目录) 检查，拒绝 ../ 越出。这两项在 selftest（T8 与“拒绝非法表达式”）里都有用例。

## 第 63 页 4.9 read_file：路径沙箱怎么防越权

只读、有边界：接入真实文件前的第一道防线
参考：配套 agent_v0.py
def read_file(path: str) -> str: root = WORKDIR.resolve() target = (root / path).resolve() if not target.is_relative_to(root): raise PermissionError("只允许读取工作目录内的文件") if not target.is_file(): raise FileNotFoundError(f"文件不存在：{path}") return target.read_text(encoding="utf-8")
先规范化，再比较：resolve() 折叠 ../ 并解析符号链接；is_relative_to 按路径分量比较，不会被“/work-evil”这样的前缀蒙混。 错误只回显相对路径：不暴露绝对路径（最小披露）。
path 参数 | execute("read_file", …) 的结果
test_report.txt | ok：返回文件内容
sub/../test_report.txt | ok：规范化后仍在目录内
../.env | PermissionError：越出目录
/etc/passwd | PermissionError：绝对路径不在目录内
link/hostname | PermissionError：符号链接指向目录外
nofile.txt | FileNotFoundError：文件不存在：nofile.txt
除读取成功外，错误都归为 execution_error。对模型而言，“不允许”和“出错了”都是该换个做法的信号。

## 第 64 页 4.10 异常、超时与副作用

工具失败不能打断循环；有副作用的工具要额外设防
参考：OpenAI: Function calling；Anthropic: Building effective agents
风险 | 例子 | 应对
抛异常 | 文件不存在、除零 | try/except → error Observation（execute 已做）
耗时过长 | 网络请求、大文件 | 设超时；超时同样转成 error Observation
输出过大 | 读取大文件 | 截断到 MAX_OBS_CHARS，注明已截断
越权访问 | ../../etc/passwd | 路径规范化 + 工作目录白名单
有副作用 | 写文件、发请求、删除 | 只读/写入分离；写入前确认；设计成幂等（重复调用无害）
模型可能重复调用同一个工具——所以有副作用的工具一定要幂等，或在 v0 阶段不接入。

## 第 65 页 4.11 observation_text()：结果如何回到模型

回传前的最后一步：序列化、截断、写回
参考：配套 agent_v0.py
def observation_text(obs: dict) -> str: text = "Observation: " + json.dumps( obs, ensure_ascii=False, default=str) if len(text) <= MAX_OBS_CHARS:      # 2000 return text return text[:MAX_OBS_CHARS] + "…(已截断)"  # 在循环里： messages.append({"role": "user", "content": observation_text(obs)})
三种情形（真实输出）
成功
Observation: {"status": "ok", "result": 94.0}
失败
Observation: {"status": "error", "type": "invalid_arguments", "message": "…
过长
读 3000 字符的文件：序列化后 3043 字符 → 截断为 2000 字符 + “…(已截断)”
ensure_ascii=False
中文保持原样，省 token，模型也更容易读。
default=str
遇到 Path、datetime 等无法 JSON 化的结果，转成字符串，回传这一步不会自己崩溃。
截断并标注“已截断”
防止一次输出撑爆上下文，也避免模型把截断的内容当成完整内容。

## 第 66 页 4.12 结果回传：让模型看到，并对应到请求

两种协议的写法；多个调用时逐个执行、逐个回传
参考：OpenAI: Function calling
Prompt 约定（本课 v0）
messages.append( {"role": "assistant", "content": raw}) messages.append( {"role": "user", "content": "Observation: " + obs_json})
原生 tool_calls
messages.append(msg)   # 先入列含 tool_calls 的消息 for call in msg.tool_calls: obs = execute(...) messages.append({ "role": "tool", "tool_call_id": call.id, "content": json.dumps(obs)})
要点
tool_call_id 把结果与对应的请求关联起来；缺失或顺序不对，服务端通常会报错 一次返回多个 tool_calls：逐个执行、逐个回传，各带自己的 id content 一律是字符串；Responses API 对应 function_call_output + call_id

## 第 67 页 4.13 错误反馈让模型自我修正

一次失败不等于任务失败：错误 Observation 就是修正线索
参考：agent_v0.py --selftest（T4a，脚本化模型）
Step 1
决策
calculator  {"expr": "1+1"}
Observation
invalid_arguments: expression: Field required; expr: Extra inputs are not permitted
Step 2
calculator  {"expression": "1+1"}
{"status": "ok", "result": 2}
Step 3
final  "2"
失败预算怎么用
连续失败 ≤ max_failures：继续，给模型修正机会 一次成功：失败计数清零 超过预算：too_many_failures 受控退出 每次失败都留在 trace 里，可复盘
trace 为脚本化模型的真实结构；用于说明机制，非模型成功率。

## 第 68 页 4.14 小模型的现实：靠工程兜底

1.5B 级本地模型的工具调用会更不稳定——用工程手段，而不是靠 Prompt 祈祷
参考：Qwen: Function Calling；vLLM: Tool Calling；BFCL
常见现象（经验性，请用自己的 trace 核对）
多写解释文字或 Markdown 代码围栏 键名拼错、漏参数、类型不对 该调用时不调用；不该调用时调用 重复同一个调用，或没查就直接回答
工程手段
temperature=0，降低随机性 Prompt 里给一个完整示例 解析容错 + 纠错 Observation 失败预算与无进展检测 换更大的模型 + 原生 tool calling（第6–7周，DGX Spark）
作业评分看闭环是否完整、错误是否被处理、调用链是否可读，不看模型答对多少。

## 第 69 页 5.1 Agent v0：四个稳定接口

之后各周都往这四个接口上“挂”能力，而不是重写
参考：本课配套 agent_v0.py；顶点课程 16 周课程安排
Agent Loop run_agent(task, llm) 输出 {status, answer, steps, trace}
模型接口 llm(messages) → str
工具注册表 TOOLS = {name: Tool(fn, 参数模型, 描述)}
状态 messages · failures · seen
Trace 每步：决策 · Observation → results/run.json
第7周：换 vLLM 服务
第5–6周：新工具 · RAG
第5周：Memory
第4 / 11周：任务集与评估
输入：任务（字符串）　输出：{status, answer, steps, trace}

## 第 70 页 本周回顾与下一步

本周回顾
Agent = 循环 + 工具 + 状态；决策在模型，执行在应用 循环靠 messages 与 Observation 推进，靠停止条件保证可控 Function Schema：name 给应用、description 给模型、parameters 两者共用 参数要过四道关卡；失败都转成 Observation，让模型自我修正 交付：Agent v0 = 四个稳定接口 + 可复现的 trace

## 第 71 页 课外参考资料与自学清单

推荐阅读（按优先级）
Anthropic · Building effective agents
Agent 与 Workflow 的区别、工具设计（ACI）
ReAct 论文（Yao et al., ICLR 2023）
推理与行动交替的来龙去脉
OpenAI · Function calling 指南
tools、tool_calls、function_call_output 的接口形态
Pydantic 文档 · Models
参数模型、Schema 导出、严格模式
