# humanpen-skill

**让 Claude Code 真正会处理文档。** 一个技能，让 Agent 能直接对硬盘上的 `.docx`、
`.pptx`、`.pdf` 动手：降低 AI 检测率、转换参考文献格式、按字数缩写、或者翻译——
排版、表格、图片、引文和公式全部保持原样。

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-D97757.svg)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

[English](README.md) · 简体中文 · [日本語](README.ja.md)

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```

> *「这是我的论文和 Turnitin 报告——只改被标红的部分，然后把参考文献转成 IEEE 格式。」*
>
> Agent 读报告、只重写被标出的段落、转换引文格式，最后把两个文件路径交给你。
> 整个过程它没有读过论文正文。

## 为什么不直接把文字贴进对话

**它处理的是文件本身，不是文字的副本。** 把一章贴进对话，回来的是一段散文——
标题层级没了、表格没了、图表编号没了、参考文献列表没了、公式没了。HumanPen 改的
是文档本身、返回的也是文档，产出用 Word 打开还是原来的样子。

**文档内容不进入模型上下文。** 脚本从硬盘读文件、上传、然后只打印一个写好的
路径。一篇 40 页的论文不消耗你任何 token，也不会被抄进对话记录里。

**可以由检测报告来指挥。** 把 Turnitin 或 iThenticate 的 AI Writing 报告 PDF 一并
给它，它就**只**重写报告标出的那些段落，其余部分逐字节不动。为了改四分之一的
内容而重写整篇，正是引文和原意被破坏的原因。

**一条命令 = 一个完整任务。** 上传、等待、下载、存到源文件旁边——Agent 跑一条
命令、读回一个路径和一笔花费，而不是每次自己拼 HTTP 请求、自己写轮询循环。

**没有依赖要装。** 一个 Python 脚本，只用标准库，Python 3.8+ 即可。

## 获取 API Key

在 <https://humanpen.net/settings> 创建。新账号赠送 100 积分——够处理一篇 1000 词
的文档。计费为**实际处理**每 1000 词 100 积分，每个任务最低 10 积分。
**失败和取消的任务不计费。**

```bash
export HUMANPEN_API_KEY=hp_your_key
```

或者把本目录下的 `.env.example` 复制为 `.env`——它已被 gitignore。

## 安装

<details open>
<summary><b>Claude Code</b>（插件）</summary>

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```
</details>

<details>
<summary><b>Claude Code</b>（手动）</summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.claude/skills/humanpen
```

想只在某个项目里用？克隆到该仓库的 `.claude/skills/humanpen`。
</details>

<details>
<summary><b>OpenAI Codex，以及任何读 AGENTS.md 的 Agent</b></summary>

Codex 没有技能加载器，所以直接把脚本告诉它。克隆到任意位置，然后在项目的
`AGENTS.md` 里加上：

```markdown
## HumanPen
文档处理——降 AI 检测率、改引文格式、缩写、翻译——通过
`python3 /path/to/humanpen-skill/scripts/humanpen.py --help`。
需要环境变量 HUMANPEN_API_KEY。每个任务消耗积分——实际处理每 1000 词 100 积分、
最低 10 积分：先说明再等我确认。
```

命令完全一样，区别只在于「怎么告诉 Agent 有这么个东西」。
</details>

想用 MCP？[humanpen-mcp](https://github.com/humanpen/humanpen-mcp) 提供同样的
能力，并且在 Cursor、Windsurf、Cline、OpenCode 和 Claude Desktop 里都能用。

## 命令

```bash
# 降低 AI 检测特征。--strategy 可选：conservative | balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# 只重写检测报告标出的段落
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf

# 文内引用与参考文献列表转成指定格式
python3 scripts/humanpen.py fix-citations paper.docx --style apa7

# 缩写到目标字数
python3 scripts/humanpen.py condense paper.docx --max-words 4000

# 翻译，保持排版
python3 scripts/humanpen.py translate paper.docx --to zh

# 读 Turnitin/iThenticate 报告：总体 AI 率、被标出的段落
python3 scripts/humanpen.py report turnitin.pdf

# 查看之前留着跑的任务，以及余额
python3 scripts/humanpen.py status <job_id> --download paper.docx
python3 scripts/humanpen.py balance
```

任务完成后会打印 JSON，其中 `output` 是文件落点、`credits_charged` 是花费。
任何子命令加 `--help` 都能看到它的参数。

支持的引文格式：APA 7、MLA 9、Harvard、Chicago（两种）、IEEE、Vancouver、
GB/T 7714、AMA、ACS、OSCOLA。翻译覆盖 12 种语言。

## 两件值得知道的事

**任务是分钟级的。** 命令会一直等，并把进度打到 stderr。中断命令**不会**取消
任务——`status <job_id>` 可以把它接回来。

**`ai_percent` 可能是 `null`，而 `null` 不等于 0。** 当提交文本太短、无法评估时，
报告打印的是 `*` 而不是数字。把它当成「AI 率 0%」是在替别人下没下过的结论。

## 相关链接

- [API 文档](https://api.humanpen.net/v1/docs.md) ·
  [OpenAPI schema](https://api.humanpen.net/v1/openapi.json)
- [humanpen-mcp](https://github.com/humanpen/humanpen-mcp)——同样的能力做成
  MCP server
- [humanpen.net](https://humanpen.net)

Apache-2.0
