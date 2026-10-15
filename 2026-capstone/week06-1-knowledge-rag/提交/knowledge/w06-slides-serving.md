# 第六周第 2 次课课件：DGX Spark 本地部署与 vLLM

原始文件：`dgx-local-serving.pptx`

## 第 1 页 DGX Spark 本地部署与 vLLM

平台连接、模型内存分析与 OpenAI 兼容推理服务 2026 年 10 月

## 第 2 页 目录

第 6 周第 2 次课：From API Agent to Private Agent（DGX Spark 环境与本地模型部署）。
平台登录与开发环境
校园网连接、SSH 密钥、VS Code 远程开发、文件传输与 tmux
硬件架构与模型内存
GB10 统一内存、生成带宽上限、vLLM 环境与 KV Cache 估算
vLLM 服务部署与调用
服务启动参数、启动日志解读、OpenAI 兼容接口与流式测速
关键参数实验与规范
上下文上限、内存占比、思考与工具调用、并发吞吐与使用规范

## 第 3 页 1.1 课程实验平台与账号体系

7 个课程小组共用一台 NVIDIA DGX Spark，按组分配独立 Linux 账号
同组成员共用账号与家目录；请勿修改其他组密码，建议在家目录下按成员建立子目录。
平台连接信息
项目 | 配置与说明
主机地址 | 10.134.43.123，SSH 端口 2222
账号名称 | group1 ～ group7（与课程分组号一致）
硬件配置 | NVIDIA GB10，128 GB 统一内存，20 核 ARM，4 TB SSD
系统软件 | Ubuntu 24.04（aarch64），Driver 580，CUDA 13.0
网络要求 | 北航校园网直连；校外需先连接学校 VPN
权限与目录边界
普通用户权限 可直接调用 GPU；无 sudo 与 docker 权限，需要系统软件包时联系课程组。 各组目录隔离 家目录权限为 750（/home/groupN），不同小组之间不可互访。 共享模型目录 /srv/spark/models 对所有组只读开放，无需重复下载权重。

## 第 4 页 1.2 终端首次登录与主机指纹核对

使用 SSH 指定 2222 端口连接，首次连接需核对 ED25519 主机指纹
若提示指纹不一致，最常见原因是漏写 -p 2222 连到了默认 22 端口上的其他设备。
① 指定端口 2222
ssh 的端口参数为小写 -p；scp 的端口参数为大写 -P。
② 核对主机指纹
确认指纹为 SHA256:tU2OdrKz... 后输入 yes，再输入课程组发放的密码。
③ 免密与多人协作
组内每位成员可将各自电脑的公钥追加到 ~/.ssh/authorized_keys，互不影响。

## 第 5 页 1.3 SSH 密钥、连接别名与远程开发

在本机配置密钥与 Host spark 别名后，终端与 VS Code / Cursor 均可直接连接
配置完成后，终端直接执行 ssh spark 即可登录，无需每次输入端口、用户名与密码。
Windows PowerShell 上传公钥
Windows 无 ssh-copy-id，可在 PowerShell 执行： type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh -p 2222 group3@10.134.43.123 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
VS Code / Cursor 远程开发
1. 安装 Remote - SSH 扩展（Cursor 自带）。 2. 按 F1 选择 Remote-SSH: Connect to Host，选择 spark（Linux）。 3. 连接后打开本组在 Spark 上的工作目录，终端与 Python 均在远端运行。

## 第 6 页 1.4 文件传输、网络限制与会话管理

通过 scp 上传实验代码；模型服务等长任务需放入 tmux 会话以防断联终止
校园网环境无法直连 GitHub 与 Hugging Face：代码在本机克隆后上传，模型使用共享目录或 ModelScope。

## 第 7 页 2.1 DGX Spark 硬件架构与内存特征

CPU 与 GPU 共用 128 GB 统一内存；自回归 Decode 阶段受内存带宽约束
Decode 阶段每生成 1 个 token 都需读取一次模型权重：单流理论上限 ≈ 内存带宽 273 GB/s ÷ 权重大小。
统一内存观测方式
nvidia-smi 中显存显示为 Not Supported；整机可用内存以 free -h 的 available 列为准（当前空闲 119 GiB）。
模型规模与单流生成速度上限
Qwen3-1.7B（约 3.5 GB）理论上限约 78 tok/s，实测约 50 tok/s；Qwen3-8B（约 16 GB）理论上限约 17 tok/s。

