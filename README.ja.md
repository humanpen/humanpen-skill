# humanpen-skill

**Claude Code に、実際の文書を扱う力を。** ディスク上の `.docx` / `.pptx` /
`.pdf` をエージェントが直接処理できるようにするスキルです。AI 検出スコアの低減、
引用形式の変換、指定字数への要約、翻訳——レイアウト、表、画像、引用、数式は
そのまま保たれます。

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-D97757.svg)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/python-%3E%3D3.8-3776AB.svg)](https://python.org)

[English](README.md) · [简体中文](README.zh-CN.md) · 日本語

```
/plugin marketplace add humanpen/humanpen-skill
/plugin install humanpen@humanpen
```

> *「これが論文と Turnitin レポート。指摘された箇所だけ書き直して、参考文献は
> IEEE 形式にして。」*
>
> エージェントはレポートを読み、指摘された段落だけを書き直し、引用形式を変換し、
> 2 つのファイルパスを返します。論文本文を読むことは一度もありません。

## テキストをチャットに貼り付けるのと何が違うのか

**コピーではなく、ファイルそのものを処理します。** 章をチャットに貼り付けて
返ってくるのは、ただの文章です——見出し階層も、表も、図番号も、参考文献一覧も、
数式もありません。HumanPen は文書自体を編集して文書を返すので、出力を Word で
開けば元のままの姿です。

**文書の中身はモデルのコンテキストに入りません。** スクリプトがディスクから読み、
アップロードし、書き出したパスだけを出力します。40 ページの論文でもトークンを
消費せず、会話ログに複製されることもありません。

**検出レポートで動きを指示できます。** Turnitin や iThenticate の AI Writing
レポート PDF を渡せば、指摘された箇所**だけ**を書き直し、それ以外は 1 バイトも
変えません。4 分の 1 を直すために全体を書き直すことこそ、引用と論旨が壊れる
原因です。

**1 コマンドで 1 つの仕事が完結します。** アップロード、待機、ダウンロード、
元ファイルの隣への保存まで。エージェントはコマンドを 1 つ実行し、パスと費用を
受け取るだけです。毎回 HTTP 呼び出しを組み立て、ポーリングループを自作する必要は
ありません。

**インストールするものはありません。** Python スクリプト 1 本、標準ライブラリ
のみ、Python 3.8 以上で動きます。

## API キーの取得

<https://humanpen.net/settings> で作成できます。新規アカウントには 100
クレジット（1,000 語程度の文書 1 本分）が付きます。料金は**実際に処理された**
1,000 語あたり 100 クレジット、1 ジョブの最低額は 10 クレジットです。
**失敗・キャンセルしたジョブは課金されません。**

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
<summary><b>OpenAI Codex、および AGENTS.md を読むエージェント全般</b></summary>

Codex にはスキルローダーがないため、スクリプトを直接伝えます。任意の場所に
クローンし、プロジェクトの `AGENTS.md` に次を追記してください：

```markdown
## HumanPen
文書処理（AI 検出スコア低減、引用形式変換、要約、翻訳）は
`python3 /path/to/humanpen-skill/scripts/humanpen.py --help` から。
環境変数 HUMANPEN_API_KEY が必要。各ジョブはクレジットを消費する——実処理
1,000 語あたり 100、最低 10。必ず伝えてから、私の承認を待つこと。
```

コマンドは同一で、違うのは「エージェントへの伝え方」だけです。
</details>

MCP サーバーの方がよい場合は
[humanpen-mcp](https://github.com/humanpen/humanpen-mcp) が同じ機能を提供し、
Cursor、Windsurf、Cline、OpenCode、Claude Desktop でも動作します。

## コマンド

```bash
# AI 検出の特徴を弱める。--strategy: conservative | balanced | aggressive
python3 scripts/humanpen.py humanize paper.docx --strategy balanced

# 検出レポートが指摘した箇所だけを書き直す
python3 scripts/humanpen.py humanize paper.docx --report turnitin.pdf

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

**`ai_percent` は `null` になりえます。そして `null` は 0 ではありません。**
提出文が短すぎて評価できない場合、レポートは数値ではなく `*` を出力します。
これを「AI 率 0%」と報告するのは、誰もしていない主張をすることになります。

## リンク

- [API ドキュメント](https://api.humanpen.net/v1/docs.md) ·
  [OpenAPI スキーマ](https://api.humanpen.net/v1/openapi.json)
- [humanpen-mcp](https://github.com/humanpen/humanpen-mcp) — 同じ機能を
  MCP サーバーとして
- [humanpen.net](https://humanpen.net)

Apache-2.0
