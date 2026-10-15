# 第一周课件：LLM 推理

原始文件：`llm-inference-tutorial.pptx`

## 第 1 页 LLM Inference 入门

Qwen3-8B Transformers 代码与张量观察 2026 年秋季
一次 Prefill 与逐 Token Decode

## 第 2 页 教程目标与实验范围

理解模型如何根据已有 token 预测下一个 token 对应结构、代码与张量：hidden states、Q/K/V、RoPE、KV cache 手写一次 prefill 和逐 token decode，观察 cache 增长 单条输入、无 padding、BF16、greedy decoding Qwen3-8B dense，关闭 thinking，使用 eager attention
内容参考自：Qwen3-8B 官方模型说明 https://huggingface.co/Qwen/Qwen3-8B

## 第 3 页 1.1 自回归生成的循环

每次选出一个 token，把它接到已有文本后继续预测
内容参考自：Hugging Face / KV Cache from scratch in nanoVLM https://huggingface.co/blog/kv-cache
图示文本的逻辑增长；使用 cache 时，decode 实际只输入最新 token

## 第 4 页 1.1 自回归生成

本例一次 forward 为每个输入位置产生词表 logits 生成时读取最后一个位置，选出一个 token，再把它送回模型
内容参考自：Hugging Face / Caching https://huggingface.co/docs/transformers/v4.51.3/cache_explanation
阶段 | 本次输入 | 已有 KV | 本次预测
Prefill | 完整 prompt：x₀ … xₛ₋₁ | 空 | y₁
Decode 1 | y₁ | prompt 的 KV | y₂
Decode 2 | y₂ | prompt + y₁ 的 KV | y₃
第一个生成 token 来自 prefill 的结果

## 第 5 页 1.2 Transformer 与 Decoder-only

原论文包含 Encoder 和 Decoder Qwen3 使用 Decoder-only 没有 Encoder 与 cross-attention 保留 causal self-attention 与 MLP Qwen3：RMSNorm、RoPE、GQA
内容参考自：Vaswani et al. / Attention Is All You Need，Fig. 1 https://arxiv.org/abs/1706.03762

## 第 6 页 1.2 Qwen3-8B 整体结构

Decoder-only Transformer：36 层相同结构、不同权重的 block token ID 经 embedding 得到向量，LM head 产生词表中各位置的分数
内容参考自：Qwen3-8B config.json https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/config.json
Token Embedding
Decoder block × 36
Final RMSNorm
LM head Linear
[B, S, 4096]
[B, S, 151936]
input_ids [B, S]
logits 词表分数

## 第 7 页 1.3 模型配置的含义

内容参考自：Qwen3-8B config.json https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/config.json
配置 | 数值 | 模型中的含义
num_hidden_layers | 36 | 串联的 Transformer decoder block 数量
hidden_size | 4096 | 每个 token 的隐藏表示维度
num_attention_heads | 32 | 每层 attention 的 Q head 数量
head_dim | 128 | 每个 Q/K/V head 的向量维度
num_key_value_heads | 8 | 每层 K head 和 V head 各有 8 个
intermediate_size | 12288 | MLP 两个上投影分支的输出维度
vocab_size | 151936 | 模型词表维度，即 logits 的类别数
记号：B = batch size；S = 本轮输入长度；T = 本轮开始时的 cache 长度 + S

## 第 8 页 1.4 Decoder block 与残差连接

一个 block 包含 Attention 与 FFN Attention 聚合不同位置的信息 FFN 逐位置变换特征 两条残差路径分别绕过一个子层 Qwen3-8B 对应图 (b) 归一化位于各子层之前 Norm 用 RMSNorm，FFN 用 SwiGLU
内容参考自：Xiong et al. / On Layer Normalization，Fig. 1 https://proceedings.mlr.press/v119/xiong20b.html

## 第 9 页 2.1 模型加载

固定 Transformers 4.51.3，显式选择 eager attention
内容参考自：Qwen3-8B 官方模型说明 https://huggingface.co/Qwen/Qwen3-8B
import torch from transformers import AutoTokenizer, AutoModelForCausalLM  model_path = "Qwen/Qwen3-8B"  # or a local checkpoint directory tokenizer = AutoTokenizer.from_pretrained(model_path) model = AutoModelForCausalLM.from_pretrained( model_path, torch_dtype=torch.bfloat16, attn_implementation="eager", device_map="cuda:0", ).eval()
实测：NVIDIA L20X；PyTorch 2.7.1+cu126；CUDA 12.6

