# 第二周课件：LLM 应用开发基础

原始文件：`llm-application-basics.pptx`

## 第 1 页 LLM Application

Prompt、Python Client、REST/API、Streaming 2026 秋季

## 第 2 页 目录

一次模型调用，贯穿四个部分
讲授内容 | 这一部分需要理解的问题
1  Prompt | 程序怎样组织任务、当前数据和对话历史
2  Python Client | 怎样发起调用、控制生成并读取返回值
3  REST/API | 请求与响应如何跨越应用和服务的边界
4  Streaming | 逐步生成的结果怎样传回、消费和衡量

## 第 3 页 一次模型调用的应用与服务

应用负责组织任务，推理服务负责运行模型
应用侧
构造输入 选择模型与生成设置 解释返回值
服务侧
接收请求、调度计算 运行模型、返回结果
参考：Huyen：AI Engineering，Fig9-1

## 第 4 页 1.1 Prompt 的组成

任务说明、示例和当前输入承担不同作用
任务说明定义输出要求；示例展示映射；变量位置填入本次数据。
参考：Huyen：AI Engineering，Fig5-1

## 第 5 页 1.2 应用任务与预期输出

举例，对于客户投诉，应用需要 LLM 输出可识别的分类标签
客户输入
“The app is crashing and my phone is overheating” 应用崩溃，同时手机发热。
预期输出
Software Bug, Hardware Malfunction
应用如何使用
解析为两个标签，再由程序匹配相应处理规则。 自由解释、拼写变化或遗漏标签都会影响后续处理。
分类范围：Software Bug、Hardware Malfunction、User Error、Feature Request、Service Outage
参考：Anthropic：Classification Evals

## 第 6 页 1.3 输出格式也是任务约定

两个标签都答对了，为什么程序仍判错？
公开 Notebook 保存的输出
Hardware Malfunction Software Bug
评估程序按逗号分隔
response.split(',')
模型给出的内容 | 解析后的集合 | 与标准答案比较
换行分隔的两个标签 | 只有一个字符串元素 | 不相等
需要明确“标签之间用逗号分隔”，并验证程序实际得到的结果。
参考：Anthropic：Classification Evals

## 第 7 页 1.4 可维护的 Prompt 模板

把业务规则写进模板，把本轮数据放进变量
组成 | 分类任务中的写法 | 为什么需要
任务与范围 | 从给定五类中选择所有适用标签 | 避免额外类别或开放式回答
类别定义 | 说明软件故障、硬件故障等边界 | 让规则对歧义输入也有意义
输出约定 | 只输出标签，多个标签用逗号分隔 | 与后续解析程序保持一致
示例 | 展示单标签、多标签和易混淆情况 | 说明仅靠定义难表达的判断
运行时变量 | <complaint>{complaint}</complaint> | 区分待处理数据与固定说明
模板和解析规则一同版本管理；模型支持与实际效果通过评估确认。
参考：Anthropic：Classification Evals；Anthropic：Context Engineering

## 第 8 页 1.5 示例选择与上下文学习

示例用于说明边界，数量增加也会消耗上下文
方法 | 输入中增加什么 | 适用判断
Zero-shot | 说明、定义、输出要求 | 先检查规则是否足够清楚
Few-shot | 若干成对的输入与期望输出 | 补充歧义、格式和边界情况
公开评估项 | 期望标签 | 它区分的边界
打开应用后手机变慢 | Software Bug | 设备变慢不自动等于硬件损坏
应用崩溃且手机发热 | Software Bug + Hardware Malfunction | 单条输入可以同时涉及两类
相似示例反复堆叠未必有用；新增示例应在独立输入上检验收益。
参考：Anthropic：Classification Evals；Anthropic：Context Engineering

## 第 9 页 1.6 上下文中的证据与缺失信息

资料没有电话号码时，模型仍可能补出一个号码
用户提问：I want to speak to someone at Acme on the phone
已提供 AcmeOS 产品资料，但其中没有客服电话。
初版 Prompt 对应的回答
请拨打客服热线 1-800-555-0123 工作日 9:00–18:00（美国东部时间）
最终版 Prompt 对应的回答
资料中没有 Acme 电话支持信息。 建议查阅官方网站或其他官方来源。
需要明确资料不足时的行为，并测试不同问法是否仍遵守约定。
参考：Anthropic：Customer Support

