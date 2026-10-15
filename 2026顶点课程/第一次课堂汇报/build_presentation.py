"""Generate editable PPTX, layout-matched PDF/PNGs, notes and evidence manifest.
Run with Python packages: python-pptx, Pillow, PyMuPDF.
All experiment values are read from the existing submission JSON files.
"""
from pathlib import Path
import json, math, hashlib, zipfile, subprocess, io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image, ImageDraw, ImageFont
import pymupdf as fitz

OUT = Path(__file__).resolve().parent
COURSE = OUT.parent
W1 = COURSE / '第一周_LLM推理/提交'
W2 = COURSE / '第二周_LLM应用开发/提交'
W3 = COURSE / '第三周_Agent与工具调用/提交'
def read(p): return json.loads(p.read_text())
d1 = read(W1/'run.json')
plain = read(W2/'results/plain.json')
example = read(W2/'results/example.json')
runs = [read(p) for p in sorted((W3/'results').glob('run*.json'))]
BG='F5F3ED'; NAVY='172D3B'; TEAL='087E83'; RUST='B65032'; MUTED='63737C'; WHITE='FFFFFF'; LIGHT='E5ECEB'; PALE='F2E5DC'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
MONO=FONT
SCALE=144
prs=Presentation(); prs.slide_width=Inches(13.333333); prs.slide_height=Inches(7.5)
prs.core_properties.title='从模型推理到可验证的 Agent：前三周学习与任务汇报'
prs.core_properties.author='姜楠翔 · 23230610'
prs.core_properties.subject='2026 顶点课程 · 2026-09-29 第一次课堂汇报'
slides=[]; warnings=[]

class Canvas:
    def __init__(self, title, tag, source='', appendix=False):
        self.slide=prs.slides.add_slide(prs.slide_layouts[6])
        self.image=Image.new('RGB',(1920,1080),'#'+BG)
        self.draw=ImageDraw.Draw(self.image)
        self.title=title; self.note=''; self.seconds=0; self.appendix=appendix
        self.slide.background.fill.solid(); self.slide.background.fill.fore_color.rgb=RGBColor.from_string(BG)
        slides.append(self)
        self.rect(0,0,13.333,.09,TEAL)
        self.text(.55,.32,12.2,.28,tag,11,TEAL,True)
        self.text(.55,.88,12.2,.7,title,30,NAVY,True)
        self.rect(.55,6.89,12.23,.012,'D8DDD9')
        self.text(.55,7.02,11.55,.23,source or '2026 顶点课程  /  姜楠翔 23230610  /  2026.09.29',9,MUTED)
        self.text(12.15,7.00,.64,.25,f'{len(slides):02d}',11,TEAL,True)
    def rect(self,x,y,w,h,color,radius=False):
        sh=self.slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
        sh.fill.solid(); sh.fill.fore_color.rgb=RGBColor.from_string(color); sh.line.fill.background()
        if radius: sh.adjustments[0]=.06
        box=tuple(round(v*SCALE) for v in (x,y,x+w,y+h))
        if radius:self.draw.rounded_rectangle(box, radius=12,fill='#'+color)
        else:self.draw.rectangle(box,fill='#'+color)
    def text(self,x,y,w,h,text,size=20,color=NAVY,bold=False,mono=False):
        # Split into individually positioned lines to keep PPTX and preview geometry aligned.
        fp=MONO if mono else BOLD if bold else FONT
        f=ImageFont.truetype(fp,round(size*2),index=7 if mono else 2)
        maxw=w*SCALE-8; lines=[]
        for para in str(text).split('\n'):
            current=''
            for ch in para:
                if self.draw.textlength(current+ch,font=f)>maxw and current:
                    lines.append(current); current=ch
                else:current+=ch
            lines.append(current)
        step=size/72*1.34
        if len(lines)*step>h+.035:
            warnings.append({'slide':len(slides),'text':str(text)[:80],'needed':len(lines)*step,'height':h})
        for i,line in enumerate(lines):
            yy=y+i*step
            tb=self.slide.shapes.add_textbox(Inches(x),Inches(yy),Inches(w),Inches(step+.045))
            tf=tb.text_frame; tf.margin_left=0;tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0;tf.word_wrap=False
            p=tf.paragraphs[0];p.text=line;p.font.name='Noto Sans Mono CJK SC' if mono else 'Noto Sans CJK SC';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
            self.draw.text((round(x*SCALE),round(yy*SCALE)),line,font=f,fill='#'+color,anchor='lt')
    def card(self,x,y,w,h,label,body,accent=TEAL,size=20):
        self.rect(x,y,w,h,WHITE,True);self.rect(x,y,.055,h,accent)
        self.text(x+.22,y+.2,w-.44,.4,label,17,accent,True)
        self.text(x+.22,y+.77,w-.44,h-.92,body,size)
    def code(self,x,y,w,h,label,code,size=15):
        self.rect(x,y,w,h,NAVY,True)
        self.text(x+.2,y+.17,w-.4,.33,label,12,'83D1CB',True)
        self.text(x+.2,y+.66,w-.4,h-.79,code,size,WHITE,mono=True)
    def banner(self,text,y=6.15,color=TEAL):
        self.rect(.55,y,12.23,.53,color,True);self.text(.76,y+.11,11.85,.35,text,16,WHITE,True)
    def notes(self,seconds,text):
        self.seconds=seconds;self.note=text
        mode='备答，不计入正文时长' if self.appendix else f'正文建议 {seconds} 秒'
        self.slide.notes_slide.notes_text_frame.text=f'第 {len(slides)} 页｜{self.title}\n{mode}\n\n{text}'

