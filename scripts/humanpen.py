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
    python humanpen.py project start "What drives churn? A short report." --file sales.csv
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


def create_free_rehumanize_job(parent_job_id: str, report_path: str, fields: dict) -> dict:
    """Submit a free re-humanize continuation and return the receipt.

    No source document is uploaded - the server clones the parent job's result -
    so only the fresh report and optional fields ride along, POSTed to the
    parent's free-rehumanize endpoint. Eligibility is entirely the server's.
    """
    report_name, report_payload, _ = _read_document(report_path)
    files = {'turnitin_file': (report_name, report_payload, 'application/pdf')}
    body, header = _encode_multipart(fields, files)
    return _request('POST', f'/jobs/{parent_job_id}/free-rehumanize', body=body, content_type=header)


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


def _await_and_report(receipt: dict, args, anchor: str) -> int:
    """Wait for a submitted job, download its result, and report.

    Shared by the upload operations and the free re-humanize continuation. The
    ``anchor`` is the local file the result is named beside when no -o is given:
    the source document for uploads, or the report for a free re-humanize (which
    uploads no document).
    """

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
    output = download_result(job, anchor, args.output)
    report_job(job, output)
    return 0


def run_operation(operation: str, args, fields: dict) -> int:
    """Submit, wait, download, report - the whole job in one call."""

    return _await_and_report(create_job(operation, args.document, fields), args, args.document)


def _load_segments_file(path: str) -> str:
    """Load a per-passage word-budget JSON file into the API's segments field.

    The file is a JSON array of {text, min_words?, max_words?}; this maps those
    user-facing names onto the API's {text, word_min?, word_max?} and returns the
    JSON string the multipart ``segments`` field expects. Validated here so a bad
    file fails before the upload, not after a charge.
    """

    source = Path(path).expanduser()
    if not source.is_file():
        raise HumanPenError(f'no such segments file: {source}', code='FILE_NOT_FOUND')
    try:
        items = json.loads(source.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise HumanPenError(f'segments file is not valid JSON: {exc}', code='INVALID_SEGMENTS') from exc
    if not isinstance(items, list) or not items:
        raise HumanPenError('segments file must be a non-empty JSON array', code='INVALID_SEGMENTS')
    segments: list[dict] = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get('text', '')).strip():
            raise HumanPenError('each segment needs a non-empty "text"', code='INVALID_SEGMENTS')
        segment: dict = {'text': item['text']}
        if item.get('min_words') is not None:
            segment['word_min'] = item['min_words']
        if item.get('max_words') is not None:
            segment['word_max'] = item['max_words']
        segments.append(segment)
    return json.dumps(segments, ensure_ascii=False)


def cmd_humanize(args) -> int:
    whole_band = args.min_words is not None or args.max_words is not None
    # The whole-document band and the per-passage paths (a report, or a segments
    # file) scope the job to different things, and the API forbids the mix - it
    # would charge before mismatching. Per-passage limits ride on --segments-file,
    # which does combine with --report (the report's passages are their scope).
    if whole_band and args.report:
        raise HumanPenError(
            '--min-words/--max-words target the whole document and cannot combine with --report, '
            'which rewrites only the flagged passages. For per-passage limits use --segments-file.',
            code='INVALID_WORD_BUDGET')
    if whole_band and args.segments_file:
        raise HumanPenError(
            '--min-words/--max-words target the whole document and cannot combine with --segments-file, '
            'which carries its own per-passage limits. Use one or the other.',
            code='INVALID_WORD_BUDGET')
    fields = {
        'strategy': args.strategy,
        'additional_instructions': args.instructions,
        '_report_path': args.report,
        'word_min': args.min_words,
        'word_max': args.max_words,
    }
    if args.segments_file:
        fields['segments'] = _load_segments_file(args.segments_file)
    return run_operation('humanize', args, fields)