## 第 10 页 1.7 任务分解与中间结果

步骤明确的复杂任务可以拆成多次模型调用
LLM Call：执行一个子任务；Gate：程序检查中间结果，未通过时结束。
适合可明确拆分的固定步骤。 每次调用更聚焦、错误更易定位，但顺序调用会增加延迟和成本，需要通过评估判断是否值得。
参考：Anthropic：Building Effective Agents，Prompt chaining

## 第 11 页 1.8 消息角色与指令边界

角色表达来源和职责，内容分隔帮助解释数据
消息或内容 | 通常放什么 | 应用需要注意
system / developer | 应用级行为规则、任务范围 | 可用角色和优先级取决于模型与接口
user | 当前请求、待处理数据 | 外部文本也可能包含伪装的指令
assistant | 此前模型输出 | 历史回答也可能错误，不能当作事实保证
tool | 工具返回的结果 | 保留调用关联，执行权限由程序控制
把“待分析的文本”标出来有助于理解；工具执行和权限检查仍由应用负责。
参考：OpenAI API：Chat Completions；Wallace et al., 2024

## 第 12 页 1.9 多轮对话中的指代

示例，“How about Emily Doe?” 依赖前面的问题
Huyen 公开文章中的对话（节译）
消息顺序 | 内容
user | John Doe 最近一次在我们这里买东西是什么时候？
assistant | 两周前，买了一顶 Fruity Fedora 帽子。
user | How about Emily Doe?
独立理解最后一句时，缺少“最近一次购买时间”这一查询目标。
参考：Huyen：Building A Generative AI Platform
用户在多轮对话里经常省略已经说过的信息，应用需要让后续调用仍能理解完整的任务。

## 第 13 页 1.10 多轮消息的构造与取舍

每次调用都要明确模型实际能看到哪些信息
messages = [ {"role": "system", "content": RULES}, {"role": "user", "content": question_1}, {"role": "assistant", "content": answer_1}, {"role": "user", "content": question_2}, ... ]
本次输入包含
稳定的规则 必要的前文 当前问题
历史策略 | 收益 | 代价
保留相关轮次 | 保留指代、约束和纠正 | 输入随对话增长
摘要或问题改写 | 压缩历史、形成独立问题 | 可能丢失事实与约束
参考：OpenAI API：Chat Completions；DSPy：History；Huyen：Building A Generative AI Platform

## 第 14 页 1.11 消息最终如何变成模型输入

消息列表经过模型对应的聊天模板和分词器
同一段对话，不同模型使用不同控制标记
模型模板 | Hugging Face 文档中的序列化片段
Mistral instruct | [INST] Hello, how are you? [/INST]
Zephyr | <|user|>\nHello, how are you?</s>
聊天模板标记角色与轮次；Tokenizer 将序列转换成 token ID。 输入长度应按实际模型的模板和分词结果计算。
参考：Transformers：Chat Templates

## 第 15 页 1.12 上下文长度与信息位置

能放进窗口的内容，未必都能被同样有效地使用
怎样读这张图
横轴：相关文档位置 纵轴：问答准确率 任务：20篇文档中找证据
同样提供了正确证据，仅仅改变它的位置，模型利用证据的效果就明显不同。 Lost in the Middle: 历史研究中，相关信息位于中间时表现下降。
图示为论文所测模型与任务，不能直接当作当前所有模型的性能规律。
参考：Liu et al., TACL 2024；Anthropic：Context Engineering

## 第 16 页 1.13 Prompt 的评估与迭代

改进是否有效，要看固定任务上的错误变化
分类 Notebook 的保存结果
初始版本：17 / 20 改进版本：20 / 20
修改同时涉及规则、示例和格式。
记录输入、模板版本、模型配置、原始响应和判分结果，才能定位改动效果。
参考：Anthropic：Classification Evals；Anthropic：Customer Support

