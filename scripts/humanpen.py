#!/usr/bin/env python3
"""HumanPen document processing from the command line.

One command per operation, each carrying the whole job through: upload the
document, wait for it, download the result next to the source. The agent
calling this never handles multipart bodies, polling loops, or presigned
URLs - and never sees the document bytes, which would cost a fortune in
context for no benefit.

Standard library only, so it runs wherever Python 3.8+ does with nothing
installed.

    export HUMANPEN_API_KEY=hp_...
    python humanpen.py humanize paper.docx --strategy balanced
    python humanpen.py translate paper.docx --to zh
    python humanpen.py report turnitin.pdf
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import uuid
from pathlib import Path
from urllib import error, request

DEFAULT_BASE_URL = 'https://api.humanpen.net/v1'
SIGNUP_URL = 'https://humanpen.net'
KEYS_URL = 'https://humanpen.net/settings/api-keys'

# Jobs run for minutes, so poll gently and back off - the API asks for this
# and a tight loop only burns rate limit.
POLL_FIRST_SECONDS = 3
POLL_MAX_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 1800

class HumanPenError(Exception):
    """A failure worth showing the user verbatim."""

    def __init__(self, message: str, *, code: str = '', retryable: bool = False):
        super().__init__(message)
        self.code = code
        # Told apart so a caller knows whether trying again could possibly
        # help: a network blip can be retried, "not enough credits" cannot.
        self.retryable = retryable


def _api_key() -> str:
    """Return the configured key, or explain where to get one."""

    key = (os.environ.get('HUMANPEN_API_KEY') or '').strip()
    if key:
        return key
    env_file = Path(__file__).resolve().parent.parent / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            name, _, value = line.partition('=')
            if name.strip() == 'HUMANPEN_API_KEY' and value.strip():
                return value.strip().strip('"').strip("'")
    raise HumanPenError(
        'No API key. Create one at ' + KEYS_URL + ' (sign up at ' + SIGNUP_URL
        + ' - new accounts get 100 free credits), then:\n'
        '  export HUMANPEN_API_KEY=hp_...',
        code='NO_API_KEY',
    )


def _base_url() -> str:
    return (os.environ.get('HUMANPEN_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')


def _encode_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    """Encode form fields and file parts into one multipart body.

    Args:
        fields: plain text fields
        files: name -> (filename, bytes, content type)
    Returns:
        tuple: (body, content type header)
    """
    boundary = f'----humanpen{uuid.uuid4().hex}'
    parts: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, payload, content_type) in files.items():
        parts.append(
            (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
             f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n').encode()
            + payload + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def _request(
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    content_type: str | None = None,
    absolute_url: str | None = None,
    authenticated: bool = True,
) -> dict:
    """Call the API and unwrap its envelope, or raise a readable error."""

    url = absolute_url or f'{_base_url()}{path}'
    req = request.Request(url, method=method, data=body)
    if authenticated:
        req.add_header('Authorization', f'Bearer {_api_key()}')
    # Identifies the caller in HumanPen's logs, which is what a support
    # question gets answered from.
    req.add_header('User-Agent', 'humanpen-skill/1.0')
    if content_type:
        req.add_header('Content-Type', content_type)
    try:
        with request.urlopen(req, timeout=300) as response:
            payload = json.loads(response.read())
    except error.HTTPError as exc:
        raw = exc.read()
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            envelope = {}
        code = str(envelope.get('code') or '')
        message = str(envelope.get('message') or exc.reason or 'request failed')
        if exc.code == 401:
            message = f'{message} - check HUMANPEN_API_KEY, or create a key at {KEYS_URL}'
        elif exc.code == 402:
            message = f'{message} - top up at {SIGNUP_URL}/pricing'
        # 429 and 5xx are the only ones where waiting changes the answer.
        raise HumanPenError(
            f'HTTP {exc.code} {code}: {message}',
            code=code,
            retryable=exc.code == 429 or exc.code >= 500,
        ) from exc
    except error.URLError as exc:
        raise HumanPenError(f'cannot reach {url}: {exc.reason}', retryable=True) from exc
    return payload.get('data', payload)


def _read_document(path_text: str) -> tuple[str, bytes, str]:
    """Read a local document into a multipart file part."""

    path = Path(path_text).expanduser()
    if not path.is_file():
        raise HumanPenError(f'no such file: {path}', code='FILE_NOT_FOUND')
    content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return path.name, path.read_bytes(), content_type


def create_job(operation: str, document: str, fields: dict) -> dict:
    """Submit one document and return the receipt."""

    filename, payload, content_type = _read_document(document)
    files = {'file': (filename, payload, content_type)}
    report = fields.pop('_report_path', None)
    if report:
        report_name, report_payload, _ = _read_document(report)
        files['turnitin_file'] = (report_name, report_payload, 'application/pdf')
    body, header = _encode_multipart(fields, files)
    return _request('POST', f'/jobs/{operation}', body=body, content_type=header)


def wait_for_job(job_id: str, *, timeout_seconds: float, quiet: bool = False) -> dict:
    """Poll until the job reaches a terminal state.

    Watches the ``finished`` flag rather than enumerating statuses, so a
    status value added later cannot strand this loop.
    """

    deadline = time.monotonic() + timeout_seconds
    delay = POLL_FIRST_SECONDS
    while True:
        try:
            job = _request('GET', f'/jobs/{job_id}')
        except HumanPenError as exc:
            # A blip while polling says nothing about the job, which is running
            # on a server somewhere regardless. Abandoning the wait over one
            # lost packet would strand work already paid for.
            if not exc.retryable or time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 2, POLL_MAX_SECONDS)
            continue
        if not quiet:
            print(f'  {job["status"]} {job["progress_percent"]}%', file=sys.stderr)
        if job.get('finished'):
            return job
        if time.monotonic() >= deadline:
            raise HumanPenError(
                f'job {job_id} still running after {timeout_seconds:.0f}s; '
                f'check later with: humanpen.py status {job_id}',
                code='TIMEOUT',
                retryable=True,
            )
        time.sleep(delay)
        delay = min(delay * 2, POLL_MAX_SECONDS)


def download_result(job: dict, source: str, output: str | None) -> Path:
    """Save the produced document beside the source, or where asked."""

    result = job.get('result') or {}
    url = result.get('download_url')
    if not url:
        raise HumanPenError('the finished job carries no result file', code='NO_RESULT')
    source_path = Path(source).expanduser()
    # The API names the result after the document it came from, so there is no
    # second naming scheme here to keep in step with it.
    default_name = result.get('filename') or source_path.name
    if output:
        target = Path(output).expanduser()
        if target.is_dir():
            target = target / default_name
    else:
        target = source_path.with_name(default_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A presigned link: plain GET, no Authorization header, short-lived.
    with request.urlopen(url, timeout=300) as response:
        target.write_bytes(response.read())
    return target


def report_job(job: dict, output: Path | None) -> None:
    """Print what the job cost and produced."""

    credits = job.get('credits') or {}
    source = job.get('source') or {}
    result = job.get('result') or {}
    print(json.dumps({
        'job_id': job.get('job_id'),
        'operation': job.get('operation'),
        'status': job.get('status'),
        'credits_charged': credits.get('charged'),
        'source_words': source.get('words'),
        'result_words': result.get('words'),
        'output': str(output) if output else None,
    }, ensure_ascii=False, indent=2))


def run_operation(operation: str, args, fields: dict) -> int:
    """Submit, wait, download, report - the whole job in one call."""

    receipt = create_job(operation, args.document, fields)
    print(f'job {receipt["job_id"]} created, {receipt["credits_frozen"]} credits reserved',
          file=sys.stderr)
    if args.no_wait:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    job = wait_for_job(receipt['job_id'], timeout_seconds=args.timeout)
    if job.get('status') != 'DONE':
        failure = job.get('error') or {}
        raise HumanPenError(
            f'job {job.get("status")}: {failure.get("message") or "no detail"}',
            code=str(failure.get('code') or ''),
        )
    output = download_result(job, args.document, args.output)
    report_job(job, output)
    return 0


def cmd_humanize(args) -> int:
    return run_operation('humanize', args, {
        'strategy': args.strategy,
        'additional_instructions': args.instructions,
        '_report_path': args.report,
    })


def cmd_citations(args) -> int:
    return run_operation('citation-format-correction', args, {
        'citation_style': args.style,
        'additional_instructions': args.instructions,
    })


def cmd_condense(args) -> int:
    return run_operation('condense', args, {
        'max_words': args.max_words,
        'additional_instructions': args.instructions,
    })


def cmd_translate(args) -> int:
    return run_operation('translate', args, {
        'source_lang': args.source_lang,
        'target_lang': args.to,
    })


def cmd_report(args) -> int:
    """Read an AI-detection report without starting a job."""

    filename, payload, _ = _read_document(args.report)
    body, header = _encode_multipart(
        {'type': args.type}, {'file': (filename, payload, 'application/pdf')})
    parsed = _request('POST', '/detect-reports/parse', body=body, content_type=header)
    print(json.dumps({
        'report_type': parsed.get('report_type'),
        'ai_percent': parsed.get('ai_percent'),
        'segment_count': parsed.get('segment_count'),
        'page_count': parsed.get('page_count'),
        'segments': parsed.get('segments'),
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args) -> int:
    job = _request('GET', f'/jobs/{args.job_id}')
    output = None
    if args.download and job.get('status') == 'DONE':
        output = download_result(job, args.download, args.output)
    report_job(job, output)
    return 0


def cmd_balance(args) -> int:
    balance = _request('GET', '/credits/balance')
    print(json.dumps(balance, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI, one subcommand per operation."""

    parser = argparse.ArgumentParser(
        prog='humanpen.py',
        description='Process documents with HumanPen: humanize, fix citations, condense, translate.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    def add_job_flags(sub):
        sub.add_argument('document', help='path to the document to process')
        sub.add_argument('-o', '--output', help='where to write the result (default: beside the source)')
        sub.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT_SECONDS,
                         help='seconds to wait before giving up on the job')
        sub.add_argument('--no-wait', action='store_true',
                         help='submit and print the receipt without waiting')
        return sub

    humanize = add_job_flags(subparsers.add_parser(
        'humanize', help='reduce AI-detection signals, keeping meaning and formatting'))
    humanize.add_argument('--strategy', default='balanced',
                          choices=['balanced', 'aggressive'],
                          help='rewriting intensity (default: balanced)')
    humanize.add_argument('--report', help='Turnitin/iThenticate AI report PDF; only its '
                                           'flagged passages are rewritten')
    humanize.add_argument('--instructions', help='extra requirements for this job')
    humanize.set_defaults(func=cmd_humanize)

    citations = add_job_flags(subparsers.add_parser(
        'fix-citations', help='convert in-text citations and the reference list to one style'))
    citations.add_argument('--style', required=True,
                           help='target style, e.g. apa7, mla9, ieee, gbt7714')
    citations.add_argument('--instructions', help='extra requirements for this job')
    citations.set_defaults(func=cmd_citations)

    condense = add_job_flags(subparsers.add_parser(
        'condense', help='shorten a document to a word budget'))
    condense.add_argument('--max-words', dest='max_words', required=True, type=int,
                          help='target word count for the whole document')
    condense.add_argument('--instructions', help='extra requirements for this job')
    condense.set_defaults(func=cmd_condense)

    translate = add_job_flags(subparsers.add_parser(
        'translate', help='translate a document, keeping its formatting'))
    translate.add_argument('--to', required=True, help='target language, e.g. zh, en, ja')
    translate.add_argument('--source-lang', dest='source_lang', default='auto',
                           help='source language (default: auto)')
    translate.set_defaults(func=cmd_translate)

    report = subparsers.add_parser(
        'report', help='read an AI-detection report: overall AI percentage and flagged passages')
    report.add_argument('report', help='path to the Turnitin/iThenticate report PDF')
    report.add_argument('--type', choices=['turnitin', 'ithenticate'],
                        help='which product exported it (default: detect from the file)')
    report.set_defaults(func=cmd_report)

    status = subparsers.add_parser('status', help='check one job, optionally downloading its result')
    status.add_argument('job_id')
    status.add_argument('--download', metavar='SOURCE',
                        help='download the result, naming it after this source document')
    status.add_argument('-o', '--output', help='where to write the downloaded result')
    status.set_defaults(func=cmd_status)

    balance = subparsers.add_parser('balance', help='show the credit balance')
    balance.set_defaults(func=cmd_balance)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except HumanPenError as exc:
        print(f'error: {exc}', file=sys.stderr)
        if exc.retryable:
            print('this one may succeed if tried again.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\ninterrupted; the job keeps running - check it with: humanpen.py status <job_id>',
              file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
