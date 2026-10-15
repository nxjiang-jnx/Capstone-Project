# 第二周课件：结构化输出与结果处理

原始文件：`structured-output-and-result-processing.pptx`

## 第 1 页 LLM Application

OpenAI API、Structured Output、JSON Schema、异常处理与结果解析 2026 秋季

## 第 2 页 本次课程内容

OpenAI API
请求描述结果，响应进入程序
Structured Output
受约束解码及其系统开销
JSON Schema
数据约束与 Python 类型定义
异常处理与结果解析
完成状态、验证、重试与流式结果

## 第 3 页 1.1 数学辅导应用的结果结构

同一份模型回答，需要分步骤显示，也需要单独读取答案
输入：how can I solve 8x + 7 = −23
{ "steps": [ { "explanation": "Subtract 7 ...", "output": "8x + 7 - 7 = -23 - 7" }, ... ], "final_answer": "x = -15/4" }
应用按字段展示
1  两边同时减去 7 8x = −30  2  两边同时除以 8 x = −15/4
最终答案   x = −15/4
参考：OpenAI Cookbook: Structured Outputs

## 第 4 页 1.2 API 响应与模型生成内容

外层描述一次调用，message.content 承载模型生成的字符串
choice = response.choices[0] message = choice.message  choice.finish_reason # "stop"  message.content # '{"steps": [...], #   "final_answer": "x = -15/4"}'  response.usage
SDK 已处理 HTTP 响应 并构造 response 对象。
content 仍是字符串。 需要继续解析其中的 JSON， 再检查应用需要的字段。
请求完成状态和内容校验分别读取。
参考：OpenAI Python SDK: Parsing helpers；OpenAI: Structured Outputs

## 第 5 页 1.3 结构化请求的组成

Prompt 给出任务，response_format 将结构约束发给服务端
response = client.chat.completions.create( model=MODEL_ID, messages=messages, response_format={ "type": "json_schema", "json_schema": { "name": "math_reasoning", "strict": True, "schema": MATH_SCHEMA } } )
messages
描述要解决的问题。
MATH_SCHEMA
定义结果的字段和类型。 模型与服务端需要支持 这项生成约束。
参考：OpenAI: Structured Outputs；OpenAI Cookbook: Structured Outputs

## 第 6 页 1.4 OpenAI API、接口与 Python SDK

Chat Completions 与 Responses 都属于 OpenAI API
OpenAI API
模型服务接口的总称，下面是其中两套生成接口。
Chat Completions API
POST /v1/chat/completions
以对话消息组织一次生成
Responses API
POST /v1/responses
以不同类型的 item 表达生成过程
同一个 Python SDK 可以调用两套接口
client.chat.completions.create(...)
client.responses.create(...)
Responses 是后续演进的接口。官方推荐新项目使用它，Chat Completions 仍受支持。
参考：OpenAI: Migrate to the Responses API；OpenAI Python SDK

## 第 7 页 1.5 消息、工具调用与上下文

Agent 的工具交互需要表示中间步骤，并将结果交回模型
Chat Completions：messages
Responses：typed items
assistant.message tool_calls: [...]  tool.message tool_call_id: "call_1"
function_call call_id: "call_1"  function_call_output call_id: "call_1"
通常由应用维护消息列表， 下一次请求带上所需历史。
可手动维护，也可使用 previous_response_id 关联上次调用。
自定义函数仍由应用执行。Responses 另提供平台内置工具及推理项支持。
关联历史仍受上下文窗口限制，历史输入仍计入 token 费用。
参考：OpenAI: Migrate to the Responses API；OpenAI: Conversation state

## 第 8 页 1.6 结构化输出的两套接口用法

同一个结果类型，使用不同的参数和解析结果入口
位置 | Chat Completions | Responses
输入 | messages | input
原始结构配置 | response_format | text.format
Pydantic helper | chat.completions.parse(   response_format=Model) | responses.parse(   text_format=Model)
解析后对象 | choices[0].message.parsed | output_parsed
示例沿用 Chat Completions 以衔接上一讲。Schema、解析与校验原则适用于两套接口。
参考：OpenAI: Structured Outputs；OpenAI Python SDK: Parsing helpers；OpenAI Python SDK

## 第 9 页 1.7 结构化回答与工具调用

结果交给谁，决定应用随后执行什么操作
结构化回答
{ "steps": [...], "final_answer": "x = -15/4" }
验证 MathReasoning 交给页面显示
模型返回的工具调用请求
tool_call.function.name # "read_file"  tool_call.function.arguments # '{"path":"main.py"}'
校验参数与执行条件 应用调用工具，再回传结果
参考：OpenAI: Structured Outputs；OpenAI Python SDK: Parsing helpers