## 第 10 页 2.2 Chat template 与 Tokenizer

聊天消息先组织成文本，再转换为整数 token ID
内容参考自：Qwen3-8B 官方模型说明 https://huggingface.co/Qwen/Qwen3-8B
messages = [{"role": "user", "content": "中国的首都是哪里？请用一句话回答。"}] text = tokenizer.apply_chat_template( messages, tokenize=False, add_generation_prompt=True, enable_thinking=False, ) inputs = tokenizer(text, return_tensors="pt", add_special_tokens=False).to(model.device)
inputs 包含 input_ids 和 attention_mask；本例没有 padding

## 第 11 页 2.2 实际输入的 Token

本次 prompt 共 22 个 token，包含聊天与 thinking 标记
内容参考自：Qwen3-8B Tokenizer https://huggingface.co/Qwen/Qwen3-8B
位置 | token ID | 单 token 解码内容
0 | 151644 | '<|im_start|>'
1 | 872 | 'user'
3 | 105538 | '中国的'
4 | 59975 | '首'
5 | 100132 | '都是'
6 | 101314 | '哪里'
18 | 151667 | '<think>'
20 | 151668 | '</think>'
21 | 271 | '\n\n'
表中为节选；input_ids [1,22]，int64；attention_mask 全部为 1

## 第 12 页 2.3 Embedding 查表的含义

每个 token ID 对应权重矩阵的一行 每一行是一个连续向量 Qwen3-8B 的查表矩阵： 151936 行，对应词表 4096 列，对应 hidden size
行列索引从 0 开始；高亮行取自本次真实 embedding，省略号代表未展示的行列
Qwen3-8B Embedding
151936 行 × 4096 列
ID | 0 | 1 | … | 4095
⋮ | ⋮ | ⋮ | ⋱ | ⋮
105538 | -0.033 | -0.014 | … | 0.018
输入 105538（“中国的”） 取出高亮行，得到 4096 维向量
内容参考自：Qwen3-8B config.json；本次 embedding 实测 https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/config.json

## 第 13 页 2.3 Embedding 与 Hidden states

Embedding 查表得到初始 hidden states，每个 token 为 4096 维
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
ids = inputs.input_ids                 # [B, S] h = model.model.embed_tokens(ids)      # [B, S, 4096] print(model.model.embed_tokens.weight.shape) print(h[0, -1, :4])
对象 | 实际 shape / 数值
embedding.weight | [151936, 4096]
h | [1, 22, 4096] · bfloat16
h[0, -1, :4] | 0.0269, 0.0096, -0.0079, 0.0044

## 第 14 页 2.4 RMSNorm

先按均方根归一化，再乘可学习的逐维缩放权重 w
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
norm = model.model.layers[0].input_layernorm w = norm.weight                         # [4096] xf = h.float() xf = xf * torch.rsqrt(xf.square().mean(-1, keepdim=True) + 1e-6) normalized = w * xf.to(h.dtype)         # [B,S,4096]  torch.testing.assert_close(normalized, norm(h))
RMSNorm 使用可学习的缩放权重 w；每个 token 独立计算平方均值

## 第 15 页 2.5 Query、Key 与 Value

用 Q 与各个 K 匹配，得到权重，再对对应的 V 做加权汇总
内容参考自：Jay Alammar / The Illustrated GPT-2 https://jalammar.github.io/illustrated-gpt2/
Q 决定怎么查，K 决定怎么匹配，V 提供被汇总的内容

## 第 16 页 2.5 三组权重产生 Q、K、V

同一个 X 分别乘三组权重 各权重通过训练学习 Qwen3-8B 的 Q 总宽度为 4096 K/V 总宽度各为 1024 随后分成 32 / 8 / 8 个 head
内容参考自：Jay Alammar / The Illustrated Transformer https://jalammar.github.io/illustrated-transformer/

## 第 17 页 2.5 Q、K、V 投影与分头