s=Canvas('从模型推理到可验证的 Agent','2026 CAPSTONE  /  FIRST CLASS PRESENTATION')
s.text(.62,1.95,11.7,.95,'前三周学习与任务完成情况',34,NAVY,True)
s.text(.65,3.06,11.7,.65,'核心问题：模型输出怎样变成可信的程序结果？',24,TEAL)
for x,num,label,detail in [(0.65,'01','推理观测','时间 · token · hidden states'),(4.78,'02','应用校验','流式输出 · 自动测试 · 修复'),(8.91,'03','Agent 分析','工具调用 · trace · Prompt')]:
    s.rect(x,4.2,3.78,1.48,WHITE,True);s.text(x+.2,4.4,.65,.5,num,27,TEAL,True);s.text(x+.98,4.4,2.6,.45,label,22,NAVY,True);s.text(x+.2,5.08,3.4,.36,detail,14,MUTED)
s.text(.65,6.18,11.7,.4,'姜楠翔  ·  23230610                 2026 年 9 月 29 日',17,MUTED)
s.notes(15,'大家好，我是姜楠翔。前三周我依次完成了 Qwen 推理、代码助手和最小 Agent 实验。今天围绕一个问题汇报：怎样把模型生成的文本，变成可以检查、可以信任的程序结果。')

s=Canvas('任务要求与完成情况','01  /  SCOPE & EVIDENCE','依据：三周 作业.md、提交/提交说明.md 与原始结果；平台上传状态未核实')
s.card(.55,1.92,3.95,2.72,'第一周｜推理跑通','自拟输入与真实输出\n记录耗时、生成 token 数\n打印张量 shape 和数值',size=19)
s.card(4.69,1.92,3.95,2.72,'第二周｜示例 + 小拓展','普通 / 流式 / 结构化已跑通\n新增自动测试与反馈修复\n保留成功、失败的逐轮结果',size=19)
s.card(8.83,1.92,3.95,2.72,'第三周｜Agent + 对照','14 项自测本次复跑全 PASS\n已有 5 组基线、完整 trace\n分析两条链并做 Prompt 拓展',size=18)
s.text(.75,4.95,11.6,.8,'共同环境：Qwen2.5-1.5B-Instruct / CUDA / bfloat16\nGPU：RTX PRO 6000 Blackwell Max-Q；第三周另比较 3B、7B',17,MUTED)
s.banner('代码、JSON 和提交包均已在本地；第三周相邻单变量设计仍有一处需要补严。',color=RUST)
s.notes(20,'第一周要求推理和张量观测，第二周要求跑通三种输出并做一项拓展，第三周要求自测、五次实验和调用链分析。本地都有代码和真实记录，自测也已复跑通过。不过第三周有一处相邻实验改变了两个参数，我会明确比较基准，不把它当作严格的连续单变量实验。')

s=Canvas('第一周：既量化推理，也检查回答','02  /  QWEN INFERENCE','证据：第一周/提交/run.json；代码 qwen_inference.py:58、139–147（路径缩写）')
for x,value,label in [(.55,f"{d1['generation_seconds']:.3f} s",'预热后的单次 generate'),(4.69,str(d1['generated_tokens'])+' tokens','真实生成数，含 EOS'),(8.83,f"{d1['tokens_per_second']:.1f} tokens/s",'74 ÷ 3.622，单次观测')]:
    s.rect(x,1.9,3.95,1.05,WHITE,True);s.text(x+.22,2.02,3.51,.49,value,28,TEAL,True);s.text(x+.22,2.6,3.51,.3,label,12,MUTED)
