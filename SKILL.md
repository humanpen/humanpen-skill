---
name: humanpen
description: Humanize document files with HumanPen to lower their AI-detection score. Rewrite a whole .docx/.pptx, or only the passages a Turnitin/iThenticate AI report flagged, while keeping every fact, number, citation, table and formula intact. Also converts citations to one style (APA, MLA, IEEE, GB/T 7714), condenses a document to a word budget, and translates while preserving layout. Use when the user points at a document FILE (.docx/.pptx; translate also takes .pdf/.xlsx/.epub/.html/.txt) or such an AI report and wants any of these; not for text pasted into chat. Also hands a whole research, data analysis or writing task, with its files, to HumanPen's cloud agents (`project` commands).
license: Apache-2.0
---

# HumanPen

A document-level AI humanizer. Point it at a document file and it uploads the file, waits for the job, and writes the result next to the source — you get a path back, **never the document's contents**. Formatting, tables, images, citations, and formulas survive intact.

**Every job spends the account's credits. State the cost and get the user's agreement before running any job command.** Per 1,000 words processed: humanize 100 credits, fix-citations 5, condense 20, translate 10, charged only on the words actually processed, with a 10-credit minimum per job; failed or cancelled jobs cost nothing.

## Setup

```bash
export HUMANPEN_API_KEY=hp_...   # create one at https://humanpen.net/settings/api-keys
```

New accounts get 100 free credits at https://humanpen.net. Without a key every command fails with instructions to get one.

## Commands

Run from this skill's directory; `python3` and nothing else is needed. `--help` on any command lists its flags. Add `-o PATH` to choose where the result lands (default `<name>-polished.docx` beside the source).

### Humanize — the main operation

Lower AI-detection signals on a `.docx` / `.pptx`. Three ways to scope it:

```bash
# 1. Whole document.  --strategy: balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# 2. Only the passages a Turnitin / iThenticate report flagged — the rest is left untouched
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf
#    Or only passages you choose: a JSON list of their exact texts
python3 scripts/humanpen.py humanize paper.docx --segments-file passages.json

# 3. Continue a finished job for FREE (once per job): re-runs its still-flagged
#    passages against a fresh report. Pass the job_id that humanize returned.
python3 scripts/humanpen.py free-rehumanize <job_id> --report new-turnitin.pdf
```

Optional length control — EXPERIMENTAL, a word limit noticeably weakens AI-rate reduction, so skip it unless a length is required:

```bash
python3 scripts/humanpen.py humanize paper.docx --min-words 1500 --max-words 1800
# Per-passage budgets for the report's flagged passages:
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf --segments-file budgets.json
```

### The other three operations

```bash
# Convert every citation + the reference list to one style.  --style: apa7 |
#   mla9 | harvard | chicago_author_date | chicago_notes | ieee | vancouver |
#   gbt7714 | gbt7714_author_year | ama | acs | oscola
python3 scripts/humanpen.py fix-citations paper.docx --style apa7

# Shorten the whole document to a word budget, or only chosen passages
#   (--segments-file: [{"text": ..., "max_words": N}]).  --mode delete drops whole
#   low-value sentences and keeps every other word verbatim (default: rewrite)
python3 scripts/humanpen.py condense paper.docx --max-words 4000

# Translate, keeping layout, tables and formulas.  --to: zh | zh-tw | en | ja |
#   ko | es | fr | pt | ru | de | pl | it   (--source-lang: same codes, default auto)
python3 scripts/humanpen.py translate paper.docx --to zh
```

### Read a report · manage jobs · check credits

```bash
# A Turnitin / iThenticate report: overall AI %, and the flagged passages
python3 scripts/humanpen.py report turnitin.pdf

# Pick a running job back up (optionally download its result); show the balance
python3 scripts/humanpen.py status <job_id> --download paper.docx
python3 scripts/humanpen.py balance

# List jobs; cancel a queued or running one (its credits come back); run a
#   failed or cancelled one again (spends credits)
python3 scripts/humanpen.py jobs
python3 scripts/humanpen.py cancel <job_id>
python3 scripts/humanpen.py retry <job_id> --download paper.docx
```

### Research projects — a whole task for the cloud agents

For a research, data analysis or writing task rather than one document to rewrite: the agents scope it with the user, propose a plan, do the work, have it reviewed and deliver files. The key must have been created with **Research projects** ticked.

```bash
python3 scripts/humanpen.py project start "<the user's request>" --file data.csv   # prints project_id, after_seq
python3 scripts/humanpen.py project wait <project_id> --after <after_seq>          # until it needs the user or is done
python3 scripts/humanpen.py project act <project_id> confirm_plan --spec-version 1 # or: answer --answers '{"q1": "..."}'
python3 scripts/humanpen.py project download <project_id> -o out/                  # the delivery, as a zip
python3 scripts/humanpen.py project rename <project_id> "<new name>"               # or name it with --title on start
```

**Confirming a plan spends credits (charged by use): show the user the plan that `project wait` prints (it is charged by what it uses; there is no price up front) and confirm only with their agreement** — unless they set a cap: `project start ... --max-credits N --auto-confirm --answer-recommended` then runs unattended within it. `project show <id>` re-reads where it stands; `project message <id> "..."` asks for changes after a delivery (a new round); while the agents work they read it after the step they are on, and `--now` interrupts that step for an urgent correction.

## Reading the output

A finished job prints JSON. Report its `output` (the result path) and `credits_charged` (the cost) to the user. **Do not read the produced file back to summarise it** unless asked — it is a full document, and the point of the path is that its contents stay out of the conversation.

`report` and a finished humanize print `ai_percent` as a number — or `null` when the report shows `*`. Turnitin prints `*` whenever AI writing is **under 20%**; it will not quantify that band, because of false positives. So `null` is usually good news, not a missing result. **It is never zero**: report it as "under 20%, which is where Turnitin stops printing a number", never "0% AI".

## Worth knowing

- **Formats.** humanize takes `.docx` / `.pptx`; fix-citations and condense take `.docx`; translate additionally takes `.pdf`, `.xlsx`, `.pptx`, `.epub`, `.html` and `.txt`.
- **Minutes, not seconds.** The command waits and prints progress to stderr. Interrupting it does **not** cancel the job — `status <job_id>` picks it back up.
- **A second pass is the plan, not a failure — and it is free.** If a detector still flags the result, `free-rehumanize <job_id>` with a fresh report rewrites only the still-flagged passages, at no credit cost (once per job, with a daily cap). Keep `balanced`; no need to escalate to `aggressive`.
- **A paragraph is the smallest unit.** A chosen or flagged passage is widened to its whole paragraph, and billed as such.
- **Result files are kept 7 days**, then deleted; the job record stays.