Q/K/V 来自同一个归一化输入，使用三个独立线性层
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
a = model.model.layers[0].self_attn x = model.model.layers[0].input_layernorm(h) B, S, _ = x.shape q = a.q_proj(x).view(B, S, 32, 128) k = a.k_proj(x).view(B, S,  8, 128) v = a.v_proj(x).view(B, S,  8, 128) q = a.q_norm(q).transpose(1, 2)  # [B, 32, S, 128] k = a.k_norm(k).transpose(1, 2)  # [B,  8, S, 128] v = v.transpose(1, 2)           # [B,  8, S, 128]
q_norm/k_norm 沿每个 head 的 128 维计算；block 的 RMSNorm 沿 4096 维计算

## 第 18 页 2.5 Q、K、V 的实际内容

固定观察首层、head 0、最后一个输入 token 的前 4 个维度
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
张量 | 索引 | 数值
Q（RoPE 前） | [0, 0, -1, :4] | -0.1074, 0.1670, 0.0864, 0.2354
K（RoPE 前） | [0, 0, -1, :4] | -5.0625, 0.3711, 3.4531, 1.5312
V | [0, 0, -1, :4] | -0.0005, 0.0024, -0.0123, -0.0256
Q：当前查询　　K：匹配特征　　V：聚合的内容向量

## 第 19 页 2.6 Grouped-Query Attention

Qwen3-8B 使用 32 个 Q head、8 个 KV head 同一组的 4 个 Q head 共享 K/V，各自计算 attention
内容参考自：Ainslie et al. / GQA，Fig. 2 https://aclanthology.org/2023.emnlp-main.298/
原图为通用示意；本例每组 4 个 Q head，cache 始终保留 8 个 KV head

## 第 20 页 2.7 Rotary Position Embedding

RoPE 按 token 的位置旋转 Q/K，让 attention 感知位置关系 每个二维子空间使用不同旋转频率；V 保持不变
内容参考自：Su et al. / RoFormer，Fig. 1 https://arxiv.org/abs/2104.09864
图中的 mθ₁ 是第一对坐标的旋转角；后文用 α 表示角度、ω 表示角频率

## 第 21 页 2.7 二维旋转的坐标公式

固定一个 token、一个 head：每对坐标在二维平面内旋转 图中的旋转角是新增角度；原向量本身已有方向
内容参考自：Su et al. / RoFormer https://arxiv.org/abs/2104.09864
r 是模长，β 是原方向角，α 是本次旋转角
旋转后：和角公式展开为 cos / sin 的乘加
Qwen3-8B：a 对应通道 i，b 对应通道 i+64；Q 与 K 分别使用同一旋转规则

## 第 22 页 2.7 旋转角度与 cos / sin

角度由位置 m 和通道对编号 i 决定，单位为弧度
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
m：token 的位置；i = 0 … 63；d = 128；θ = rope_theta = 1,000,000
inv_freq = 1.0 / (1_000_000 ** (torch.arange(0, 128, 2, device=h.device).float() / 128))                 # [64] pos = torch.arange(S, device=h.device)[None]       # prefill freqs = pos.float()[..., None] * inv_freq           # [B,S,64] emb = torch.cat((freqs, freqs), dim=-1)             # [B,S,128] cos = emb.cos().to(h.dtype) sin = emb.sin().to(h.dtype)
cat 重复的是同一组 64 个角度，使通道 i 与 i+64 取到相同的 cos / sin

## 第 23 页 2.7 rotate_half 与旋转公式

rotate_half 将每对坐标 (a, b) 变成 (−b, a)，提供公式中的交叉项
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
past_len = 0  # prefill; decode: cache length BEFORE this call pos = torch.arange(past_len, past_len + S, device=h.device)[None] cos, sin = model.model.rotary_emb(h, pos)          # [B,S,128] cos, sin = cos[:, None], sin[:, None]              # [B,1,S,128] def rotate_half(x): x1, x2 = x[..., :64], x[..., 64:] return torch.cat((-x2, x1), dim=-1)  q_rot = q * cos + rotate_half(q) * sin k_rot = k * cos + rotate_half(k) * sin
Prefill 的位置为 0 … 21；第一次 decode 使用位置 22，不会重新从 0 开始

## 第 24 页 2.8 Attention 的加权汇总

一个 Q 与每个 K 做点积 缩放后用 softmax 得到权重 将权重乘对应的 V，再相加 示例：0.88 V₁ + 0.12 V₂ 原图尚未加入 causal mask Qwen3-8B 将分数除以 √128
内容参考自：Jay Alammar / The Illustrated Transformer https://jalammar.github.io/illustrated-transformer/

