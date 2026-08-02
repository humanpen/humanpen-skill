# humanpen-skill

**Give Claude Code the ability to work on real documents.** A skill that lets an
agent take a `.docx`, `.pptx` or `.pdf` on disk and lower its AI-detection
score, convert its citations to another style, condense it to a word budget, or
translate it — with formatting, tables, images, citations and formulas intact.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-D97757.svg)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

English · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

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

Create one at <https://humanpen.net/settings>. New accounts get 100 free
credits — enough for a 1,000-word document. Pricing is 100 credits per 1,000
words actually processed, 10 credits minimum per job. **Failed and cancelled
jobs cost nothing.**

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
<summary><b>OpenAI Codex, and any agent that reads AGENTS.md</b></summary>

Codex has no skill loader, so tell it about the script directly. Clone
anywhere, then add to your project's `AGENTS.md`:

```markdown
## HumanPen
Document processing — lower AI-detection score, fix citations, condense,
translate — via `python3 /path/to/humanpen-skill/scripts/humanpen.py --help`.
Needs HUMANPEN_API_KEY in the environment. Each job costs credits — 100 per
1,000 words processed, 10 minimum: say so and wait for my go-ahead.
```

The commands are identical; only the way the agent is told about them differs.
</details>

Prefer an MCP server? [humanpen-mcp](https://github.com/humanpen/humanpen-mcp)
offers the same operations as tools, and works in Cursor, Windsurf, Cline,
OpenCode and Claude Desktop as well.

## Commands

```bash
# Lower AI-detection signals. --strategy: conservative | balanced | aggressive
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

**`ai_percent` can be `null`, and `null` is not zero.** A report prints `*`
instead of a number when the submission is too short to assess. Reporting that
as "0% AI" would be a claim nobody made.

## Links

- [API documentation](https://api.humanpen.net/v1/docs.md) ·
  [OpenAPI schema](https://api.humanpen.net/v1/openapi.json)
- [humanpen-mcp](https://github.com/humanpen/humanpen-mcp) — the same
  operations as an MCP server
- [humanpen.net](https://humanpen.net)

Apache-2.0
