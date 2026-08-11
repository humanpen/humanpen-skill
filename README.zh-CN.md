# humanpen-skill

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent_Skills-open_standard-6E56CF.svg)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

[English](README.md) · 简体中文 · [日本語](README.ja.md)

[官网](https://humanpen.net) · [价格](https://humanpen.net/pricing) · [开发者文档](https://humanpen.net/developers)

> **关键词：** 降AI, AI降重, AI humanizer, Agent Skill, Turnitin AI检测, 降低AI率, AIGC检测, AI改写工具, DOCX降AI, Claude Code Skill, Codex Skill

**哪里标红改哪里，保留格式降 AI。** [HumanPen](https://humanpen.net) 的 [Agent Skill](https://agentskills.io)——文档级 AI humanizer，支持全文降 AI，也支持自定义修改片段，还可基于 Turnitin/iThenticate AI 率检测报告自动指定修改片段，定点改写 `.docx` / `.pptx` 中被标记的文本，同时原样保留排版、表格、图片、引文、公式等。另支持 12 种引用格式转换、按目标字数缩写、12 种语言互译。

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```

## 功能特性

- **精准定位改写范围** — 导入 Turnitin / iThenticate AI Writing Report 自动定位标红段落；未标记的内容不进入改写范围
- **原格式进、原格式出** — DOCX 处理后仍是 DOCX，PPTX 处理后仍是 PPTX，排版、表格、图片、公式原样保留，结果可继续编辑
- **保护学术结构** — 文内引用、参考文献、脚注、目录域、交叉引用、图表编号、公式和特殊排版被识别为重点保护对象
- **不靠制造错误降 AI** — 通过理解语义和重构句法改变表达，不把语法错误、拼写错误或生硬句子作为策略
- **完整处理长文** — 没有单次输入词数上限，单文件可达 100 MB，不必手工拆成多个文本框
- **免费继续降** — 仍有标红？凭新检测报告免费继续降，直到满意为止
- **目标词数控制（试验中）** — 可设定 min/max 词数区间，让改写结果落在目标范围内
- **只按实际修改量计费** — 按改写词数扣费，不按全文；失败或取消不收费；积分不过期
- **零依赖** — 一个 Python 脚本，只用标准库，Python 3.8+

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
<summary><b>CodeBuddy / WorkBuddy</b></summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.codebuddy/skills/humanpen
```

想只在某个项目里用，就克隆到项目根的 `.codebuddy/skills/humanpen`。
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
# 降低 AI 检测特征。--strategy 可选：balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# 只重写检测报告标出的段落
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf

# 限定篇幅（试验功能——限定字数会削弱降 AI 效果）。整篇区间，或对报告标出的段落逐段设区间：
python3 scripts/humanpen.py humanize paper.docx --min-words 1500 --max-words 1800
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf --segments-file budgets.json

# 对已完成任务免费继续降一次（每个任务一次）：用该任务结果的新报告，只重跑仍标红的片段
python3 scripts/humanpen.py free-rehumanize <job_id> --report new-turnitin.pdf

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

任务完成后会打印 JSON，其中 `output` 是保存路径、`credits_charged` 是花费。
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