s.code(.55,3.18,6.03,2.63,'按源码简化 · 先同步，再计时',
'''model.generate(**inputs, generation_config=config)
synchronize(device)  # 预热结束
start = time.perf_counter()
generated = model.generate(
    **inputs, generation_config=config)
synchronize(device)
elapsed = time.perf_counter() - start''',13)
s.text(6.88,3.2,5.72,.5,'Prefill → Decode：观察增量计算',21,NAVY,True)
s.text(6.88,3.9,5.72,1.74,'hidden states：29 个 = 28 层 + embedding\n最后层：[1, 48, 1536] → [1, 1, 1536]\nK cache：[1, 2, 48, 128] → [1, 2, 49, 128]\n数值 [0,-1,:4]：0.31055, 2.0, 0.0, 1.58594',16)
s.banner('输出把 KV cache 解释成数据库缓存，且未遵守“两句话”：跑通推理不等于回答正确。',color=RUST)
s.notes(35,'第一周我问模型：用两句话解释 KV cache。输入有四十八个 token，预热一次后，正式生成七十四个 token，用时三点六二二秒。计时前后做 GPU 同步，加载和调试不计入生成耗时。调试里，最后层 hidden state 从四十八个位置变成一个位置，缓存长度从四十八增加到四十九，对应增量解码。但回答混入了数据库缓存概念，也没有遵守两句话的要求。实际 KV cache 缓存的是历史 token 的键和值。因此跑通和答对需要分别检查。')

s=Canvas('第二周：从“能看”到“能校验”','03  /  CODE ASSISTANT','证据：第二周/提交/results/plain.json、example.json；llm_app.py:123–168')
s.card(.55,1.92,5.93,1.8,'普通回答','216 tokens / 6.23 s\n带 Markdown 围栏和解释，需要另行提取代码。',size=18)
s.card(6.68,1.92,6.1,1.8,'流式 + 结构化示例','58 tokens / 2.21 s；首段文本约 1.10 s\nSchema、语法通过；原示例尚未执行功能测试。',size=18)
s.text(.65,4.01,12,.42,'拓展后的五层校验：validate_text(text, task)',22,NAVY,True)
steps=[('JSON','json.loads'),('字段','Pydantic'),('语法','ast.parse'),('函数名','顶层 def'),('功能','run_tests')]
for i,(label,detail) in enumerate(steps):
    x=.55+i*2.49;s.rect(x,4.73,2.27,.98,LIGHT,True);s.text(x+.12,4.83,2.03,.39,label,22,TEAL,True);s.text(x+.12,5.32,2.03,.28,detail,13,MUTED)
s.banner('流式改善到达体验；JSON / Schema / 语法 / 功能正确性需要逐层区分。')
s.notes(30,'第二周普通回答是带围栏的代码和解释；流式结构化示例在一点一秒左右开始到达文本，最终通过字段和语法检查。两次请求的提示词和输出长度不同，所以不能据此认定流式本身更快。我的拓展是在 JSON、字段和语法之后，再检查函数名并实际执行测试。校验结果才能说明程序是否满足任务，而不是只看生成文本像不像代码。')

s=Canvas('第二周拓展：用测试反馈驱动自动修复','04  /  VALIDATE → FEEDBACK → REPAIR','证据：第二周/提交/results/ext_*；llm_app.py:105、171、325–338')
s.text(.65,1.83,12,.6,'--task 读取任务与测试；--repair 3 允许最多 3 次修复（总计最多 4 次生成）。',17,MUTED)
s.code(.55,2.6,5.45,2.87,'fresh 模式 · 实际代码节选（长提示常量见源码）',
'''if args.repair_mode == "history":
    messages.append({
        "role": "assistant", "content": text})
    prompt = feedback
else:
    messages.pop()
    # 原始任务 + 错误反馈；丢弃失败回答''',13)
headers=['任务','不修复','history v2','fresh v3']
rows=[['正数计数','JSON 错误','修复 3 次 / 5/5','修复 1 次 / 5/5'],['第二大不同值','语法错误','修复 3 次仍失败','修复 2 次 / 7/7'],['游程编码 rle','语法错误','修复 3 次仍失败','修复 3 次仍失败']]
xs=[6.23,7.83,9.15,10.97]; widths=[1.52,1.24,1.74,1.77]
for j,v in enumerate(headers):s.text(xs[j],2.66,widths[j],.45,v,14,TEAL,True)
for i,row in enumerate(rows):
    s.rect(6.18,3.23+i*.67,6.6,.59,WHITE if i%2==0 else LIGHT,True)
    for j,v in enumerate(row):s.text(xs[j],3.36+i*.67,widths[j],.48,v,12,NAVY)