def cmd_free_rehumanize(args) -> int:
    fields = {
        'strategy': args.strategy,
        'additional_instructions': args.instructions,
    }
    if args.segments_file:
        fields['segments'] = _load_segments_file(args.segments_file)
    receipt = create_free_rehumanize_job(args.job_id, args.report, fields)
    return _await_and_report(receipt, args, args.report)


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


# ---------- research projects ----------
#
# A research project is a conversation with HumanPen's cloud agents rather than one job: they scope the request with
# the user, quote a plan in credits, work, are reviewed and deliver files, and in between they wait on the user. So
# these commands follow the API's own steps (start, show, wait, act, message, download) instead of hiding them: what
# the agents ask and the plan they quote are the user's to answer.

# A project with autonomy shows a wait for a few seconds before HumanPen answers it: `project wait` waits through it.
AUTONOMY_GRACE_SECONDS = 30
MESSAGE_CHARS = 1500


def _json_request(method: str, path: str, body: dict | None = None, idempotent: bool = False) -> dict:
    """A JSON call; `idempotent` sends an Idempotency-Key so the request is never done twice."""

    req_body = json.dumps(body).encode('utf-8') if body is not None else None
    url = f'{_base_url()}{path}'
    req = request.Request(url, method=method, data=req_body)
    req.add_header('Authorization', f'Bearer {_api_key()}')
    req.add_header('User-Agent', 'humanpen-skill/1.0')
    if req_body is not None:
        req.add_header('Content-Type', 'application/json')
    if idempotent:
        req.add_header('Idempotency-Key', uuid.uuid4().hex)
    try:
        with request.urlopen(req, timeout=120) as response:
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
        elif exc.code == 403 and 'projects:' in message:
            message = f'{message} - research projects need a key created with "Research projects" ticked, at {KEYS_URL}'
        raise HumanPenError(f'HTTP {exc.code} {code}: {message}', code=code,
                            retryable=exc.code == 429 or exc.code >= 500) from exc
    except error.URLError as exc:
        raise HumanPenError(f'cannot reach {url}: {exc.reason}', retryable=True) from exc
    return payload.get('data', payload)


def _local_files(paths: list[str]) -> list[dict]:
    files = []
    for text in paths or []:
        path = Path(text).expanduser()
        if not path.is_file():
            raise HumanPenError(f'no such file: {path}', code='FILE_NOT_FOUND')
        files.append({'name': path.name, 'size': path.stat().st_size, 'path': path})
    names = [item['name'] for item in files]
    repeated = {name for name in names if names.count(name) > 1}
    if repeated:
        raise HumanPenError(f'two files are named {sorted(repeated)[0]}; rename one', code='DUPLICATE_FILE_NAME')
    return files


def _put(url: str, data: bytes, headers: dict | None = None) -> str:
    """PUT bytes to a signed URL (no Authorization: the URL is the credential); returns the ETag."""

    req = request.Request(url, method='PUT', data=data)
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with request.urlopen(req, timeout=600) as response:
            return response.headers.get('ETag') or ''
    except (error.HTTPError, error.URLError) as exc:
        raise HumanPenError(f'uploading failed: {exc}', code='UPLOAD_FAILED', retryable=True) from exc


def _upload(project_id: str, uploads: list, files: list[dict]) -> list[str]:
    """Send each file to its target (one PUT, or numbered parts of a large one), then tell the project."""

    done = []
    for upload in uploads or []:
        local = next((item for item in files if item['name'] == upload.get('name')), None)
        target = upload.get('target') or {}
        if local is None:
            raise HumanPenError(f"the API asked for a file not sent: {upload.get('name')}", code='UPLOAD_MISMATCH')
        if target.get('method') == 'PUT':
            _put(target['url'], local['path'].read_bytes(), target.get('headers'))
            done.append({'name': local['name']})
        elif target.get('method') == 'MULTIPART':
            parts, size = [], int(target['part_size'])
            with local['path'].open('rb') as handle:
                for part in target['parts']:
                    handle.seek((int(part['number']) - 1) * size)
                    parts.append({'number': part['number'], 'etag': _put(part['url'], handle.read(size))})
            done.append({'name': local['name'], 'upload_id': target['upload_id'], 'parts': parts})
        else:
            raise HumanPenError(f"unknown upload target for {upload.get('name')}", code='UPLOAD_MISMATCH')
    if done:
        _json_request('POST', f'/agent/projects/{project_id}/uploads/complete', {'files': done})
    return [item['name'] for item in done]