## 第 10 页 2.1 输出模式提供不同的约束

JSON 语法正确，与满足应用 Schema，是不同的检查
方式 | 生成侧约束 | 仍要检查
Prompt 要求 JSON | 模型遵循文字要求 | JSON 语法、字段和类型
JSON mode | 正常完整输出为合法 JSON | 字段和类型
Structured Outputs strict: true | 遵守受支持的 Schema | 完成状态、拒答与业务正确性
{"answer": "-15/4"}
JSON 合法，但缺少 steps / final_answer。
参考：OpenAI: Structured Outputs

## 第 11 页 2.2 Prompt 与 Schema 的分工

结构约束确定可接受的形状，Prompt 描述应该完成的任务
任务要求
逐步求解方程，解释每次等式变换，给出化简后的答案。
同一 Schema 下的两个 final_answer
"x = -15/4"
"x = 4"
8 × (−15/4) + 7 = −23 满足原方程
8 × 4 + 7 = 39 不满足原方程
参考：OpenAI Cookbook: Structured Outputs；OpenAI: Structured Outputs

## 第 12 页 2.3 受约束解码的下一 Token 选择

语法状态根据当前前缀，动态排除不合法的候选
Schema 规定 done 为布尔值。图中展示连续两个生成位置。
冒号后允许 true / false；值生成完成后，合法延续变为分隔符。
参考：MLC: XGrammar；XGrammar, MLSys 2025

## 第 13 页 2.4 受约束生成的系统开销

Schema 编译与逐步掩码计算，也进入生成的关键路径
参考：MLC: XGrammar；XGrammar, MLSys 2025
Grammar Compilation
将结构规则编译成 运行时可使用的表示。
Mask Gen
根据当前语法状态， 计算合法 token 掩码。
Apply Mask
将掩码应用到 logits， 屏蔽不合法的候选。
Sampling
从合法候选中 选出下一个 token。
上：CPU / GPU 相互等待。 下：编译、掩码计算与 GPU 工作部分重叠。

## 第 14 页 3.1 properties 与 required

定义字段约束后，还要明确该字段是否必须出现
{ "type": "object", "properties": { "final_answer": {"type": "string"} }, "required": ["final_answer"] }
不通过
{}
缺少 final_answer
通过
{"final_answer":"x = -15/4"}
properties 本身不会要求字段存在。
参考：JSON Schema: object

## 第 15 页 3.2 additionalProperties

对象默认允许未知字段，需要显式关闭额外字段
{ "type": "object", "properties": { "final_answer": {"type": "string"} }, "required": ["final_answer"], "additionalProperties": false }
输入
{ "final_answer": "x = -15/4", "confidence": 0.99 }
confidence 没有被声明， 因此验证失败。
参考：JSON Schema: object；OpenAI: Structured Outputs

## 第 16 页 3.3 缺失字段与 null

“没有这个字段”和“这个字段的值未知”可以分别表达
"properties": { "answer": { "type": ["string", "null"] } }, "required": ["answer"]
{}
不通过：字段缺失
{"answer": null}
通过：值可为 null
{"answer": "42"}
API 要求字段必填时，可用包含 null 的类型表示无答案。
参考：JSON Schema: object；OpenAI: Structured Outputs；JSON Schema: enum；Pydantic: Models

## 第 17 页 3.4 嵌套对象、数组与 $ref

MathReasoning 的 steps 是 Step 对象组成的数组
{ "$defs": { "Step": { "type": "object", "properties": { "explanation": {"type": "string"}, "output": {"type": "string"} }, "required": ["explanation", "output"], "additionalProperties": false } } }
外层 steps 字段
"steps": { "type": "array", "items": { "$ref": "#/$defs/Step" }, "minItems": 1 }
items 检查每个元素。 minItems 限制元素数量。
参考：JSON Schema: array；JSON Schema: structuring；OpenAI Cookbook: Structured Outputs

## 第 18 页 3.5 枚举与数值范围

能由数据契约表达的边界，应交给验证器检查
状态枚举
"status": { "type": "string", "enum": ["ok", "unknown"] }
"status": "maybe"
失败：值不在允许的集合中。
非负整数
"count": { "type": "integer", "minimum": 0 }
"count": -1
失败：整数类型正确，范围错误。
参考：JSON Schema: enum；JSON Schema: numeric

## 第 19 页 3.6 pattern 与描述性注解

