# humanpen-skill

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent_Skills-open_standard-6E56CF.svg)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

[English](README.md) · [简体中文](README.zh-CN.md) · 日本語

[公式サイト](https://humanpen.net) · [料金](https://humanpen.net/pricing) · [開発者ドキュメント](https://humanpen.net/developers)

> **キーワード:** AI ヒューマナイザー, Agent Skill, Turnitin AI 検出, AI 検出スコア低減, DOCX AI 書き換え, AI 検出回避, Claude Code スキル, Codex スキル

**指摘された箇所だけ書き直す。フォーマットはそのまま。** [HumanPen](https://humanpen.net) の [Agent Skill](https://agentskills.io)——文書レベルの AI ヒューマナイザーです。文書全体の AI 率低減、ユーザー指定箇所の書き直し、Turnitin / iThenticate の AI 率検出レポートに基づく指摘箇所の自動特定と書き直しに対応し、`.docx` / `.pptx` のレイアウト、表、画像、引用、数式をそのまま保持します。12 種の引用形式変換、語数指定の要約、12 言語間の翻訳にも対応します。

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```

## 特長

- **検出レポートで改写範囲を特定** — Turnitin / iThenticate の AI Writing レポートを読み込み、指摘された段落だけを書き直します。指摘のない部分は一切触れません
- **元のフォーマットで入り、元のフォーマットで返る** — DOCX は DOCX のまま、PPTX は PPTX のまま。レイアウト、表、画像、数式はそのまま保持され、結果はそのまま編集できます
- **学術構造を保護** — 文中引用、参考文献、脚注、目次フィールド、相互参照、図表番号、数式、特殊書式は保護対象として扱われます
- **エラー注入なし** — 意味と構文を再構成して表現を変えます。文法ミスやスペルミス、不自然な文を検出回避の手段にはしません
- **長文をそのまま処理** — 入力語数の上限なし。1 ファイル最大 100 MB、テキストボックスに分割する必要はありません
- **無料で何度でも** — まだ指摘が残っていれば、AI 率が `*` または 0% になるまで、新しいレポートで無料で再実行できます
- **語数コントロール（試験的）** — min/max の語数範囲を指定し、仕上がりを目標内に収められます
- **書き直した分だけ課金** — 実際に変更された語数で課金。文書全体ではありません。失敗・キャンセルは無料。クレジットに有効期限なし
- **依存ゼロ** — Python スクリプト 1 本、標準ライブラリのみ、Python 3.8+

## API キーの取得

<https://humanpen.net> で登録し、<https://humanpen.net/settings/api-keys> で
キーを作成します。新規アカウントには無料クレジットが付くので、文書を 1 本
通して結果を確かめられます。

```bash
export HUMANPEN_API_KEY=hp_your_key
```

または、このディレクトリの `.env.example` を `.env` にコピーしてください
（gitignore 済みです）。

## インストール

<details open>
<summary><b>Claude Code</b>（プラグイン）</summary>

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```
</details>

<details>
<summary><b>Claude Code</b>（手動）</summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.claude/skills/humanpen
```

プロジェクト単位で使う場合は、そのリポジトリの `.claude/skills/humanpen` に
クローンしてください。
</details>

<details>
<summary><b>OpenAI Codex</b></summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.agents/skills/humanpen
```

Codex はリポジトリ内の `.agents/skills/` も読みます。プロジェクト単位で使う
場合はそちらへ。
</details>

<details>
<summary><b>CodeBuddy / WorkBuddy</b></summary>

```bash
git clone https://github.com/humanpen/humanpen-skill ~/.codebuddy/skills/humanpen
```

プロジェクト単位で使う場合は、プロジェクト直下の `.codebuddy/skills/humanpen` へ。
</details>

<details>
<summary><b>Cursor、Gemini CLI、OpenCode、Copilot、Goose、Amp、Kiro ほか 35 以上</b></summary>

これは標準的な [Agent Skill](https://agentskills.io)——`SKILL.md` を含むただの
フォルダです。標準に対応したクライアントはすべて同じフォルダを読み込み、違いは
走査するディレクトリだけで、各製品のドキュメントに記載されています。そのディレクトリ
にクローンすればインストール完了です。

```bash
git clone https://github.com/humanpen/humanpen-skill
```
</details>

MCP サーバーの方がよい場合は
[humanpen-mcp](https://github.com/humanpen/humanpen-mcp) が同じ機能を提供し、
Cursor、Windsurf、Cline、OpenCode、Claude Desktop でも動作します。

## コマンド

```bash
# AI 検出の特徴を弱める。--strategy: balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# 検出レポートが指摘した箇所だけを書き直す
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf

# 文字数を制限（試験的機能——文字数の制限は AI 率低減の効果を弱めます）。
# 全体の範囲、またはレポートが指摘した段落ごとの範囲：
python3 scripts/humanpen.py humanize paper.docx --min-words 1500 --max-words 1800
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf --segments-file budgets.json

# 完了済みジョブを無料で続行（ジョブごとに1回）：その結果の新しいレポートで、まだ指摘された箇所だけを再実行
python3 scripts/humanpen.py free-rehumanize <job_id> --report new-turnitin.pdf

# 文中引用と参考文献一覧を指定の形式へ
python3 scripts/humanpen.py fix-citations paper.docx --style apa7

# 目標字数まで短縮
python3 scripts/humanpen.py condense paper.docx --max-words 4000

# レイアウトを保ったまま翻訳
python3 scripts/humanpen.py translate paper.docx --to zh

# Turnitin / iThenticate レポートを読む：全体の AI 率と指摘箇所
python3 scripts/humanpen.py report turnitin.pdf

# 実行中のジョブと残高
python3 scripts/humanpen.py status <job_id> --download paper.docx
python3 scripts/humanpen.py balance
```

完了したジョブは JSON を出力します。`output` が保存先、`credits_charged` が
費用です。各サブコマンドに `--help` を付ければ引数一覧が出ます。

対応する引用形式：APA 7、MLA 9、Harvard、Chicago（2 種）、IEEE、Vancouver、
GB/T 7714、AMA、ACS、OSCOLA。翻訳は 12 言語に対応します。

## 知っておくとよい 2 点

**ジョブは分単位です。** コマンドは待機し、進捗を stderr に出力します。コマンドを
中断してもジョブはキャンセルされません——`status <job_id>` で再び拾えます。

**`ai_percent` が `null` になるのは、多くの場合よい知らせです。** AI 検出率が
**20% を下回る**とき、Turnitin は数値ではなく `*` を出力します。その区間は
誤検出が多すぎるため、数値を出さない方針だからです。つまり `null` は「20% 未満、
Turnitin はそれ以上言わない」であって、0 でも「結果なし」でもありません。

## よくある質問

**Turnitin の AI 率は下がりますか。**
`balanced` なら通常 1 回で 20% 未満——Turnitin が数値をやめて `*` を出す境目——
まで下がります。届かなければ、結果と新しいレポートをもう一度渡せば、まだ指摘の
ある箇所だけが書き直されます。

**iThenticate のレポートにも対応していますか。**
はい。どちらも渡せます。形式はファイルから判別します。

**文書はモデルのコンテキストに送られますか。**
いいえ。ファイルをアップロードし、パスを返すだけです。40 ページの論文でも
トークンは消費しません。

## リンク

- [API ドキュメント](https://api.humanpen.net/v1/docs.md) ·
  [OpenAPI スキーマ](https://api.humanpen.net/v1/openapi.json)
- [humanpen-mcp](https://github.com/humanpen/humanpen-mcp) — 同じ機能を
  MCP サーバーとして
- [humanpen.net](https://humanpen.net)

Apache-2.0