def _latest_events(project_id: str, types: str, keep: int) -> list:
    """The latest few events of these types, reading the timeline from its start."""

    after, kept = 0, []
    for _ in range(20):
        page = _json_request('GET', f'/agent/projects/{project_id}/events?after={after}&limit=500&types={types}')
        kept = (kept + page.get('events', []))[-keep:]
        if page.get('next_after', after) == after:
            break
        after = page['next_after']
    return kept


def _busy(state) -> bool:
    """Whether a project is not the user's to act on yet: queued for its turn, or the agents at work."""

    return state in ('queued', 'working')


def _autonomy_will_answer(project: dict) -> bool:
    """Whether HumanPen may be about to answer what the project needs from its user (its autonomy covers it): a plan
    to confirm (HumanPen confirms it when its own estimate fits what is left of the cap; the API does not show that
    estimate, so the grace in project wait decides), or questions it answers with the recommended answers."""

    autonomy = project.get('autonomy') or {}
    needed = (project.get('required_input') or {}).get('type')
    if not autonomy or project.get('state') != 'input_required':
        return False
    if needed == 'confirm_or_revise_plan':
        return autonomy.get('confirm_plan') == 'auto'
    return needed == 'answer_questions' and autonomy.get('answer') == 'recommended'


def _describe(project: dict) -> dict:
    """What an agent needs to tell the user and take the next step."""

    needed = project.get('required_input') or {}
    spec = project.get('spec') or {}
    picture = {
        'project_id': project.get('id'), 'title': project.get('title'), 'state': project.get('state'),
        'stage': project.get('stage'), 'needs_from_user': needed.get('type'), 'pause_id': needed.get('pause_id'),
        'queue_position': project.get('queue_position'),
        'allowed_actions': project.get('allowed_actions'),
        'now': (project.get('activity') or {}).get('description'),
        'question': project.get('question'),
        'delivered_version': project.get('delivered_version'),
        'consumed_credits': project.get('consumed_credits', (project.get('billing') or {}).get('consumed_credits')),
        'credit_cap': (project.get('autonomy') or {}).get('max_credits'),
    }
    if needed.get('type') == 'confirm_or_revise_plan':
        picture['plan'] = {'spec_version': project.get('spec_version'), 'goal': spec.get('goal') or spec.get('title'),
                           'deliverables': [item.get('path') or item.get('description')
                                            for item in spec.get('deliverables') or []],
                           'estimate_minutes': project.get('estimate_minutes')}
    if needed.get('type') == 'answer_questions' and project.get('stage') == 'scoping':
        asked = _latest_events(project['id'], 'intake.questions', 1)
        picture['questions'] = asked[0]['data'].get('questions') if asked else None
    if not _busy(project.get('state')):
        said = _latest_events(project['id'], 'agent.message', 1)
        text = str(said[0]['data'].get('text') or '') if said else ''
        picture['last_message'] = text[:MESSAGE_CHARS] + ('...' if len(text) > MESSAGE_CHARS else '')
    return {key: value for key, value in picture.items() if value is not None}