## 第 8 页 2.2 Python 虚拟环境与 vLLM 安装

在组账号下建立独立虚拟环境，使用 uv 与国内镜像安装 CUDA 13 版 vLLM
北外镜像在校园网内实测约 35 MB/s，安装耗时约 1 分钟；若镜像波动可切换为华为云镜像。
预置共享模型目录（/srv/spark/models，只读）
模型名称 | 本地路径 | 权重大小 | 课堂与课后使用建议
Qwen3-1.7B | /srv/spark/models/Qwen3-1.7B | 3.8 GB | 课堂实验统一使用，7 组可同时运行
Qwen3-8B | /srv/spark/models/Qwen3-8B | 16 GB | 单个服务需约 24 GiB，课后错峰实验使用
Qwen3.8-27B-FP8 | /srv/spark/models/hub/models--Qwen--Qwen3.8-27B-FP8/... | 29 GB | 体积较大，供课程项目按需调用

## 第 9 页 2.3 模型结构参数与 KV Cache 估算

根据 config.json 计算模型权重与单 token KV Cache 占用，理解上下文容量限制
单 token KV Cache = 2 (K/V) × 层数 28 × KV 头数 8 × 头维度 128 × 2 字节 = 112 KiB。
内存组成分析
1. 模型权重（3.20 GiB） Qwen3-1.7B 启用 tie_word_embeddings，词嵌入与输出层共享 0.58 GiB，实际加载 3.20 GiB。 2. GQA 降低 KV Cache 16 个注意力查询头共享 8 个 KV 头，KV Cache 体积减半。 3. 上下文长度与内存预算 默认最大长度 40960 需 4.38 GiB KV Cache；在受限内存预算下必须显式下调 --max-model-len。

## 第 10 页 3.1 启动本地 vLLM 服务与核心参数

在终端 1 启动 OpenAI 兼容服务，显式设置端口、内存占比与最大上下文长度
首次启动需执行 torch.compile 与 CUDA Graph 捕获（约 3 分钟）；缓存生成后再次启动约 1 分钟。
启动参数 | 课堂推荐配置 | 参数作用与设置原因
位置参数（模型路径） | /srv/spark/models/Qwen3-1.7B | 指定本地模型目录；若填模型 ID 会尝试连接 Hugging Face 下载
--served-model-name | qwen3-1.7b | 客户端请求中 model 字段使用的名称，避免暴露冗长的本地路径
--host / --port | 127.0.0.1 / 8100 + 组号 | 仅监听本机回环地址；按组号分配端口避免多组冲突
--gpu-memory-utilization | 0.08（约 9.74 GiB） | 限制单服务内存上限（默认 0.9 会占用 110 GiB），保证 7 组可同时运行
--max-model-len | 8192 | 限制单请求最大上下文长度（输入 + 输出），使 KV Cache 能放入内存预算

## 第 11 页 3.2 启动日志解读：内存去向与容量

从 EngineCore 日志核对权重占用、KV Cache 可用空间以及最大并发倍数
3.47 GiB KV Cache ÷ 112 KiB/token ≈ 32,528 tokens；按 8192 长度计算可同时容纳约 3.97 个满长请求。
① 固定开销与激活峰值
权重 3.22 GiB（与估算 3.20 GiB 吻合），加上 CUDA 运行时与激活峰值后剩余空间全部划归 KV Cache。
② 编译与图捕获缓存
torch.compile 与 CUDA Graph 缓存保存在 ~/.cache/vllm，二次启动时编译仅需 0.12 s。
③ 服务就绪标志
出现 Application startup complete 后，服务开始在 127.0.0.1:$PORT 接收 HTTP 请求。

## 第 12 页 3.3 服务调用：cURL 与 OpenAI SDK

