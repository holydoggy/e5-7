"""Standalone REPAIR-only API: consume an incoming incremental-check report and emit a patch.

This service deliberately does NOT run EChecker/scan. It only validates the report
envelope/hash/commit and calls lab.patch() on the target checkout.
"""
import argparse
import hashlib
import json
import re
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'labs/e8e10'), str(ROOT / 'labs/e11e12/vendor'), '/app']
from lab import patch, run


class Failure(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path, out, job_id):
    return {'uri': f'artifact://{job_id}/{path.relative_to(out).as_posix()}',
            'sha256': sha256_bytes(path.read_bytes()), 'bytes': path.stat().st_size}


def under_data(value):
    return Path(value).resolve().is_relative_to((ROOT / 'data').resolve())


def validate(request):
    if request.get('mode') != 'repair':
        raise Failure('INVALID_REQUEST', 'mode must be repair')
    for field in ('repo', 'target', 'report', 'report_sha256'):
        if not request.get(field):
            raise Failure('INVALID_REQUEST', f'{field} required')
    if not re.fullmatch(r'[0-9a-f]{40}', request['target']):
        raise Failure('INVALID_REQUEST', 'target must be a 40-hex commit')
    if not re.fullmatch(r'[0-9a-f]{64}', request['report_sha256']):
        raise Failure('INVALID_REQUEST', 'report_sha256 must be a 64-hex digest')
    repo = Path(request['repo']).resolve()
    report_path = Path(request['report']).resolve()
    if not under_data(repo) or not repo.is_dir():
        raise Failure('INVALID_REQUEST', 'repo must be an existing directory under /course/data')
    if not under_data(report_path) or not report_path.is_file():
        raise Failure('INVALID_REQUEST', 'report must be an existing file under /course/data')
    raw = report_path.read_bytes()
    actual = sha256_bytes(raw)
    if actual != request['report_sha256']:
        raise Failure('REPORT_HASH_MISMATCH', f'expected {request["report_sha256"]}, got {actual}')
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        raise Failure('REPORT_SCHEMA_MISMATCH', 'report is not JSON')
    if envelope.get('schema_version') != 'e11e12-1':
        raise Failure('REPORT_SCHEMA_MISMATCH', 'schema_version must be e11e12-1')
    if envelope.get('kind') != 'incremental-check':
        raise Failure('REPORT_KIND_MISMATCH', 'kind must be incremental-check')
    if envelope.get('status') != 'SUCCEEDED':
        raise Failure('REPORT_STATUS_INVALID', 'report status must be SUCCEEDED')
    if envelope.get('commit') != request['target']:
        raise Failure('REPORT_COMMIT_MISMATCH', 'report envelope commit != target')
    report = envelope.get('data') or {}
    if report.get('commit') != request['target']:
        raise Failure('REPORT_COMMIT_MISMATCH', 'report data.commit != target')
    try:
        head = run(['git', 'rev-parse', 'HEAD'], repo).strip()
    except ValueError as exc:
        raise Failure('REPO_CHECK_FAILED', str(exc))
    if head != request['target']:
        raise Failure('REPO_HEAD_MISMATCH', f'repo HEAD {head} != target {request["target"]}')
    return repo, envelope, report