def _print(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_project_start(args) -> int:
    files = _local_files(args.file)
    body = {'files': [{'name': item['name'], 'size': item['size']} for item in files]}
    if args.title:
        body['title'] = args.title
    if args.lang:
        body['lang'] = args.lang
    if args.max_credits:
        body['autonomy'] = {'confirm_plan': 'auto' if args.auto_confirm else 'ask',
                            'answer': 'recommended' if args.answer_recommended else 'ask',
                            'max_credits': args.max_credits}
    elif args.auto_confirm or args.answer_recommended:
        raise HumanPenError('--auto-confirm and --answer-recommended need --max-credits, a cap the user agreed to',
                            code='MAX_CREDITS_REQUIRED')
    created = _json_request('POST', '/agent/projects', body, idempotent=True)
    project_id = created['project']['id']
    names = _upload(project_id, created.get('uploads'), files)
    sent = _json_request('POST', f'/agent/projects/{project_id}/messages',
                         {'text': args.request, **({'attachments': names} if names else {})}, idempotent=True)
    return _print({'project_id': project_id, 'after_seq': sent.get('seq'), 'files': names,
                   'next': f'project wait {project_id} --after {sent.get("seq")}'})


def cmd_project_show(args) -> int:
    return _print(_describe(_json_request('GET', f'/agent/projects/{args.project_id}')))


def cmd_project_wait(args) -> int:
    """Wait until the project needs the user or has finished (its state is no longer queued or working)."""

    deadline = time.monotonic() + args.timeout
    grace = None
    after = args.after
    delay = POLL_FIRST_SECONDS
    while True:
        if after is not None:
            left = max(1, min(30, int(deadline - time.monotonic())))
            page = _json_request('GET', f'/agent/projects/{args.project_id}/events?after={after}'
                                        f'&types=project.state&wait={left}')
            after = page.get('next_after', after)
            events = page.get('events') or []
            state = events[-1].get('data', {}).get('state') if events else None
            settled = state is not None and not _busy(state)
        else:
            status = _json_request('GET', f'/agent/projects/{args.project_id}/status')
            state = status.get('state')
            settled = not _busy(state)
        if settled:
            project = _json_request('GET', f'/agent/projects/{args.project_id}')
            if not _autonomy_will_answer(project):
                return _print(_describe(project))
            grace = grace or time.monotonic() + AUTONOMY_GRACE_SECONDS
            if time.monotonic() >= grace:
                return _print(_describe(project))
        if time.monotonic() >= max(deadline, grace or 0):
            project = _describe(_json_request('GET', f'/agent/projects/{args.project_id}'))
            return _print({**project, 'after_seq': after, 'note': 'still working - run project wait again'})
        if after is None:
            print(f'  ... {args.project_id}: {state or "working"}', file=sys.stderr)
            time.sleep(delay)
            delay = min(delay * 2, POLL_MAX_SECONDS)


def cmd_project_act(args) -> int:
    body = {'action': args.action}
    for name in ('spec_version', 'pause_id', 'max_credits', 'version', 'value', 'text'):
        if getattr(args, name, None) is not None:
            body[name] = getattr(args, name)
    if args.answers:
        try:
            body['answers'] = json.loads(args.answers)
        except json.JSONDecodeError as exc:
            raise HumanPenError('--answers must be JSON: {"<question id>": "<answer>"}', code='BAD_ANSWERS') from exc
    answer = _json_request('POST', f'/agent/projects/{args.project_id}/actions', body, idempotent=True)
    return _print({'project_id': args.project_id, 'done': args.action, 'after_seq': answer.get('seq')})


def cmd_project_message(args) -> int:
    files = _local_files(args.file)
    names = []
    if files:
        targets = _json_request('POST', f'/agent/projects/{args.project_id}/uploads',
                                {'files': [{'name': item['name'], 'size': item['size']} for item in files]},
                                idempotent=True)
        names = _upload(args.project_id, targets.get('uploads'), files)
    sent = _json_request('POST', f'/agent/projects/{args.project_id}/messages',
                         {'text': args.text, **({'attachments': names} if names else {})}, idempotent=True)
    return _print({'project_id': args.project_id, 'after_seq': sent.get('seq'), 'files': names})


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def cmd_project_download(args) -> int:
    """Save a delivered version's zip. The API redirects to a short-lived signed URL, fetched without the key."""

    deliveries = _json_request('GET', f'/agent/projects/{args.project_id}/deliveries').get('deliveries') or []
    chosen = ([item for item in deliveries if item.get('version') == args.version] if args.version
              else deliveries[-1:])
    if not chosen:
        raise HumanPenError('nothing delivered yet' if not args.version else f'no delivered version {args.version}',
                            code='NO_DELIVERY')
    version = chosen[0]['version']
    zip_path = f'/agent/projects/{args.project_id}/deliveries/{version}/zip'
    req = request.Request(_base_url() + zip_path)
    req.add_header('Authorization', f'Bearer {_api_key()}')
    req.add_header('User-Agent', 'humanpen-skill/1.0')
    location = None
    try:
        request.build_opener(_NoRedirect).open(req, timeout=60)
    except error.HTTPError as exc:
        location = exc.headers.get('Location') if 300 <= exc.code < 400 else None
        if location is None:
            raise HumanPenError(f'HTTP {exc.code}: the delivery could not be downloaded', code='DOWNLOAD_FAILED',
                                retryable=exc.code >= 500) from exc
    if not location:
        raise HumanPenError('the API gave no download link', code='DOWNLOAD_FAILED')
    directory = Path(args.output or '.').expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'project-{args.project_id[:8]}-v{version}.zip'
    with request.urlopen(location, timeout=600) as response:
        target.write_bytes(response.read())
    return _print({'project_id': args.project_id, 'version': version, 'files': chosen[0].get('files'),
                   'output': str(target), 'bytes': target.stat().st_size})


def _add_project_commands(subparsers) -> None:
    project = subparsers.add_parser(
        'project', help='hand a research, data analysis or writing task to HumanPen\'s cloud agents')
    commands = project.add_subparsers(dest='project_command', required=True)

    start = commands.add_parser('start', help='start a project: upload files and send the request')
    start.add_argument('request', help="what the user wants done, in the user's words")
    start.add_argument('--file', action='append', metavar='PATH', help='an input file (repeat for more)')
    start.add_argument('--title', help='a name for the project')
    start.add_argument('--lang', help='the language to write in, e.g. en or zh')
    start.add_argument('--max-credits', dest='max_credits', type=int, metavar='N',
                       help='a cap on what the whole project may be charged, agreed by the user; with it budget '
                            'pauses go on by themselves within the cap')
    start.add_argument('--auto-confirm', dest='auto_confirm', action='store_true',
                       help="confirm the plan without asking when HumanPen's estimate of it fits what is left of "
                            'the cap (needs --max-credits)')
    start.add_argument('--answer-recommended', dest='answer_recommended', action='store_true',
                       help="answer the agents' questions with the recommended answers (needs --max-credits)")
    start.set_defaults(func=cmd_project_start)

    show = commands.add_parser('show', help='where a project stands: what it needs from the user, the plan or '
                                            'questions, the last message')
    show.add_argument('project_id')
    show.set_defaults(func=cmd_project_show)

    wait = commands.add_parser('wait', help='wait until the project needs the user or has finished')
    wait.add_argument('project_id')
    wait.add_argument('--after', type=int, metavar='SEQ', help='the after_seq the last command printed')
    wait.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT_SECONDS, help='seconds to wait at most')
    wait.set_defaults(func=cmd_project_wait)

    act = commands.add_parser('act', help="take one of the project's allowed_actions")
    act.add_argument('project_id')
    act.add_argument('action', choices=['confirm_plan', 'answer', 'top_up', 'one_more_round', 'accept_as_is',
                                        'pause', 'resume', 'cancel', 'feedback', 'extend_retention'])
    act.add_argument('--spec-version', dest='spec_version', type=int, help='confirm_plan: the version shown')
    act.add_argument('--pause-id', dest='pause_id', help='top_up: the pause it continues')
    act.add_argument('--answers', help='answer: JSON {"<question id>": "<answer>"}')
    act.add_argument('--max-credits', dest='max_credits', type=int, help='a higher cap for the whole project')
    act.add_argument('--version', type=int, help='feedback: the delivered version')
    act.add_argument('--value', choices=['satisfied', 'needs_changes'], help='feedback: the verdict')
    act.add_argument('--text', help='feedback: what to change')
    act.set_defaults(func=cmd_project_act)

    message = commands.add_parser('message', help='write to the agents, with files: context, or changes after a '
                                                  'delivery')
    message.add_argument('project_id')
    message.add_argument('text')
    message.add_argument('--file', action='append', metavar='PATH', help='a file to add (repeat for more)')
    message.set_defaults(func=cmd_project_message)

    download = commands.add_parser('download', help='save a delivered version as a zip')
    download.add_argument('project_id')
    download.add_argument('--version', type=int, help='the delivered version (default: the latest)')
    download.add_argument('-o', '--output', metavar='DIR', help='the directory to save it in (default: here)')
    download.set_defaults(func=cmd_project_download)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI, one subcommand per operation."""

    parser = argparse.ArgumentParser(
        prog='humanpen.py',
        description='Process documents with HumanPen: humanize, fix citations, condense, translate; or run a '
                    'research project with its cloud agents.',
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
    humanize.add_argument('--min-words', dest='min_words', type=int, metavar='N',
                          help='lower word bound for the rewritten document (optional). EXPERIMENTAL: a word '
                               'limit noticeably weakens AI-rate reduction, so omit unless a length is '
                               'required. Not with --report or --segments-file')
    humanize.add_argument('--max-words', dest='max_words', type=int, metavar='N',
                          help='upper word bound for the rewritten document (optional). Same caveat and '
                               'exclusivity as --min-words')
    humanize.add_argument('--segments-file', dest='segments_file', metavar='PATH',
                          help='JSON file for per-passage word control: a list of '
                               '{"text": ..., "min_words": N, "max_words": N}. Get the passage texts from '
                               'the `report` command and pass --report alongside so it defines scope. '
                               'EXPERIMENTAL (see --min-words). Not with --min-words/--max-words')
    humanize.set_defaults(func=cmd_humanize)

    free_rehumanize = subparsers.add_parser(
        'free-rehumanize',
        help='continue a finished humanize job for free: re-run its still-flagged passages with a new report')
    free_rehumanize.add_argument('job_id', help='the finished humanize job to continue (its job_id)')
    free_rehumanize.add_argument('--report', required=True,
                                 help="fresh Turnitin/iThenticate report PDF for that job's result; only its "
                                      'still-flagged passages are rewritten, at no credit cost')
    free_rehumanize.add_argument('--strategy', default='balanced', choices=['balanced', 'aggressive'],
                                 help='rewriting intensity (default: balanced, recommended for a continuation)')
    free_rehumanize.add_argument('--segments-file', dest='segments_file', metavar='PATH',
                                 help='JSON file for per-passage word control on the flagged passages: a list '
                                      'of {"text": ..., "min_words": N, "max_words": N}')
    free_rehumanize.add_argument('--instructions', help='extra requirements for this job')
    free_rehumanize.add_argument('-o', '--output', help='where to write the result (default: beside the report)')
    free_rehumanize.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT_SECONDS,
                                 help='seconds to wait before giving up on the job')
    free_rehumanize.add_argument('--no-wait', action='store_true',
                                 help='submit and print the receipt without waiting')
    free_rehumanize.set_defaults(func=cmd_free_rehumanize)

    citations = add_job_flags(subparsers.add_parser(
        'fix-citations', help='convert in-text citations and the reference list to one style'))
    citations.add_argument('--style', required=True,
                           help='target style: apa7, mla9, harvard, chicago_author_date, '
                                'chicago_notes, ieee, vancouver, gbt7714, '
                                'gbt7714_author_year, ama, acs, oscola')
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
    translate.add_argument('--to', required=True,
                           help='target language: zh, zh-tw, en, ja, ko, es, fr, pt, ru, de, pl, it')
    translate.add_argument('--source-lang', dest='source_lang', default='auto',
                           help='source language, same codes as --to (default: auto)')
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

    _add_project_commands(subparsers)
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