## 第 25 页 2.8 Scaled Dot-Product Attention

拼接各 head 的 attention 输出，再用 o_proj 混合不同 head 的特征
内容参考自：Vaswani et al. / Attention Is All You Need，Fig. 2 https://arxiv.org/abs/1706.03762

## 第 26 页 2.8 Causal Mask 的可见范围

在 softmax 前屏蔽未来位置，softmax 沿 key 维逐行计算
内容参考自：Hugging Face / Continuous batching from first principles https://huggingface.co/blog/continuous_batching
代码用极小负数屏蔽未来位置，使其 softmax 权重为 0；不是将分数乘 0

## 第 27 页 2.8 Causal mask 与注意力权重

Prefill 中，每个位置只能读取自己和之前位置的 K/V
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py

## 第 28 页 2.8 Eager attention

首层 prefill：计算 QK 分数、屏蔽未来位置，再对 V 加权求和
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
from transformers.models.qwen3.modeling_qwen3 import repeat_kv K = repeat_kv(k_rot, 4)            # [B,32,S,128] V = repeat_kv(v, 4)                # [B,32,S,128] scores = (q_rot @ K.transpose(-2, -1)) * a.scaling future = torch.ones(S, S, device=h.device, dtype=torch.bool).triu(1) scores = scores.masked_fill(future, torch.finfo(q_rot.dtype).min) probs = scores.softmax(-1, dtype=torch.float32).to(q_rot.dtype) z = probs @ V                      # [B,32,S,128] z = z.transpose(1, 2).reshape(B, S, 4096) attention_out = a.o_proj(z)         # [B,S,4096]
本页 T = S；decode 中 K/V 还包含 cache 的历史部分，Q 只含当前输入

## 第 29 页 2.9 SwiGLU MLP 模块结构

同一输入 x 分成两条投影分支 W：gate_proj，4096→12288 V：up_proj，4096→12288 gate 经 SiLU 后，与 up 逐元素相乘 两路均为 [B,S,12288] W₂：down_proj，12288→4096
内容参考自：Sebastian Raschka / Fig. 6，右下模块子图 https://magazine.sebastianraschka.com/p/from-gpt-2-to-gpt-oss-analyzing-the
原图由下向上读；Qwen3 选择 Swish / SiLU，圆圈中的 × 表示逐元素相乘

## 第 30 页 2.9 SwiGLU 的门控原理

SiLU 对 gate 投影逐元素激活 z 为 gate 投影，v 为 up 投影 门控值随当前 token 的输入变化 可以为负，也可以大于 1 与 up 分支逐通道相乘 j 为通道编号，乘后再做 down_proj
内容参考自：Sebastian Raschka / Fig. 5，激活函数曲线子图 https://magazine.sebastianraschka.com/p/from-gpt-2-to-gpt-oss-analyzing-the
绿色点线为 SiLU / Swish；SiLU 是激活函数，SwiGLU 还包含两分支的门控相乘

## 第 31 页 2.9 SwiGLU MLP

两个分支映射到 12288 维，相乘后投影回 4096 维
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
mlp = model.model.layers[0].mlp u = h + attention_out x = model.model.layers[0].post_attention_layernorm(u) gate = torch.nn.functional.silu(mlp.gate_proj(x))  # [B,S,12288] up = mlp.up_proj(x)                              # [B,S,12288] mlp_out = mlp.down_proj(gate * up)                # [B,S,4096] h1 = u + mlp_out                                # block output
实测对象 | shape | 最后一个 token 的前 4 维
gate_proj 输出 | [1,22,12288] | 0.0527, -0.0535, -0.1357, 0.1230
MLP 输出 | [1,22,4096] | 0.0178, -0.0369, 0.0270, -0.0417
gate_proj 行展示 SiLU 之前的线性投影值；完整张量保存在 tensors.pt

## 第 32 页 2.10 Hidden states 的读取