vLLM 提供标准 OpenAI 兼容接口，现有 Agent 代码只需将 base_url 指向本地端口
Qwen3 默认开启思考模式；不需要思考过程时，通过 extra_body 传入 enable_thinking=False。
Python 客户端调用方式
from openai import OpenAI client = OpenAI(base_url="http://127.0.0.1:8103/v1", api_key="EMPTY") resp = client.chat.completions.create( model="qwen3-1.7b", messages=[{"role": "user", "content": "..."}], extra_body={"chat_template_kwargs": {"enable_thinking": False}}, )
与第 3～6 周 Agent 代码衔接
• 接口协议完全一致：/v1/models 与 /v1/chat/completions。 • 未设置 --api-key 时，客户端 api_key 填任意非空字符串即可。 • 第 7 周迁移 Agent 时无需改动业务循环，仅替换连接参数。

## 第 13 页 3.4 流式输出与推理性能实测

运行 chat_demo.py 测量首 token 延迟（TTFT）与 Decode 生成速度
单请求实测 TTFT 为 48 ms，生成速度 50.2 token/s（对应 TPOT 约 19.9 ms/token）。
TTFT（Time To First Token）
从发送请求到收到首个输出 token 的耗时，主要反映 Prefill 阶段处理输入序列的计算与排队开销。
生成速度与 TPOT（Time Per Output Token）
首个 token 之后每秒生成的 token 数（50.2 tok/s），倒数即为每步 Decode 耗时（约 20 ms），受内存带宽限制。

## 第 14 页 3.5 思考模式与 max_tokens 预算

开启思考模式时，<think> 推理链同样计入 completion_tokens 上限
若开启思考模式，需相应调大 max_tokens（如 1024 以上），否则模型会在给出最终结论前被截断。
现象分析
当 max_tokens=256 时，256 个生成 token 全部消耗在 <think> 块内，输出在「总结一下，9.9」处截断。
服务端分离思考字段
启动服务时加入 --reasoning-parser qwen3，可将思考内容拆入 message.reasoning，正文仅保留最终回答。

## 第 15 页 4.1 参数实验：上下文上限与内存占比

对比 --max-model-len 与 --gpu-memory-utilization 对 KV Cache 容量的直接影响
模型权重固定不变，调大 --gpu-memory-utilization 增加的内存预算几乎全部转化为 KV Cache 容量。
实验 2：调整 --gpu-memory-utilization 实测对比（--max-model-len 8192）
--gpu-memory-utilization | 总内存预算 | 模型权重 | 可用 KV Cache | 可缓存 Token 总数 | 8192 长度最大并发
0.08（课堂默认） | 9.74 GiB | 3.22 GiB | 2.85 ～ 3.47 GiB | 26,704 ～ 32,528 | 3.26x ～ 3.97x
0.12（对比实验） | 14.60 GiB | 3.22 GiB | 8.64 GiB | 80,864 | 9.87x

## 第 16 页 4.2 编译开关、工具调用与并发吞吐

验证 --enforce-eager、Tool Calling 解析器，以及多请求 Batching 的吞吐提升
4 并发时总生成吞吐达 222.8 tok/s（单请求的 4.5 倍），单请求 TPOT 仍保持约 17～20 ms
实验 3：--enforce-eager（跳过编译与 CUDA Graph）
运行模式 | 启动耗时 | 单流生成速度
默认（编译 + CUDA Graph） | 首次 ~190 s / 缓存 ~56 s | 50.2 token/s
--enforce-eager | ~49 s | 48.4 token/s
实验 5：vllm bench serve 并发吞吐对比（512 输入 / 128 输出）
最大并发数 | 总输出吞吐 | 平均 TTFT | 平均 TPOT
1 | 49.6 token/s | 43.3 ms | 20.0 ms
4 | 222.8 token/s | 106.4 ms | 17.2 ms

## 第 17 页 课程实验规范与常见问题排查

多人共享统一内存设备，请严格遵守端口、内存占比与进程清理规范
完整命令、脚本说明与故障排查清单见仓库 2026-capstone/week06-2-dgx-local-serving/README.md。
端口与监听范围
使用 8100 + 组号（如 group3 用 8103），设置 --host 127.0.0.1；每组同时只运行一个 vLLM 服务。
内存预算控制
课堂实验保持 --gpu-memory-utilization 0.08 与 --max-model-len 8192；切勿使用默认值 0.9。
常见启动报错
Address already in use：端口冲突或旧服务未关；Free memory is less than desired：调小内存占比。
实验结束清理
在服务终端按 Ctrl+C 停止进程，并用 free -h 与 ps -u $USER 确认内存和后台进程已释放。