s.text(6.22,5.49,6.55,.51,'校验器：python -I 子进程；逐项比较值与类型；5 秒超时。',14,MUTED)
s.banner('这 3 个任务中，fresh 修好 2 个；rle 仍失败。上下文重建的改善只在本组实验内成立。')
s.notes(40,'我新增任务文件、测试执行器和自动反馈。失败后，history 模式保留错误回答，再追加修改要求；fresh 模式移除失败回答，重新发送原始任务和错误说明。在三个任务中，history 只修好了正数计数，而且用了三次修复。fresh 分别用一次和两次修复，通过正数计数的五个测试和第二大不同值的七个测试。游程编码仍然失败。这个结果提示错误上下文可能影响修复，但样本很少，不能推广成普遍结论。子进程隔离和超时也不等于完整沙箱。')

s=Canvas('第三周：同一任务，五组基线结果','05  /  AGENT BASELINE','证据：第三周/提交/results/run1–run5；比较基准按历史配置明确标注，未补跑基线')
s.text(.65,1.83,12,.54,'固定任务：读取 test_report.txt，计算测试通过率；passed=47、failed=3 → 94%。',19,NAVY,True)
cols=[.65,1.3,4.2,6.04,8.73]; widths=[.6,2.85,1.73,2.6,3.75]
for j,v in enumerate(['组','配置','比较基准','status','最终结果 / 失败位置']):s.text(cols[j],2.64,widths[j],.43,v,15,TEAL,True)
rows=[['1','1.5B / greedy','默认','ok','未答出数值，错误收尾'],['2','1.5B / sample T=.7','对 1：采样开关','ok','未答出数值，错误收尾'],['3','1.5B / sample T=1.2','对 2：温度','too_many_failures','重复非法路径、格式错误'],['4','3B / greedy','对 1：模型规模','max_steps','算出 94，但未合法 final'],['5','7B / greedy','对 4：模型规模','too_many_failures','LaTeX 截取 / JSON 转义失败']]
for i,row in enumerate(rows):
    y=3.23+i*.49;s.rect(.55,y-.07,12.23,.46,WHITE if i%2==0 else LIGHT,True)
    for j,v in enumerate(row):s.text(cols[j],y+.015,widths[j],.38,v,12 if j in (2,3) else 14)
s.text(.65,5.84,12,.36,'Agent Loop：raw → parse_decision → execute → Observation → 下一轮 / final',17,TEAL,True)
s.banner('5 组最终答案正确数：0/5；其中 2 组 status=ok。终态必须与答案、trace 联合评估。',y=6.25,color=RUST)
s.notes(30,'第三周任务固定为读取报告，计算四十七除以五十，也就是百分之九十四。五组基线最终都没有答对，其中两组却显示 ok。比较温度用第二组对第三组，比较模型规模用第一组对第四组，以及第四组对第五组。第三组切到第四组同时改变了采样和模型规模，因此不能把整个执行顺序说成严格的相邻单变量对照。这也是实验设计需要补严的地方。')

s=Canvas('两条代表性调用链：错误收尾 vs 有答案却不收尾','06  /  TRACE ANALYSIS','证据：run1_1.5B_greedy.json、run4_3B_greedy.json；raw、decision、observation 均来自原始 trace')
s.rect(.55,1.92,5.94,3.95,WHITE,True);s.rect(6.7,1.92,6.08,3.95,WHITE,True)
s.text(.77,2.12,5.5,.5,'1.5B greedy｜status = ok',22,RUST,True)
s.text(.77,2.87,5.46,2.56,'① raw 含 JSON → decision: read_file\n   path="/content/test_report.txt"\n   Observation: PermissionError\n② raw 为自然语言 → format_error\n③ raw 为 final JSON → decision: final\n   answer：“计算测试通过率需要更多的信息…”',16)
s.text(6.93,2.12,5.57,.5,'3B greedy｜status = max_steps',22,TEAL,True)
s.text(6.93,2.87,5.56,2.56,'① read_file("test_report.txt") → 47 / 3\n② calculator("47/(47+3)*100") → 94.0\n③ 再算失败率 → 6.0\n④ raw：“通过率为 94.0%…” → 无 JSON\n⑤ 重新调用 calculator → 100.0（算式错）\n⑥ raw 为自然语言 → 格式失败，步数耗尽',16)
s.banner('代码定位：final 分支直接返回 finish("ok", answer)，没有检查任务正确性。')
s.notes(45,'第一条是小模型的错误收尾。它先编造绝对路径，工具拒绝并提示使用相对路径；下一轮只写自然语言，被判格式错误；第三轮合法输出 final，却说信息不足。代码只要解析到 final 就返回 ok，没有验证答案。第二条是三 B 的链：先读到四十七和三，再调用计算器得到九十四。但随后多算失败率，并用自然语言给答案，违反了 final 的 JSON 协议。纠错之后又把算式改错，最终耗尽步数。两条链分别说明：合法收尾可能答错，算出正确中间结果也可能无法完成流程。')