## 第 17 页 1.14 组装本次调用的 messages

示例，把分类规则和当前投诉放到各自的消息中
system：固定规则
将投诉归入以下一个或多个类别： Software Bug、Hardware Malfunction、User Error、 Feature Request、Service Outage。 只输出适用类别，多个类别用逗号分隔，不添加解释。
user：当前投诉
The app is crashing and my phone is overheating
这两条消息组成 messages，作为下一节 Client 调用的输入。
参考：Anthropic：Classification Evals；Transformers：Chat Templates；OpenAI API：Chat Completions

## 第 18 页 2.1 Python Client 的职责

应用需要把一次生成接入自己的程序流程
工作 | 应用自己负责 | Client 通常提供
输入 | 构造 messages，选择模型与参数 | 参数接口与请求序列化
通信 | 确定服务地址、凭据与等待策略 | 发出 HTTP 请求，管理连接
返回 | 判断结果是否满足任务 | 解析响应为 Python 对象
异常与资源 | 决定恢复、重试或结束任务 | 异常类型、超时设置、关闭接口
Client 是服务接口的程序封装；模型计算仍发生在推理服务中。
参考：OpenAI Python SDK：Usage / Clients / Errors

## 第 19 页 2.2 一次生成调用

messages 沿用上一节已经准备好的输入
from openai import OpenAI  client = OpenAI(base_url=BASE_URL) result = client.chat.completions.create( model=MODEL_ID, messages=messages, temperature=0.2, max_completion_tokens=128, ) choice = result.choices[0]
连接设置
BASE_URL 指向服务 凭据从环境变量读取
本次生成
模型、消息与生成设置 返回对象包含内容和状态
示例为 Chat Completions 接口结构；参数支持须与具体模型和服务核对。
参考：OpenAI Python SDK：Usage / Clients / Errors；OpenAI API：Chat Completions

## 第 20 页 2.3 Client 的生命周期与等待策略

多次调用可以复用客户端，等待时间需要显式管理
设计选择 | 这样做的理由 | 需要检查的边界
复用 Client | 让底层连接池复用已有连接 | 不在每个请求内反复创建和丢弃
设置超时 | 避免一次网络等待无限拖住任务 | 单次读取超时与任务总期限不同
默认重试 | 部分瞬时错误可以自动恢复 | 可能增加总等待和重复请求
结束时关闭 | 释放连接等资源 | 复用期间不要提前关闭
复用连接可以减少通信开销；模型本身的推理时间不会因此消失。
参考：OpenAI Python SDK：Usage / Clients / Errors；HTTPX Clients & Timeouts

## 第 21 页 2.4 返回对象中的内容、状态与用量

程序应同时读取“生成了什么”和“怎样结束”
result.choices[0].message.content # Software Bug, Hardware Malfunction  result.choices[0].finish_reason # stop  result.usage # 输入、输出及总 token 用量  result._request_id # 定位服务请求
内容
交给业务解析和校验
结束原因
区分正常结束和长度截断
用量与请求标识
支持成本分析和故障追踪
参考：OpenAI Python SDK：Usage / Clients / Errors；OpenAI API：Chat Completions

## 第 22 页 2.5 生成参数在控制什么

输入决定条件，采样参数影响下一 token 的选择
生成阶段 | 主要输入或控制项 | 对应用的影响
读取上下文 | messages、模型与模板 | 决定可用信息和任务条件
计算下一 token 分数 | 当前上下文、已生成 token | 得到词表上各候选的 logits
选择下一 token | temperature、top_p 等采样设置 | 改变输出的随机性与候选范围
继续或终止 | 结束标记、长度上限、停止规则 | 决定输出是否继续增长
参考：Transformers：Sampler；Huyen：AI Engineering，Ch2 Sampling

## 第 23 页 2.6 Temperature 与概率分布