模型有 36 个 block，此接口记录 37 个状态张量
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
with torch.inference_mode(): out = model(**inputs, use_cache=False, output_hidden_states=True)
API 索引 | 含义 | 实测 shape
out.hidden_states[0] | Embedding 输出 | [1,22,4096]
out.hidden_states[1] | 第 0 个 block 输出 | [1,22,4096]
out.hidden_states[-1] | 末层输出经 Final RMSNorm | [1,22,4096]
最后状态的切片 [0, -1, :4]
1.1719, 0.3906, -0.2539, -0.8672

## 第 33 页 2.10 LM head 与下一个 Token

LM head 产生词表分数；greedy decoding 取最大分数的 ID
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
with torch.inference_mode(): logits = model.lm_head(out.hidden_states[-1])  # [1,S,151936] next_id = logits[:, -1:].argmax(-1)                # [1,1]
候选 ID | Token 文本 | Logit | Softmax 概率
105538 | '中国的' | 49.500 | 99.95335%
58695 | '中国' | 41.750 | 0.04305%
68990 | '北京' | 39.000 | 0.00275%
105492 | '中华人民' | 37.250 | 0.00048%
104554 | '北京市' | 37.000 | 0.00037%
上表为 prefill 最后一个位置的真实 top-5 候选

## 第 34 页 3.1 完整前缀重算的计算范围

把完整前缀送回模型，会重复计算历史位置的 Q/K/V 与中间状态
内容参考自：Hugging Face / Continuous batching from first principles https://huggingface.co/blog/continuous_batching

## 第 35 页 3.2 一次 Prefill

完整 prompt 输入一次，建立各层 KV cache，并预测第一个 token
内容参考自：Hugging Face / Caching https://huggingface.co/docs/transformers/v4.51.3/cache_explanation
from transformers import DynamicCache cache = DynamicCache() ids, mask = inputs.input_ids, inputs.attention_mask position = torch.arange(ids.shape[1], device=ids.device) with torch.inference_mode(): out = model(input_ids=ids, attention_mask=mask, position_ids=position[None, :], cache_position=position, past_key_values=cache, use_cache=True) next_id = out.logits[:, -1:].argmax(-1)

## 第 36 页 3.2 Prefill 张量形状总览

内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
对象 | Prefill shape | 维度含义
input_ids | [1, 22] | batch × 输入 token
hidden state | [1, 22, 4096] | batch × token × hidden
Q | [1, 32, 22, 128] | B × Q head × S × D
每层 K / V cache | [1, 8, 22, 128] | B × KV head × T × D
attention probabilities | [1, 32, 22, 22] | batch × Q head × query × key
logits | [1, 22, 151936] | batch × token × 词表
next_id | [1, 1] | 一个尚未写入 cache 的新 token

## 第 37 页 3.3 一步 Decode

输入上轮选出的 token，mask 覆盖历史和当前输入，cache 复用历史 K/V
内容参考自：Hugging Face / Caching https://huggingface.co/docs/transformers/v4.51.3/cache_explanation
# Stop first if next_id is EOS; otherwise consume it. mask = torch.cat((mask, mask.new_ones((1, 1))), dim=-1) position = position[-1:] + 1 with torch.inference_mode(): out = model(input_ids=next_id, attention_mask=mask, position_ids=position[None, :], cache_position=position, past_key_values=cache, use_cache=True) next_id = out.logits[:, -1:].argmax(-1)
第一次 decode：input_ids [1,1]；mask [1,23]；position = [22]

## 第 38 页 3.4 KV Cache 保留历史计算

Attention 中，蓝色 K/V 复用，白色 K/V 与当前 Q 为本轮新算 新 Q 仍要读取全部历史 K/V 当前 token 仍需经过全部 36 个 block
内容参考自：Hugging Face / Continuous batching from first principles https://huggingface.co/blog/continuous_batching

## 第 39 页 3.4 KV Cache 的内容与追加

每层保存 RoPE 后的 K 与 投影后的 V，沿序列维追加 历史 token 的 Q 不需要缓存，历史 K 也不需要再次旋转
内容参考自：Hugging Face / Caching https://huggingface.co/docs/transformers/v4.51.3/cache_explanation
K cache
历史 22 个位置的 K
新 K
T = 23
V cache
历史 22 个位置的 V
新 V
每层 K、V 各自：[1, 8, 22, 128]  变为  [1, 8, 23, 128]

## 第 40 页 3.4 Prefill 与 Decode 的形状对比