s=Canvas('第三周拓展：Prompt 改变失败发生的位置','07  /  PROMPT ABLATION','证据：第三周/提交/results/ext_* 共 19 个 JSON；1.5B 固定 seed 1–5，T=.7 / top_p=.8 / top_k=20')
s.card(.55,1.9,3.95,2.93,'原始 Prompt｜1.5B × 5','0/5 最终答案正确\n没有一次成功读取目标文件\nseed3 的“Observation”是模型\n自己写出的文本，不是真工具结果',accent=RUST,size=17)
s.card(4.69,1.9,3.95,2.93,'v2｜文件清单 + 收尾示例','5/5 成功读取目标文件\n0/5 调用 calculator\n0/5 最终答案正确\n本组出现直接心算与错误数值',size=17)
s.card(8.83,1.9,3.95,2.93,'v3｜要求算术必须用工具','5/5 调用 calculator\n0/5 最终答案正确\n4 次用未绑定变量，1 次列错算式\n工具被调用 ≠ 参数正确',size=17)
s.text(.65,5.12,12,.7,'3B / 7B：v2、v3 的四个贪心运行均合法收尾，最终答案均为 94%。\nv3 的两条链：read_file → calculator → final；不改 Loop、工具与解析逻辑。',18,TEAL,True)
s.banner('观察：Prompt 改善了路径和收尾；1.5B 的数值代入问题仍在。小样本不能证明模型能力边界。')
s.notes(35,'拓展只改变系统提示词，保持 Loop 和工具逻辑不变。v2 提供真实文件名、收尾规则和示例，五个 seed 都读到了文件，但都跳过计算器并答错。v3 加入必须调用计算器的规则和完整示例，五次都调用了工具，可是四次传入未绑定变量，一次把算式列错，所以仍然零次答对。三 B 和七 B 在两个新版提示下都答对了。这组实验让我看到，提示词能改善调用流程，但不能保证工具参数正确，也不足以证明小模型的能力边界。')

s=Canvas('我的收获：可观测、可验证、可定位','08  /  TAKEAWAYS & NEXT STEP')
s.card(.55,1.97,3.95,2.65,'01｜把结果保存下来','输入、生成参数、耗时、token\n张量 shape 与取样数值\nraw / decision / observation',size=19)
s.card(4.69,1.97,3.95,2.65,'02｜把正确性分层检查','生成成功 ≠ 回答正确\nSchema 通过 ≠ 功能正确\nstatus=ok ≠ 任务完成',size=19)
s.card(8.83,1.97,3.95,2.65,'03｜把失败定位到一步','路径选择、输出协议、数值代入\n分别检查，不用终态掩盖原因\n保留未修好的 rle 与失败链',size=18)
s.text(.75,4.99,11.7,.84,'下一步：补严单变量序列；增加按数值与工具证据判定的最终验收。\n局限：每组样本少；测试覆盖有限；Prompt 约定没有约束解码保证。',19,MUTED)
s.banner('前三周的主线：先跑通，再加校验，最后通过 trace 理解可靠性。谢谢！')
s.notes(20,'我的主要收获是三点：保存足够的观测信息，把正确性分层检查，再通过 trace 定位失败。下一步我会补严单变量实验，并让最终验收同时检查数值和工具证据。这次样本和测试覆盖都有限，因此保留失败结果，不把局部改善说成普遍结论。谢谢大家。')