class Store:
    def __init__(self, root):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.jobs = {}
        self.keys = {}
        for path in root.glob('job-*/state.json'):
            state = json.loads(path.read_text())
            if state.get('status') in ('QUEUED', 'RUNNING'):
                state.update(status='FAILED',
                             error={'code': 'SERVER_RESTARTED', 'message': 'Resubmit with a new key'})
                save(path, state)
            self.jobs[state['job_id']] = state
            self.keys[state['idempotency_key']] = (state['request_hash'], state['job_id'])

    def submit(self, request, key):
        if not isinstance(request, dict):
            raise Failure('INVALID_REQUEST', 'input must be a JSON object')
        if not isinstance(key, str) or not key or len(key) > 128:
            raise Failure('INVALID_REQUEST', 'idempotency_key required, max 128 characters')
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        with self.lock:
            if key in self.keys:
                old, jid = self.keys[key]
                if old != digest:
                    raise Failure('IDEMPOTENCY_CONFLICT', 'same key with different input')
                return dict(self.jobs[jid])
            repo, envelope, report = validate(request)
            jid = 'job-' + uuid.uuid4().hex
            state = {'schema_version': 'e11e12-1', 'kind': 'repair', 'job_id': jid,
                     'trace_id': 'trace-' + uuid.uuid4().hex, 'status': 'QUEUED',
                     'idempotency_key': key, 'request_hash': digest,
                     'target': request['target'], 'report_sha256': request['report_sha256']}
            self.jobs[jid] = state
            self.keys[key] = (digest, jid)
            save(self.root / jid / 'state.json', state)
            self.pool.submit(self.work, jid, request, repo, envelope, report)
            return dict(state)

    def work(self, jid, request, repo, envelope, report):
        state = self.jobs[jid]
        state['status'] = 'RUNNING'
        save(self.root / jid / 'state.json', state)
        out = self.root / jid / 'evidence'
        out.mkdir(parents=True, exist_ok=True)
        try:
            save(out / 'request.json', request)
            save(out / 'received-report.json', envelope)
            (out / 'report.sha256.txt').write_text(request['report_sha256'] + '\n', encoding='utf-8')
            diff, plan = patch(repo, report)
            if not diff:
                raise Failure('NO_MISSING_DEPENDENCY', 'report produced no patch')
            patch_file = out / 'candidate.patch'
            patch_file.write_text(diff, encoding='utf-8')
            patch_sha = sha256_bytes(patch_file.read_bytes())
            repair = {'schema_version': 'e11e12-1', 'kind': 'repair', 'job_id': jid,
                      'trace_id': state['trace_id'], 'commit': request['target'],
                      'status': 'SUCCEEDED',
                      'data': {'report_sha256': request['report_sha256'],
                               'patch_sha256': patch_sha, 'edits': plan},
                      'artifacts': [artifact(patch_file, out, jid)]}
            save(out / 'repair-result.json', repair)
            result = {'schema_version': 'e11e12-1', 'kind': 'repair', 'job_id': jid,
                      'trace_id': state['trace_id'], 'commit': request['target'],
                      'status': 'SUCCEEDED',
                      'data': {'report_sha256': request['report_sha256'],
                               'patch_sha256': patch_sha, 'edits': plan},
                      'artifacts': [artifact(p, out, jid) for p in
                                    (patch_file, out / 'repair-result.json', out / 'received-report.json')]}
            save(out / 'result.json', result)
            state.update(status='SUCCEEDED', patch_sha256=patch_sha)
        except Exception as exc:
            state.update(status='FAILED',
                         error={'code': getattr(exc, 'code', 'REPAIR_FAILED'), 'message': str(exc)})
            save(out / 'result.json', {'schema_version': 'e11e12-1', 'kind': 'repair',
                                       'job_id': jid, 'trace_id': state['trace_id'],
                                       'commit': request['target'], 'status': 'FAILED',
                                       'error': state['error'], 'artifacts': []})
        save(self.root / jid / 'state.json', state)


def serve(host, port):
    store = Store(ROOT / 'work/repair-jobs')

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != '/v1/jobs':
                return self.reply(404, {'error': 'NOT_FOUND'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536:
                    raise Failure('INVALID_REQUEST', 'request size must be 1..65536')
                body = json.loads(self.rfile.read(size))
                state = store.submit(body['input'], body['idempotency_key'])
                self.reply(202, state)
            except Failure as exc:
                self.reply(409 if exc.code == 'IDEMPOTENCY_CONFLICT' else 400,
                           {'error': exc.code, 'message': str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                self.reply(400, {'error': 'INVALID_REQUEST', 'message': str(exc)})

        def do_GET(self):
            if self.path == '/health':
                return self.reply(200, {'status': 'ok', 'schema_version': 'e11e12-1', 'mode': 'repair'})
            parts = self.path.split('?')[0].strip('/').split('/')
            if len(parts) < 3 or parts[:2] != ['v1', 'jobs'] or parts[2] not in store.jobs:
                return self.reply(404, {'error': 'NOT_FOUND'})
            jid = parts[2]
            out = store.root / jid / 'evidence'
            state = store.jobs[jid]
            if len(parts) == 3:
                return self.reply(200, dict(state))
            if parts[3:] == ['artifacts']:
                if not (out / 'result.json').exists():
                    return self.reply(409, {'error': 'RESULT_NOT_READY'})
                return self.reply(200, json.loads((out / 'result.json').read_text()))
            if len(parts) >= 5 and parts[3] == 'files':
                name = unquote('/'.join(parts[4:]))
                path = (out / name).resolve()
                if not path.is_relative_to(out.resolve()) or '.git' in path.parts or not path.is_file():
                    return self.reply(404, {'error': 'NOT_FOUND'})
                data = path.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('X-Content-SHA256', hashlib.sha256(data).hexdigest())
                self.end_headers()
                self.wfile.write(data)
                return
            self.reply(404, {'error': 'NOT_FOUND'})

    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8081)
    args = parser.parse_args()
    serve(args.host, args.port)