pattern 可以被检查，description 用于解释字段含义
"ticket_id": { "type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$", "description": "工单编号，例如 ABC-2026" }
匹配
"ABC-2026"
不匹配
"abc-2026"
^ 与 $ 约束整串。 缺少锚点时，通常按 “存在匹配子串”检查。
参考：JSON Schema: string；JSON Schema: annotations

## 第 20 页 3.7 anyOf 与结果分支

一个字段可以承载多种合法类型，分支必须有明确的数据约定
"result": { "anyOf": [ {"type": "string"}, {"type": "null"} ] }
"有答案" 或 null
至少满足一个分支。 复杂任务也可以让分支 各自拥有不同对象结构。
oneOf：恰好一个分支成立。  allOf：每个分支都成立。
参考：JSON Schema: combining；OpenAI: Structured Outputs

## 第 21 页 3.8 用 Pydantic 保持类型与 Schema 一致

同一份模型定义，可以导出 Schema，也可以验证返回文本
class Step(BaseModel): model_config = ConfigDict(extra="forbid") explanation: str output: str  class MathReasoning(BaseModel): model_config = ConfigDict(extra="forbid") steps: list[Step] = Field(min_length=1) final_answer: str
schema = MathReasoning.model_json_schema() obj = MathReasoning.model_validate_json(raw, strict=True)
禁止额外字段 需要逐层声明。
Field 约束 进入导出的 Schema。
参考：Pydantic: Models；Pydantic: JSON Schema；Pydantic: Strict Mode；OpenAI Python SDK: Parsing helpers

## 第 22 页 3.9 SDK 的 parse helper

Pydantic 模型可以直接交给 SDK，用于请求配置与响应解析
completion = client.chat.completions.parse( model=MODEL_ID, messages=messages, response_format=MathReasoning )  message = completion.choices[0].message if message.parsed is not None: answer = message.parsed.final_answer
模型类
SDK 根据模型类 生成严格 Schema。
Python 对象
解析后可以按属性 读取字段。
参考：OpenAI Python SDK: Parsing helpers；OpenAI: Structured Outputs

## 第 23 页 3.10 Pydantic 的类型转换与 strict

是否允许字符串转成数字，是客户端验证策略的一部分
class Count(BaseModel): count: int  data = {"count": "3"}
默认验证
Count.model_validate(data) # Count(count=3)
严格验证
Count.model_validate(data, strict=True) # ValidationError: int_type
输入值为字符串 "3"。 默认验证可转换为整数， strict=True 拒绝该转换。
参考：Pydantic: Strict Mode；Pydantic: Models

## 第 24 页 3.11 Schema 之外的业务关系

两个字段各自类型正确，合在一起仍可能不满足业务约束
class Range(BaseModel): start: int end: int  @model_validator(mode="after") def check_order(self): if self.start > self.end: raise ValueError("start > end") return self
{"start": 8, "end": 3}
两个字段均为整数， 但区间顺序错误。
自定义 validator 在本地运行，不会自动变成服务端的生成规则。
参考：Pydantic: Validators；Pydantic: JSON Schema

## 第 25 页 3.12 标准 Schema 与服务支持范围

本地验证器认可的 Schema，生成 API 可能不接受
本地可以定义
{ "allOf": [ {"type": "integer"}, {"minimum": 0} ] }
OpenAI 严格输出的接口要求
根节点为 object 所有字段列入 required 每层对象关闭额外字段
allOf 不在支持子集中。 不能直接将左侧用作输出 Schema。
固定模型、服务端与 Schema 版本， 用一次请求验证兼容性。
参考：OpenAI: Structured Outputs；python-jsonschema: Validation

## 第 26 页 4.1 完成状态决定内容如何处理

检查正文之前，先区分正常回答、工具调用与未完成输出
choice = response.choices[0] msg = choice.message  if msg.refusal: show_refusal(msg.refusal) elif choice.finish_reason == "tool_calls": handle_tool_calls(msg.tool_calls) elif choice.finish_reason != "stop": record_incomplete(choice.finish_reason) else: consume_complete_text(msg.content)
拒答
工具请求
截断 / 过滤
完整正文
参考：OpenAI: Structured Outputs；OpenAI Python SDK: Parsing helpers

## 第 27 页 4.2 完整结果的解析与消费

