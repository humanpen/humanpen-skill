# humanpen-skill

**Give your AI agent the ability to work on real documents.** An
[Agent Skill](https://agentskills.io) for [HumanPen](https://humanpen.net).
Point Claude Code, Codex, Cursor, Gemini CLI or any of 40+ other clients at a
`.docx`, `.pptx` or `.pdf` on disk, and it can lower the file's AI-detection
score, convert its citations to another style, condense it to a word budget, or
translate it — formatting, tables, images, citations and formulas intact.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent_Skills-open_standard-6E56CF.svg)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

English · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[Website](https://humanpen.net) · [Pricing](https://humanpen.net/pricing) · [Developer docs](https://humanpen.net/developers)

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```

> *"Here's my thesis and the Turnitin report — rewrite just the flagged parts,
> then put the references in IEEE style."*
>
> The agent reads the report, rewrites only the passages it marked, converts the
> citations, and hands back two file paths. It never had to read the thesis.

## Why this instead of pasting text into the chat

**It works on the file, not on a copy of the text.** Paste a chapter into a chat
and you get prose back — no headings, no tables, no figure numbering, no
reference list, no equations. HumanPen edits the document itself and returns a
document, so what comes out still opens in Word looking like what went in.

**The document never enters the model's context.** The script reads the file
from disk, uploads it, and prints the path it wrote. A 40-page paper costs you
no tokens and is not copied into a transcript.

**It can be guided by a detection report.** Give it the Turnitin or iThenticate
AI Writing PDF and it rewrites *only* the passages that report flagged, leaving
everything else byte-identical. Rewriting a whole document to fix a quarter of
it is how citations and meaning get damaged.

**One command is one finished job.** Upload, wait, download, saved next to the
source — the agent runs a command and reads back a path and a cost, instead of
assembling HTTP calls and writing its own polling loop each time.

**Nothing to install.** One Python script, standard library only, Python 3.8+.

## Get a key

Sign up at <https://humanpen.net> and create a key at
<https://humanpen.net/settings/api-keys>. New accounts start with free credits,
enough to put a document through and see what comes back.

```bash
export HUMANPEN_API_KEY=hp_your_key
```

Or copy `.env.example` to `.env` in this directory — it is gitignored.

## Install

<details open>
<summary><b>Claude Code</b> (plugin)</summary>

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```
</details>

<details>
<summary><b>Claude Code</b> (manual)</summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.claude/skills/humanpen
```

Project-scoped instead? Clone into `.claude/skills/humanpen` in the repo.
</details>

<details>
<summary><b>OpenAI Codex</b></summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.agents/skills/humanpen
```

Codex also reads `.agents/skills/` inside a repository, if you would rather
scope it to one project.
</details>

<details>
<summary><b>CodeBuddy / WorkBuddy</b></summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.codebuddy/skills/humanpen
```

Project-scoped: clone into `.codebuddy/skills/humanpen` at the project root.
</details>

<details>
<summary><b>Cursor, Gemini CLI, OpenCode, Copilot, Goose, Amp, Kiro, and 35+ more</b></summary>

This is a plain [Agent Skill](https://agentskills.io): a folder with a
`SKILL.md` in it. Every client that implements the standard loads the same
folder — only the directory it scans differs, and each documents its own. Clone
the repository into that directory and the skill is installed.

```bash
git clone https://github.com/humanpen/humanpen-skill
```
</details>

Prefer an MCP server? [humanpen-mcp](https://github.com/humanpen/humanpen-mcp)
offers the same operations as tools, and works in Cursor, Windsurf, Cline,
OpenCode and Claude Desktop as well.

## Commands

```bash
# Lower AI-detection signals. --strategy: balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# Rewrite only the passages a detection report flagged
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf

# Citations and reference list to one style
python3 scripts/humanpen.py fix-citations paper.docx --style apa7

# Shorten to a word budget
python3 scripts/humanpen.py condense paper.docx --max-words 4000

# Translate, keeping layout
python3 scripts/humanpen.py translate paper.docx --to zh

# Read a Turnitin/iThenticate report: overall AI %, flagged passages
python3 scripts/humanpen.py report turnitin.pdf

# A job left running, and the balance
python3 scripts/humanpen.py status <job_id> --download paper.docx
python3 scripts/humanpen.py balance
```

A finished job prints JSON with `output` (where the file landed) and
`credits_charged` (what it cost). `--help` on any command lists its flags.

Citation styles: APA 7, MLA 9, Harvard, Chicago (both), IEEE, Vancouver,
GB/T 7714, AMA, ACS, OSCOLA. Translation covers 12 languages.

## Two things worth knowing

**Jobs take minutes.** The command waits, printing progress to stderr.
Interrupting it does not cancel the job — `status <job_id>` picks it back up.

**`ai_percent` can be `null`, and that is usually good news.** Turnitin prints
`*` instead of a number whenever AI writing comes in **under 20%** — it will not
quantify that band, because too much of it is false positives. So `null` means
"under 20%, and Turnitin will say no more", never "0%" and never "no result".

## Questions people ask

**Will this bring a Turnitin AI score down?**
Usually under 20% in one pass with `balanced` — the threshold below which
Turnitin prints `*` instead of a number. If it misses, run the result back
through with the new report; only the passages still flagged get rewritten.

**Does it work with iThenticate too?**
Yes — pass either report. The format is read from the file.

**Is my document sent to the model?**
No. It uploads the file and prints a path. A 40-page paper costs no tokens.

## Links

- [API documentation](https://api.humanpen.net/v1/docs.md) ·
  [OpenAPI schema](https://api.humanpen.net/v1/openapi.json)
- [humanpen-mcp](https://github.com/humanpen/humanpen-mcp) — the same
  operations as an MCP server
- [humanpen.net](https://humanpen.net)

Apache-2.0