s=Canvas('附录 A｜第一周输入、输出与张量数值','APPENDIX  /  INFERENCE DETAILS','证据：第一周/提交/run.json；完整原文未改写',True)
s.text(.65,1.86,12,.65,'输入：'+d1['prompt'],19,NAVY,True)
s.card(.55,2.66,7.22,2.55,'模型原始输出',d1['output_text'],RUST,size=17)
s.code(7.99,2.66,4.79,2.55,'hidden_states[28][0,-1,:8]',str(d1['debug']['hidden_states']['28']['sample']),14)
s.text(.65,5.4,12,.67,'Prefill shape [1,48,1536]；Decode shape [1,1,1536]；logits [1,48,151936]\nK cache 的 2 是 KV head 数，128 是每个 head 的维度；调试 forward 不计入正式耗时。',16)
s.banner('本次只有一个正式计时样本，未做统计；缓存 shape 观测不等于实测了缓存加速倍数。',color=RUST)
s.notes(0,'这一页保留第一周完整输入和模型输出。输出把 KV cache 泛化成内存和数据库缓存，后面又说快速访问模型参数，这不准确。LLM 的 KV cache 保存历史 token 的注意力键和值，避免逐步解码时反复计算这些历史投影。hidden state 的三个维度是 batch、序列长度、hidden size；缓存的四个维度是 batch、KV head、序列长度、head 维度。数值取的是最后一个位置的前八个分量。这里只做了单次计时，不能报告平均性能或有无缓存的加速比。')

s=Canvas('附录 B｜第二周：校验器代码与真实通过版本','APPENDIX  /  VALIDATOR & GENERATED CODE','代码：llm_app.py:123–168、105–121；结果：ext_v3fresh_second_largest_repair3.turn03.json',True)
s.code(.55,1.93,6.34,3.94,'核心校验顺序 · 按源码省略异常处理',
'''data = json.loads(text)
result = CodeResult.model_validate(data)
tree = ast.parse(result.code)
defined = [n.name for n in tree.body
           if isinstance(n, ast.FunctionDef)]
# expected == result.function_name
# and expected in defined
tests = run_tests(result.code, expected,
                  task["tests"])
out["passed"] = tests["status"] == "passed"''',14)
accepted=read(W2/'results/ext_v3fresh_second_largest_repair3.turn03.json')['result']['parsed']['code']
s.code(7.12,1.93,5.66,2.67,'模型真实生成代码 · 第 2 次修复后',accepted,14)
s.text(7.15,4.87,5.58,.88,'7/7 测试通过：重复值、空列表、单值、负数等。\n测试用例通过只证明这些用例的行为。',17)
s.banner('run_tests 比较结果值与类型；本组未在真实模型中触发“语法正确但测试失败”的反馈分支。',color=RUST)
s.notes(0,'validate_text 先解析 JSON，再做 Pydantic 字段校验和 AST 语法检查。之后检查任务规定的函数名，代码顶层是否真的定义了该函数，最后执行任务测试。右侧是模型在 fresh 模式第二次修复后真实生成的版本，经过七个用例。它用 set 去重，再排序取倒数第二个；不足两个不同值时返回 None。注意七个测试通过不是形式化正确性证明。本组真实生成失败主要发生在 JSON 和语法层，功能失败的反馈路径只有之前离线检查记录，不能说真实模型已经完整验证了所有分支。')

s=Canvas('附录 C｜第二周：修复上下文与执行隔离','APPENDIX  /  REPAIR IMPLEMENTATION','代码：llm_app.py:105–121、325–338；history / fresh 只是两种上下文组织方式',True)
s.code(.55,1.92,7.0,3.92,'按源码简化 · 保留与清除上下文的差别',
'''feedback = repair_feedback(result, task)
# 仅 structured 且 complete 时生成反馈
if feedback and repairs < args.repair:
    if source == "user":
        task_prompt = prompt
    repairs, source = repairs + 1, "auto_repair"
    if args.repair_mode == "history":
        messages.append({
            "role": "assistant", "content": text})
        prompt = feedback
    else:
        messages.pop()  # 删除本轮 user 消息''',12)
s.text(7.82,2.02,4.69,.5,'fresh 分支随后重建 prompt',19,TEAL,True)
s.text(7.82,2.83,4.69,1.17,'原始任务 + 本次失败说明\n不加入失败 assistant 回答\n每轮写入 .turnNN.json',18)
s.text(7.82,4.42,4.69,1.08,'执行：sys.executable -I -c\n超时：5 秒\n比较：值相等 AND 类型相同',17)
s.banner('执行生成代码的子进程可以访问系统资源；-I 和 timeout 不是完整安全沙箱。',color=RUST)
s.notes(0,'这里给出修复实现的关键差异。进入修复前保存用户的原始任务。history 把失败的 assistant 回答加入 messages，并追加错误反馈。fresh 则删除当前 user 消息，然后用原任务加反馈构造下一轮 prompt，失败回答没有加入历史。每轮结果分别保存，repair_round 从零开始，零表示最初生成。测试由当前 Python 的隔离模式子进程执行，超时五秒，它防止常见环境干扰和长时间卡住，但没有文件、网络或资源访问沙箱，不能作为运行任意不可信代码的安全保证。')