温度缩放分数差异，改变分布的集中程度
pᵢ：候选概率；zᵢ：候选分数；T：温度；Σⱼ：遍历词表求和。
候选分数 z | T = 0.5 | T = 1 | T = 2
2 | 86.50% | 64.39% | 45.51%
1 | 11.71% | 23.69% | 27.60%
0 | 1.58% | 8.71% | 16.74%
−1 | 0.21% | 3.21% | 10.15%
四候选计算示意：低温更集中，高温更平缓；T = 0 通常由实现切换为贪心选择。
参考：Transformers：Sampler；vLLM：Sampling & Reproducibility

## 第 24 页 2.7 Top-p 与候选集合

保留累计概率达到阈值的最小候选集合
按概率降序排列 | 原概率（T = 1） | 累计概率 | top_p = 0.8
候选 A | 64.39% | 64.39% | 保留
候选 B | 23.69% | 88.08% | 保留
候选 C | 8.71% | 96.79% | 移除
候选 D | 3.21% | 100% | 移除
保留 A、B 后重新归一化：73.11%、26.89%。
阈值控制累计概率质量，保留数量会随分布变化；不是固定保留80%的词。
参考：Holtzman et al.：ICLR 2020；Transformers：Sampler

## 第 25 页 2.8 生成设置与任务要求

参数的选择需要对应可观察的收益和代价
任务需求 | 可以调整什么 | 需要验证什么
标签输出保持一致 | 较低随机性、明确格式与长度 | 标签正确率、可解析率、重复运行波动
生成多个候选答案 | 提高随机性或多次独立调用 | 有效候选比例、重复度、额外开销
减少长输出等待 | 约束回答范围、设置输出上限 | 是否截断必要内容，质量是否下降
比较两版 Prompt | 固定模型和支持的生成配置 | 输入分布一致，记录每次原始响应
低温不能修复错误知识；长度上限也不等于“答案会在这里完整结束”。
参考：OpenAI API：Chat Completions；vLLM：Sampling & Reproducibility；Anthropic：Classification Evals

## 第 26 页 2.9 Token 预算与停止条件

输入占用上下文，输出上限约束生成预算
输入 token + 为输出预留的 token ≤ 模型上下文上限
示意：8192 的窗口中，输入占6144，最多剩2048可用于输出预算。
结束方式 | 含义 | 应用接下来做什么
stop | 遇到正常结束或适用的停止规则 | 继续检查内容和任务约定
length | 达到生成长度限制 | 将结果标为可能不完整
tool_calls | 模型生成了工具调用请求 | 交由后续工具处理流程校验
不同模型还有独立输出限制；部分推理模型的输出预算包含不可见的推理 token。
参考：OpenAI API：Chat Completions；Transformers：Chat Templates

## 第 27 页 2.10 调用结果的三个判断层次

HTTP 成功、生成结束和任务完成需要分别判断
判断层次 | 观察什么 | 分类任务的例子
通信与服务 | HTTP状态、连接异常、请求标识 | 服务器返回了有效响应
生成过程 | finish_reason、是否中断、输出预算 | 标签文本没有因长度被截断
应用任务 | 解析成功、标签合法、内容正确 | 得到两个适用标签，且没有额外类别
Client 帮助读取响应，业务正确性需要应用自己验证。
参考：OpenAI Python SDK：Usage / Clients / Errors；OpenAI API：Chat Completions；Anthropic：Classification Evals

## 第 28 页 3.1 Python 调用与 HTTP 请求

Client 将 Python 参数编码为接口约定的请求
Python 中的设置 | HTTP 请求中的位置 | 含义
base_url=BASE_URL | 目标地址与路径前缀 | 向哪个服务发送请求
凭据配置 | Authorization 请求头 | 服务如何识别调用者
chat.completions.create(...) | POST /v1/chat/completions | 请求一次聊天生成
model / messages / temperature | JSON 请求体中的字段 | 模型输入与生成设置
下一页展开这份请求；应用任务和 messages 都保持不变。
参考：OpenAI Python SDK：Usage / Clients / Errors；OpenAI API：Chat Completions

## 第 29 页 3.2 一次请求的报文结构

