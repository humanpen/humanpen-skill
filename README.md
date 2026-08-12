# humanpen-skill

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent_Skills-open_standard-6E56CF.svg)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

English · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[Website](https://humanpen.net) · [Pricing](https://humanpen.net/pricing) · [Developer docs](https://humanpen.net/developers)

> **Keywords:** ai humanizer, agent skill, turnitin ai detection, reduce ai score, humanize ai text, bypass ai detection, docx ai humanizer, ai content rewriter, ai writing tool, claude code skill, codex skill, ithenticate ai report

**Humanize what's flagged. Preserve the rest.** An [Agent Skill](https://agentskills.io) for [HumanPen](https://humanpen.net) — a document-level AI humanizer that can humanize an entire document, rewrite user-selected passages, or automatically target flagged text from a Turnitin / iThenticate AI-detection report, editing `.docx` / `.pptx` files in place while preserving formatting, tables, images, citations, and formulas. Also converts citations between 12 styles, condenses to a word budget, and translates between 12 languages.

## Features

- **Selective rewriting by detection report** — import a Turnitin / iThenticate AI Writing Report to pinpoint flagged passages; unflagged content is never touched
- **Format in, format out** — a DOCX comes back as a DOCX, a PPTX as a PPTX; formatting, tables, images, and formulas survive intact and the result is still editable
- **Academic structure preserved** — in-text citations, reference lists, footnotes, TOC fields, cross-references, figure numbering, equations, and special formatting are treated as protected objects
- **No error injection** — restructures meaning and syntax to change expression; never adds grammar mistakes, spelling errors, or awkward sentences as a detection strategy
- **Full-length documents** — no per-input word limit; a single file can be up to 100 MB, no splitting into text boxes
- **Free to keep going** — still flagged? Re-humanize for free with a fresh report until the AI rate falls to `*` or 0%
- **Word-count control (experimental)** — set a min/max word range to keep the output within a target length
- **Pay per rewrite** — billed on words actually changed, not the whole document; failed and cancelled jobs cost nothing; credits never expire
- **Nothing to install** — one Python script, standard library only, Python 3.8+

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

# Constrain length (EXPERIMENTAL - a word limit weakens AI-rate reduction).
# Whole document, or per-passage budgets for the report's flagged passages:
python3 scripts/humanpen.py humanize paper.docx --min-words 1500 --max-words 1800
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf --segments-file budgets.json

# Continue a finished job for FREE (once per job): re-run its still-flagged
# passages with a fresh report for that job's result
python3 scripts/humanpen.py free-rehumanize <job_id> --report new-turnitin.pdf

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