s=Canvas('附录 D｜Agent 协议、终止条件与 7B 失败链','APPENDIX  /  PARSING & TERMINATION','代码：agent_v0.py:202–211、285–315；证据：run5_7B_greedy.json（纠正原提交说明概括）',True)
s.code(.55,1.93,6.13,2.49,'实际解析与收尾代码节选',
'''start, end = text.find("{"), text.rfind("}")
return _decision.validate_json(
    text[start:end + 1])
# run_agent 中：
if decision.action == "final":
    return finish("ok", decision.answer)''',13)
s.text(.65,4.73,5.93,1.09,'默认 max_steps=6，max_failures=2。\n失败数 > 2 才终止；工具成功清零。\n同工具同参数累计第 3 次触发 no_progress。',17)
s.text(6.96,2.03,5.65,.46,'7B 原始 trace 的真实错误',21,RUST,True)
s.text(6.96,2.87,5.64,2.49,'step 1：相对路径读取成功。\nstep 2：LaTeX 的 {通过率} 被截取，\n              不是合法 JSON。\nstep 3、4：final JSON 里有非法反斜杠\n              转义，且原文答案为 93.5%。\n最终：too_many_failures，未返回 answer。',16)
s.banner('解析启发式、JSON 转义和答案错误是不同问题；不能概括为“连续三轮都截到 LaTeX”。',color=RUST)
s.notes(0,'解析器用第一个左花括号到最后一个右花括号，交给判别联合校验。这能容忍 JSON 前后的解释，但也可能截到数学公式。七 B 的第二步确实是花括号截取错误；生成停止器也从第一个花括号数深度，所以结合源码推测，它可能在 LaTeX 花括号闭合时提前停止，这属于推断。第三和第四步已经在写 final JSON，却因 LaTeX 的反斜杠没有合法转义而解析失败，而且文本里的九十三点五也算错了。原提交说明把三步都概括成花括号截取，不符合原始 trace，这里已经纠正。另外源码的重复调用计数是累计次数，不是严格连续三次；工具成功才把失败计数清零。自测使用脚本化模型验证程序路径，不代表真实 Qwen 的任务成功率。')

s=Canvas('附录 E｜实验设计、复现与提交边界','APPENDIX  /  REPRODUCIBILITY','完整命令与文件清单见同目录《要求核对与证据索引.md》；原始作业未修改',True)
s.card(.55,1.93,5.93,2.17,'严格的连续单变量序列（建议补跑）','1.5B greedy → 1.5B sample T=.7\n→ 1.5B sample T=1.2 → 3B sample T=1.2\n→ 7B sample T=1.2',size=17)
s.card(6.7,1.93,6.08,2.17,'现有实验可以支持的比较','组 1 ↔ 2：采样开关；组 2 ↔ 3：温度。\n组 1 ↔ 4 ↔ 5：贪心条件下的模型规模。\n不从五组单次结果推断稳定成功率。',size=17)
s.text(.65,4.42,12,.83,'提交要求：第一周 脚本+结果+说明；第二周 修改代码+结果+说明；第三周 5 份完整 trace+说明。\n第二、三周命名：学号_姓名_第二/三周作业.zip；不包含模型权重与虚拟环境。',17)
s.text(.65,5.5,12,.62,'截止：第一周 9/20 23:59；第二周 9/27 23:59；第三周 10/4 23:59。\n9/29 上午汇报仅 3–5 分钟；正文讲到第 9 页，附录用于答疑。',17,MUTED)
s.banner('截至制作时：已有本地提交包，未确认 SPOC 上传；建议补跑配置没有当作已完成实验。',color=RUST)
s.notes(0,'这里解释设计边界。原始五组可以做共享基准的比较，但第三组到第四组不是严格单变量变更。如果老师要求连续相邻每次只改一项，建议新增三 B 采样一点二和七 B 采样一点二，再按左侧序列完整运行和保存。这个序列只是建议，没有把未跑结果写进汇报。已有提交包也只证明本地打包完成，不证明 SPOC 平台提交。截止时间按老师通知保留，第一周已经早于制作日期。正式汇报控制在九页正文，附录只在老师追问时展开。')