请求头描述通信属性，请求体承载生成参数
POST /v1/chat/completions HTTP/1.1 Host: model.example Authorization: Bearer <API_KEY> Content-Type: application/json  { "model": "<MODEL_ID>", "messages": [ {"role": "system", "content": "<分类规则>"}, {"role": "user", "content": "<同一条投诉>"} ], "temperature": 0.2 }
请求行
方法与目标资源
请求头
认证信息、内容类型
请求体
已构造的消息和参数
参考：RFC 9110；OpenAI API：Chat Completions

## 第 30 页 3.3 API、REST、HTTP 与 JSON

四个术语描述不同层面的约定
术语 | 它规定什么 | 与这次调用的关系
API | 程序可调用的操作、输入输出和错误 | Chat Completions 的接口契约
REST | 客户端/服务端、无状态、统一接口等架构约束 | 解释资源接口与无状态设计取舍
HTTP | 方法、状态码、头部和表示传输语义 | POST 请求与对应响应
JSON | 对象、数组、字符串等数据编码格式 | 编码 messages 和返回字段
采用 HTTP 和 JSON 的接口，不会自动满足 REST 的全部约束。
参考：RFC 9110；Fielding：REST Architecture；RFC 8259：JSON

## 第 31 页 3.4 HTTP 响应与模型结果

状态码在外层，生成内容与结束原因在响应体
HTTP/1.1 200 OK Content-Type: application/json x-request-id: <REQUEST_ID>  { "choices": [{ "message": { "role": "assistant", "content": "Software Bug, Hardware Malfunction" }, "finish_reason": "stop" }] }
200 OK
这次请求成功返回
content
需要解析和校验的文本
finish_reason
生成的终止原因
参考：RFC 9110；OpenAI API：Chat Completions

## 第 32 页 3.5 无状态请求与有状态应用

无状态接口要求请求提供处理它所需的信息
状态所在位置 | 保存什么
应用的会话存储 | 历史消息、用户约束、工具记录
本次 API 请求 | 选择后的 messages 或受支持的会话引用
HTTP 连接 | 复用通信通道
推理服务缓存 | 可复用的模型计算中间结果
显式携带上下文便于分发和重放请求，代价是重复传输与上下文管理。
参考：Fielding：REST Architecture；OpenAI API：Chat Completions；vLLM：Automatic Prefix Caching

## 第 33 页 3.6 服务端怎样处理这次请求

接口层、调度器和执行引擎承担不同工作
接口层
解析请求、检查参数
调度器
排队，决定何时进入计算
执行引擎
运行模型，生成并返回结果
应用看到的等待包含排队与执行；优化 application Python 代码未必能解决服务端等待。
参考：Orca：OSDI 2022

## 第 34 页 3.7 超时与重试的语义

客户端没有收到响应，不一定代表服务端没有执行
过程 | 客户端看到什么 | 服务端可能发生什么
提交请求 | 请求已发出 | 开始排队或生成
响应未及时到达 | 等待超时 | 仍在运行，或已完成但响应丢失
重新提交 | 发出另一个 POST | 再次执行，产生额外工作
应用总期限要覆盖重试与等待；重试策略需要考虑任务是否允许重复。
POST 不保证幂等；是否支持请求去重，应查具体服务契约。
参考：OpenAI Python SDK：Usage / Clients / Errors；RFC 9110

## 第 35 页 3.8 接口兼容与模型能力

相同的调用方式，仍需核对服务和模型的约定
检查项 | 更换服务时可能变化什么
地址与认证 | base_url、路径前缀、凭据方式
模型输入 | 支持的角色、聊天模板、多模态输入格式
生成控制 | temperature、stop、输出长度字段的支持
返回行为 | 工具调用、流式事件、usage和错误结构
OpenAI-compatible 通常指一组兼容接口；不代表所有端点、参数和语义完全相同。
参考：vLLM：OpenAI-compatible Serving；Transformers：Chat Templates

## 第 36 页 4.1 完整返回与流式返回

