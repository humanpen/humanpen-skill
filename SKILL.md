---
name: humanpen
description: Process document files with HumanPen - lower AI-detection scores on a Word/PowerPoint file, convert citations to APA/MLA/IEEE/GB-T 7714, condense a document to a word budget, or translate one while keeping its layout. Also reads Turnitin and iThenticate AI reports to get the overall AI percentage and the flagged passages. Use when the user points at a document FILE (.docx/.pptx/.pdf) and wants any of these; not for text pasted into chat.
license: Apache-2.0
---

# HumanPen

Four document operations behind one API. Every command uploads the file,
waits for the job, and writes the result next to the source - you get a
path back, never the document's contents.

Each run spends the account's credits. **Say what it will cost and get the
user's agreement before running any of the four job commands.** 1,000 words
costs 100 credits, charged only on the words actually processed, with a
10-credit minimum per job.

## Setup

```bash
export HUMANPEN_API_KEY=hp_...   # create one at https://humanpen.net/settings/api-keys
```

New accounts get 100 free credits at https://humanpen.net. Without a key
every command fails with instructions to get one.

## Commands

Run them from this skill's directory; `python3` and nothing else is needed.

```bash
# Lower AI-detection signals. --strategy: balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# Rewrite only the passages a detection report flagged, leaving the rest alone
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf

# Constrain length. EXPERIMENTAL - a word limit noticeably weakens AI-rate
# reduction, so skip it unless a length is required. Whole document:
python3 scripts/humanpen.py humanize paper.docx --min-words 1500 --max-words 1800
# Per-passage: bound only the report's flagged passages (texts from `report`)
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf --segments-file budgets.json

# Citations and the reference list to one style
python3 scripts/humanpen.py fix-citations paper.docx --style apa7

# Shorten the whole document to a word budget
python3 scripts/humanpen.py condense paper.docx --max-words 4000

# Translate, keeping layout, tables and formulas
python3 scripts/humanpen.py translate paper.docx --to zh

# Read a Turnitin/iThenticate report: overall AI %, and the flagged passages
python3 scripts/humanpen.py report turnitin.pdf

# A job you left running, and the balance
python3 scripts/humanpen.py status <job_id> --download paper.docx
python3 scripts/humanpen.py balance
```

`--help` on any command lists its flags. Add `-o PATH` to choose where the
result lands; the default is `<name>-polished.docx` beside the source.

## Reading the output

A finished job prints JSON:

```json
{
  "job_id": "8f14…",
  "operation": "humanize",
  "status": "DONE",
  "credits_charged": 118,
  "source_words": 1180,
  "result_words": 1150,
  "output": "/path/paper-polished.docx"
}
```

Report the `output` path and `credits_charged` to the user. Do not read the
produced file back to summarise it unless asked - it is a full document, and
the point of the path is that its contents stay out of the conversation.

`report` prints `ai_percent` as a number, or `null` when the report shows
`*` or states no figure. Turnitin prints `*` whenever AI writing is **under
20%** - it will not quantify that band because of false positives - so `null`
is usually good news, not a missing result. **It is never zero**: report it as
"under 20%, which is where Turnitin stops printing a number", never as "0% AI".

## Notes worth knowing

- **Formats**: humanize takes .docx and .pptx; the others take .docx, and
  translate additionally takes .pdf, .xlsx, .pptx, .epub, .html and .txt.
- **Minutes, not seconds.** The command waits and prints progress to stderr.
  Interrupting it does not cancel the job - `status <job_id>` picks it back up.
- **Failures cost nothing.** A job that errors or is cancelled is charged 0.
- **Result files are kept 7 days**, then deleted; the job record stays.
- **A second pass is the plan, not a failure.** If a detector still flags the
  result, humanize the rewritten file again with its new report via `--report`:
  only the passages still marked get rewritten, and the rest stays put. Keep
  `balanced` for the second pass too - no need to escalate to `aggressive`.
