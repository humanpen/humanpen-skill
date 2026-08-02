#!/usr/bin/env python3
"""Check this skill against the API it actually talks to.

A published client rots when the API moves, and it rots in someone else's
install rather than in a test run. This asks the live API for its own OpenAPI
document and verifies that every path this skill builds is one the API still
documents.

No credentials and no private repository: the OpenAPI document is public, so
anyone who forks this can run the same check.

    python3 scripts/check_api.py
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = os.environ.get('HUMANPEN_BASE_URL', 'https://api.humanpen.net/v1').rstrip('/')
CLIENT = Path(__file__).resolve().parent / 'humanpen.py'
PATH_PATTERN = re.compile(r"'(/(?:jobs|files|credits|detect-reports|auth)[^'\s]*)'")
PLACEHOLDER = re.compile(r'\{[^}]+\}')


def _normalize(path):
    """Reduce an interpolated path to the template form OpenAPI uses.

    Args:
        path (str)
    Returns:
        str
    """
    return PLACEHOLDER.sub('{id}', path)


def main():
    """Compare the paths this client calls against the published API.

    Returns:
        int: process exit code
    """
    try:
        with urllib.request.urlopen(f'{BASE_URL}/openapi.json', timeout=30) as response:
            document = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # A network failure is not a contract failure, and reporting it as one
        # teaches people to ignore this check.
        print(f'SKIP: could not reach {BASE_URL}/openapi.json ({exc})', file=sys.stderr)
        return 0

    documented = {_normalize(path) for path in document.get('paths', {})}
    called = {_normalize(path) for path in PATH_PATTERN.findall(CLIENT.read_text(encoding='utf-8'))}

    if not called:
        print('FAIL: found no API paths in the client - this check has stopped checking.',
              file=sys.stderr)
        return 1

    missing = sorted(called - documented)
    if missing:
        print('FAIL: the API no longer documents paths this client calls:', file=sys.stderr)
        for path in missing:
            print(f'  {path}', file=sys.stderr)
        print(f'\nCompare against {BASE_URL}/docs.md and update the client.', file=sys.stderr)
        return 1

    print(f'OK: all {len(called)} paths this client calls are documented by {BASE_URL}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