stream=True 让应用在完整答案之前接收增量事件
方式 | 响应到达时的形态 | 应用怎样消费
完整返回 | 生成结束后得到一个完整结果对象 | 一次读取content，再解析
流式返回 | 生成过程中持续收到增量事件 | 接收、累积并更新显示，最后确认结束
同一条分类结果的示意
完整文本：Software Bug, Hardware Malfunction 增量片段：“Software”　“ Bug,”　“ Hardware”　“ Malfunction”
参考：OpenAI API：Chat Completions；OpenAI SDK：ChatCompletionChunk

## 第 37 页 4.2 Prefill、Decode 与逐步输出

自回归生成天然存在“先读输入，再逐步生成”的过程
Prefill
处理已有输入上下文 准备后续生成所需状态
Decode
根据前文逐步生成token 结果可以分批交付给客户端
iter 1 读入 “I think this”；后续轮次继续使用新生成的 “is”“great”。
参考：Orca：OSDI 2022；vLLM：Metrics，Intervals 图

## 第 38 页 4.3 一次请求的时间分解

首个输出之前的等待，与后续生成间隔不同
首个 token 之前
请求到达、排队、Prefill 共同影响首个输出前的等待
首个 token 之后
Decode与调度影响输出间隔 网络和界面还会增加交付延迟
原图起点在服务端；客户端计时还包含请求传输等开销。
参考：vLLM：Metrics，Intervals 图

## 第 39 页 4.4 TTFT、TPOT 与总等待

先明确计时边界，再计算和比较指标
指标 | 本页的定义 | 反映什么
TTFT 首token延迟 | 从提交请求到收到第一个输出token | 开始看到输出前等多久
TPOT 平均每输出token时间 | 首个到最后一个token的时长 / (N − 1) | 后续输出平均有多快
到最后一个输出 token 的时长 = TTFT + (N − 1) × TPOT
计算示意： 输出 token 数 N = 51，TTFT = 0.8 s，TPOT = 0.04 s 到最后一个输出 token：0.8 + 50 × 0.04 = 2.8 s
参考：vLLM：Metrics，Intervals 图

## 第 40 页 4.5 SSE 的事件边界

一个 HTTP 响应体可以连续承载多个事件
HTTP/1.1 200 OK Content-Type: text/event-stream  data: {"choices":[{"delta":{"content":"Software"}}]}  data: {"choices":[{"delta":{"content":" Bug,"}}]}  data: {"choices":[{"delta":{"content":" Hardware"}}]}  data: {"choices":[{"delta":{"content":" Malfunction"}}]}  data: {"choices":[{"delta":{},"finish_reason":"stop"}]}  data: [DONE]
响应头只发送一次
data: 后是事件数据 空行结束一个事件
[DONE] 是此API约定 不属于通用SSE标准
协议示意，省略公共字段；网络读取块可以拆开或合并事件，需先恢复事件边界。
参考：WHATWG：Server-sent events；OpenAI SDK：ChatCompletionChunk；OpenAI API：Chat Completions

## 第 41 页 4.6 delta 与结果累积

delta 只描述本次事件新增的部分
事件 | delta.content | 累计得到的文本
1 | Software | Software
2 | Bug, | Software Bug,
3 | Hardware | Software Bug, Hardware
4 | Malfunction | Software Bug, Hardware Malfunction
结束 | 无新增内容，finish_reason=stop | 保留累计文本，记录结束原因
token、SSE事件、网络读取块和屏幕刷新不必一一对应。
参考：OpenAI SDK：ChatCompletionChunk；OpenAI SDK：Streaming helpers

## 第 42 页 4.7 流式消费者的工作

累积文本、更新显示、保存终止状态
text = "" reason = None for event in stream: if not event.choices: continue choice = event.choices[0] text += choice.delta.content or "" render(text) if choice.finish_reason is not None: reason = choice.finish_reason
累积
只追加新增内容 保留片段中的空格
显示
刷新频率可独立于事件到达
完成判断
循环结束后检查 reason
参考：OpenAI Python SDK：Usage / Clients / Errors；OpenAI SDK：ChatCompletionChunk；OpenAI SDK：Streaming helpers

## 第 43 页 4.8 部分结果、完成与可执行结果