内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
对象 | Prefill | 第一次 Decode
输入 token | [1,22] | [1,1]
hidden state | [1,22,4096] | [1,1,4096]
本次 Q | [1,32,22,128] | [1,32,1,128]
本次新 K/V | [1,8,22,128] | [1,8,1,128]
累计 K/V cache | [1,8,22,128] | [1,8,23,128]
attention probabilities | [1,32,22,22] | [1,32,1,23]
logits | [1,22,151936] | [1,1,151936]

## 第 41 页 3.4 Decode 读取全部历史 K/V

新 query 位于位置 22，可以关注包含自身的全部 23 个位置
内容参考自：Transformers v4.51.3 / Qwen3 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
每层每个 Q head 计算 1 个 query，读取 T 个 K/V

## 第 42 页 3.4 KV Cache 的存储量

每处理一个新输入位置，36 层各自向 cache 追加该位置的 K/V
内容参考自：Qwen3-8B 配置与本次张量采集 https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/config.json
上下文长度 | 全部 36 层 K/V 的逻辑存储
每新增 1 个缓存位置 | 147456 bytes = 144 KiB
Prefill：T = 22 | 3,244,032 bytes = 3.0938 MiB
T = 4096（按公式计算） | 576 MiB
只统计 K/V 张量；未包含权重、临时激活和显存分配器预留空间

## 第 43 页 3.5 一次完整生成的实测记录

输入：中国的首都是哪里？请用一句话回答。
Forward | 输入长度 | 位置 / 末位置 | Cache 长度 | 预测 Token
prefill | 22 | 21 | 22 | '中国的'
decode_1 | 1 | 22 | 23 | '首'
decode_2 | 1 | 23 | 24 | '都是'
decode_3 | 1 | 24 | 25 | '北京'
decode_4 | 1 | 25 | 26 | '。'
decode_5 | 1 | 26 | 27 | '<|im_end|>'
最终输出：中国的首都是北京。

## 第 44 页 4.1 推理结果的交叉检查

同一份权重、同一输入与 greedy 策略下，比较三种执行路径
检查 | 本次结果
最简手写循环 vs 采集脚本 | 生成 token ID 序列完全一致
手写循环 vs model.generate() | 生成 token ID 序列完全一致
缓存推理 vs 每轮完整前缀重算 | 每轮 argmax 一致
首层：追加前后的历史 K/V | 首层历史切片逐元素完全相同
重算与缓存路径的 logits 最大绝对差 | 0.750000（BF16，限本次实验）

## 第 45 页 4.2 最简循环中的关键边界

Prefill 预测 y₁；decode 输入 y₁，再预测 y₂ Decode 的 input_ids 长度为 1，attention_mask 覆盖完整上下文 position 随 cache 长度递增，已缓存的 K 不再做 RoPE cache 每层保存 K/V，不保存 Q 或全部 hidden states 先检查 EOS，再决定是否执行下一轮 forward
内容参考自：Hugging Face / Caching https://huggingface.co/docs/transformers/v4.51.3/cache_explanation

## 第 46 页 4.3 运行代码与课堂实验

配套文件包含最简推理、张量采集和本次实测数据
# See README.md for the tested dependency versions. python code/minimal_inference.py --model Qwen/Qwen3-8B python code/walkthrough_prefill.py --model Qwen/Qwen3-8B python code/collect_trace.py --model Qwen/Qwen3-8B --out my_trace  # data/trace.json       shapes, indexed values, generation trace # data/tensors.pt       full layer-0 tensors: prefill / decode_1
实验 1：修改 prompt 长度，预测所有 shape 的变化
实验 2：读取 Q/K 的完整 128 维，手算并核对一次 RoPE
实验 3：去掉 cache，比较生成结果与重复计算的范围

## 第 47 页 附录：中间张量的采集位置

Linear 输出用 forward hook，RoPE 前后在原函数调用处记录
内容参考自：Transformers v4.51.3 / 采集脚本对应位置 https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py
saved = {} def hook(module, args, output): saved["q_projection"] = output.detach().cpu().clone()  q_proj = model.model.layers[0].self_attn.q_proj handle = q_proj.register_forward_hook(hook) with torch.inference_mode(): out = model(**inputs, use_cache=True) handle.remove() print(saved["q_projection"].shape)
RoPE、attention probabilities 与 cache 的完整采集实现见 collect_trace.py