只在完成状态通过后，将文本转成应用对象
try: obj = MathReasoning.model_validate_json( raw_text, strict=True ) except ValidationError as exc: save_validation_errors(exc.errors()) else: check_business_rules(obj) render_steps(obj.steps) show_answer(obj.final_answer)
解析 JSON 验证字段
保留错误位置， 再决定重试或反馈。
按业务规则检查后， 读取类型化字段。
参考：Pydantic: Models；OpenAI Python SDK: Parsing helpers；Pydantic: Error Handling

## 第 28 页 4.3 验证错误的字段定位

错误信息把“格式不对”定位到具体字段和预期类型
输入对象
{ "steps": [ {"explanation": "Subtract 7.", "output": 123} ], "final_answer": "x = -15/4" }
ValidationError.errors() 节选
loc: ("steps", 0, "output") type: "string_type" msg: "Input should be a valid string"
steps 数组的第 1 个元素中，output 应为字符串。
参考：Pydantic: Error Handling；Pydantic: Strict Mode

## 第 29 页 4.4 API 异常与重试预算

失败原因不同，重新发送同一个请求的价值也不同
try: response = client.chat.completions.create(...) except APIConnectionError: handle_connection_failure() except APIStatusError as exc: record_error(exc.status_code, exc.request_id)
请求本身有问题
400 / 无效 Schema 修改请求后再试。
临时失败
部分连接错误 / 5xx 限次退避，计入总预算。
限流或配额
429 需要看错误详情， 配额耗尽不能靠重试解决。
参考：OpenAI Python SDK

## 第 30 页 4.5 校验失败后的修复反馈

把具体错误反馈给模型，限制次数，并重新验证完整结果
验证器定位的问题
loc: ("steps", 0, "output") type: "string_type"
反馈内容
steps[0].output 必须是字符串。请根据原方程重新检查， 返回完整结果，保留 steps 和 final_answer 的结构。
记录本次原文与错误， 只允许有限次重新生成。  新结果仍需检查完成状态， 并重新通过完整验证。
参考：Pydantic: Error Handling；OpenAI: Structured Outputs

## 第 31 页 4.6 结构化结果在 Agent 中的位置

模型提供结构化决策，应用保留执行控制与状态更新
for call in message.tool_calls or []: args = ReadFileArgs.model_validate_json( call.function.arguments, strict=True ) check_allowed_path(args.path) result = read_file(args.path) messages.append({ "role": "tool", "tool_call_id": call.id, "content": result })
参数解析
执行条件检查
工具执行与异常处理
调用 ID 关联结果， 下一轮继续使用。
参考：OpenAI Python SDK: Parsing helpers；OpenAI: Structured Outputs

## 第 32 页 4.7 Streaming 中的 JSON 前缀

一个合法完整结果，在中间时刻通常还不能解析成完整 JSON
连续收到的正文片段
1   {"steps":[ 2   {"explanation":"Subtract 7.", 3   "output":"8x = -30"}], 4   "final_answer":"x = -15/4"}
前 3 段未闭合外层对象。 第 4 段形成完整 JSON。
buffer += delta.content or "" # 结束事件确认完成后 obj = MathReasoning.model_validate_json(buffer)
参考：OpenAI Python SDK: Parsing helpers；OpenAI: Structured Outputs

## 第 33 页 4.8 结果日志中的状态与计时

结构通过、业务通过和请求耗时，应分别记录
{ "request_id": "...", "schema_version": "v1", "finish_reason": "stop", "status": "schema_valid", "functional_correctness": "not_tested", "attempt": 1 }
状态区分
请求是否成功 结果是否完成 字段是否通过 业务是否通过
计时边界
客户端总耗时与 服务端生成耗时分开。
日志字段示意；request_id 用于关联服务端请求。
参考：OpenAI Python SDK；Pydantic: Error Handling

## 第 34 页 4.9 JSONSchemaBench 的评估视角

同一项研究同时检查生成速度、Schema 覆盖和任务准确率
A  效率
纵轴 Token/s，比较不同 Schema 集 上的生成速度。
B  覆盖率
检验实际支持的 Schema， 不能只看是否接收某个配置字段。
C  任务质量
纵轴准确率，比较下游任务结果。
原图：JSONSchemaBench Figure 1，2025 年论文实验；不代表当前版本排名。
参考：JSONSchemaBench, 2025

## 第 35 页 课外参考资料

OpenAI Cookbook / Python SDK
Math tutor 示例、parse helper、流式事件与错误处理。
Understanding JSON Schema
对象、数组、组合约束与可直接验证的数据实例。
Pydantic 文档
模型定义、Schema 导出、严格模式与自定义验证器。
XGrammar / JSONSchemaBench
生成约束的执行机制，以及效率、覆盖率和质量评估。