收到一些文字，不足以证明一次任务已经完成
当前状态 | 可以显示什么 | 是否交给后续程序执行
持续收到片段 | 标识为生成中的内容 | 暂不执行尚未完成的结构化结果
正常结束 | 累计结果与结束状态 | 解析和校验通过后再使用
达到长度限制 | 明确可能不完整 | 按失败或补救策略处理
网络异常中断 | 可保留部分结果供查看 | 不能把断流当作正常完成
HTTP 200 之后仍可能发生中断；终止事件与业务校验必须保留。
参考：OpenAI SDK：ChatCompletionChunk；OpenAI SDK：Streaming helpers；RFC 9110

## 第 44 页 4.9 缓冲与取消的传播

服务已生成、客户端已接收、用户已看见是三个时刻
位置 | 可能出现什么 | 应用如何定位
推理服务 | 逐步生成，但被调度影响 | 查看服务阶段与输出指标
代理或传输层 | 缓存片段后集中转发 | 检查流式代理配置与到达时间
SDK 与界面 | 解析、合并或降低刷新频率 | 分别记录接收与显示时间
用户取消后 | 本地停止显示，但上游仍可能运行 | 关闭流，并检查取消是否传到服务
停止界面刷新不会自动释放服务器上的生成任务。
参考：NGINX：proxy_buffering；vLLM：AsyncLLM cancellation；vLLM：Metrics，Intervals 图

## 第 45 页 4.10 Streaming、Async 与并发

它们分别控制交付、等待和同时在途的工作
概念 | 解决的问题 | 不会自动带来什么
Streaming | 完整答案之前交付部分结果 | 模型计算量下降
Async / await | 等待I/O时允许程序处理其他工作 | 同一请求的模型运算自动更快
并发请求 | 同时保持多个请求在途 | 吞吐随并发数量无限增长
并发过高会增加排队和资源争用；依赖上一轮结果的调用仍需等待必要结果。
参考：Python：Coroutines and tasks；OpenAI Python SDK：Usage / Clients / Errors；vLLM：Metrics，Intervals 图

## 第 46 页 4.11 延迟优化的目标与取舍

吞吐、首token等待和后续输出速度需要一起观察
曲线与坐标
蓝线：Decode批次混入一次Prefill 橙线：仅Decode 横轴：批次大小 纵轴：执行延迟（ms）
左图：输入长度 128 右图：输入长度 1024 混合批次的执行延迟更高。
图示为论文实验；应用应结合实际负载观察首输出等待和后续速率。
参考：DistServe：OSDI 2024；vLLM：Metrics，Intervals 图

## 第 47 页 4.12 对后续 Agent 系统的支撑

一次调用的输入、状态和观测会进入更长的执行流程
本讲已建立的概念 | 后续系统中的用途
messages、历史与证据 | Agent Loop组织状态；Memory和RAG补充上下文
内容与结束状态分开 | 工具调用前检查结果完整性和参数
请求标识、用量与时间边界 | Trace定位失败；评估质量、延迟和成本
连接、排队与并发 | Serving分析容量和吞吐，控制资源使用
先把一次调用的边界讲清楚，才能解释多步执行为什么成功、失败或变慢。
参考：Huyen：Building A Generative AI Platform

## 第 48 页 本讲回顾

按一次请求的过程，检查四个环节
环节 | 本讲形成的认识
Prompt | 明确任务和结果约定，选择必要证据与历史
Python Client | 控制一次生成，管理连接和等待，读取内容与状态
REST/API | 区分接口契约、通信语义和数据编码
Streaming | 累积增量结果，确认完成，分解端到端等待
下一次课：Structured Output、JSON Schema、异常处理与结果解析

## 第 49 页 课外参考资料

优先阅读的四组资料
Chip Huyen · AI Engineering
第2、5、9、10章：生成控制、Prompt、推理优化与应用架构
Anthropic · Courses
Classification Evals 与 Customer Support：输入输出约定和评估迭代
OpenAI · Python SDK 与 API Reference
Client配置、请求响应、生成字段和流式事件
vLLM · Metrics 与 Serving 文档
请求阶段、TTFT/TPOT、服务接口与性能观察
