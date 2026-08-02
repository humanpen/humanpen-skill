# humanpen-skill

**让你的 AI Agent 真正会处理文档。** [HumanPen](https://humanpen.net) 的
[Agent Skill](https://agentskills.io)。让 Claude Code、Codex、Cursor、Gemini CLI
等 40 多个客户端直接对硬盘上的 `.docx`、`.pptx`、`.pdf` 动手：降低 AI 检测率、
转换参考文献格式、按字数缩写、或者翻译——排版、表格、图片、引文和公式全部保持
原样。

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent_Skills-open_standard-6E56CF.svg)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

[English](README.md) · 简体中文 · [日本語](README.ja.md)

[官网](https://humanpen.net) · [价格](https://humanpen.net/pricing) · [开发者文档](https://humanpen.net/developers)

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

在 <https://humanpen.net> 注册，然后到 <https://humanpen.net/settings/api-keys>
创建 key。新账号有赠送积分，够跑一篇文档看看效果。

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
<summary><b>OpenAI Codex</b></summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.agents/skills/humanpen
```

Codex 也会读仓库里的 `.agents/skills/`，想只在某个项目里用就克隆到那里。
</details>

<details>
<summary><b>Cursor、Gemini CLI、OpenCode、Copilot、Goose、Amp、Kiro 等 35+ 客户端</b></summary>

这就是一个标准的 [Agent Skill](https://agentskills.io)：一个装着 `SKILL.md` 的
文件夹。所有实现该标准的客户端加载的都是同一个文件夹，区别只在于各自扫描哪个
目录——每家自己的文档里都写了。把仓库克隆进那个目录即安装完成。

```bash
git clone https://github.com/humanpen/humanpen-skill
```
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

**`ai_percent` 可能是 `null`，而这通常是好消息。** 当 AI 率**低于 20%** 时，
Turnitin 打印的是 `*` 而不是数字——这一档它拒绝给出具体数值，因为其中误判太多。
所以 `null` 的意思是「低于 20%，Turnitin 不肯多说」，既不是 0，也不是「没结果」。

## 常见问题

**能把 Turnitin 的 AI 率降下来吗？**
`balanced` 版一般一次就能降到 20% 以下——这正是 Turnitin 改打 `*`、不再给数字的
门槛。没到位就把结果连同新报告再传一次，只重写仍被标出的片段。

**iThenticate 的报告也支持吗？**
支持，两种都能传，格式从文件自动识别。

**我的文档会进模型上下文吗？**
不会。上传文件，返回一个路径。40 页的论文不消耗任何 token。

## 相关链接

- [API 文档](https://api.humanpen.net/v1/docs.md) ·
  [OpenAPI schema](https://api.humanpen.net/v1/openapi.json)
- [humanpen-mcp](https://github.com/humanpen/humanpen-mcp)——同样的能力做成
  MCP server
- [humanpen.net](https://humanpen.net)

Apache-2.0