assert len(slides)==14
assert sum(s.seconds for s in slides)==270
OUT.mkdir(exist_ok=True);(OUT/'预览').mkdir(exist_ok=True)
ppt_path=OUT/'23230610_姜楠翔_前三周学习汇报.pptx'
prs.save(ppt_path)
doc=fitz.open()
for i,s in enumerate(slides,1):
    png=OUT/'预览'/f'{i:02d}.png';s.image.save(png)
    compressed=io.BytesIO();s.image.save(compressed,format='JPEG',quality=92)
    page=doc.new_page(width=960,height=540);page.insert_image(page.rect,stream=compressed.getvalue())
doc.save(OUT/'23230610_姜楠翔_前三周学习汇报_预览.pdf',deflate=True)
# PDF is a layout preview rendered from the shared layout, not an Office engine export.
thumbs=Image.new('RGB',(1920,math.ceil(len(slides)/3)*390),'#E4E8E7');dd=ImageDraw.Draw(thumbs)
font=ImageFont.truetype(FONT,18)
for i,s in enumerate(slides):
    im=s.image.resize((620,349));x=10+(i%3)*640;y=12+(i//3)*390;thumbs.paste(im,(x,y));dd.text((x,y+353),f'{i+1:02d}  {s.title}',font=font,fill='#'+NAVY)
thumbs.save(OUT/'预览总览.jpg',quality=92)
md=['# 前三周课堂汇报逐页讲稿','', '姓名：姜楠翔；学号：23230610。汇报日期：2026 年 9 月 29 日上午。', '', '正文第 1–9 页，建议总时长 **4 分 30 秒**。第 10–14 页为答疑附录，不在常规汇报中逐页讲。所有讲稿已写入 PPT 的备注。', '', '按正常中文语速排练；若时间紧，缩短第 5、7 页的细节，保留两个失败链的结论。']
elapsed=0
for i,s in enumerate(slides,1):
    md.extend(['',f'## 第 {i} 页｜{s.title}',''])
    if s.appendix:md.extend(['备答页，不计入正文时间。',''])
    else:
        md.extend([f'建议 {s.seconds} 秒；累计 {elapsed//60}:{elapsed%60:02d} → {(elapsed+s.seconds)//60}:{(elapsed+s.seconds)%60:02d}。','']);elapsed+=s.seconds
    md.append(s.note)
(OUT/'逐页中文讲稿.md').write_text('\n'.join(md)+'\n')
# Export a simple printable PDF of the script, with an embedded CJK font.
doc=fitz.open();page=None;y=0
for line in md:
    fsize=16 if line.startswith('# ') else 13 if line.startswith('## ') else 11
    line=line.lstrip('# ').replace('**','') if line.startswith('#') else line.replace('**','')
    font=ImageFont.truetype(FONT,round(fsize*2)); wrapped=[];cur=''
    for ch in line:
        if font.getlength(cur+ch)/2>505 and cur:wrapped.append(cur);cur=ch
        else:cur+=ch
    wrapped.append(cur)
    for part in wrapped:
        if page is None or y>780:
            page=doc.new_page(width=595,height=842);page.insert_font(fontname='noto',fontfile=FONT);y=45
        page.insert_text((45,y),part,fontname='noto',fontsize=fsize,color=(.09,.18,.23));y+=fsize*1.65
doc.subset_fonts()
doc.save(OUT/'逐页中文讲稿.pdf',deflate=True,garbage=4)
evidence=[]
for directory in [W1,W2,W3]:
    for p in sorted(directory.rglob('*')):
        if p.is_file() and p.suffix in ('.json','.py','.md','.txt'):
            evidence.append({'path':str(p.relative_to(COURSE)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
selftest=subprocess.run([str(COURSE/'第一周_LLM推理/.venv/bin/python'),str(W3/'agent_v0.py'),'--selftest'],capture_output=True,text=True)
(OUT/'agent_selftest_制作时复核.log').write_text(selftest.stdout+selftest.stderr)
assert selftest.returncode==0 and selftest.stdout.count('PASS')==14 and 'FAIL' not in selftest.stdout
manifest={'main_slides':9,'appendix_slides':5,'planned_seconds':270,'week1_seconds':d1['generation_seconds'],'week1_tokens':d1['generated_tokens'],'baseline_statuses':[d['status'] for d in runs],'selftest_pass_count':14,'sources':evidence,'layout_warnings':warnings,'preview_method':'shared-layout Pillow rendering; editable PPTX not rendered by Microsoft PowerPoint/LibreOffice'}
(OUT/'证据与制作校验.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'slides':len(slides),'planned_seconds':270,'warnings':warnings,'pptx':str(ppt_path)},ensure_ascii=False,indent=2))
