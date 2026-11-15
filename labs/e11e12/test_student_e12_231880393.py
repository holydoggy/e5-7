import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

import pipeline
import server
from lab import commit, fixture, patch, run


class StudentE12(unittest.TestCase):
    @staticmethod
    def request():
        return {
            'mode': 'e12',
            'repo': str(pipeline.ROOT / 'data' / 'restart-test'),
            'base': 'a' * 40,
            'target': 'b' * 40,
        }

    def stored_state(self, root, job_id, key, status):
        digest = hashlib.sha256(
            json.dumps(self.request(), sort_keys=True).encode()).hexdigest()
        state = {
            'schema_version': 'e11e12-1', 'job_id': job_id,
            'idempotency_key': key, 'request_hash': digest, 'status': status,
        }
        if status == 'SUCCEEDED':
            state['trace_id'] = 'trace-completed'
        pipeline.save(root / job_id / 'state.json', state)
        return state

    def test_restart_marks_unfinished_and_preserves_completed_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.stored_state(root, 'job-queued', 'queued', 'QUEUED')
            self.stored_state(root, 'job-running', 'running', 'RUNNING')
            completed = self.stored_state(root, 'job-done', 'done', 'SUCCEEDED')
            store = server.Store(root)
            try:
                for job_id in ['job-queued', 'job-running']:
                    self.assertEqual(store.jobs[job_id]['status'], 'FAILED')
                    self.assertEqual(store.jobs[job_id]['error']['code'],
                                     'SERVER_RESTARTED')
                    persisted = json.loads((root / job_id / 'state.json').read_text())
                    self.assertEqual(persisted, store.jobs[job_id])
                self.assertEqual(store.jobs['job-done'], completed)
                with mock_patch.object(store.pool, 'submit') as submit:
                    again = store.submit(self.request(), 'done')
                    self.assertEqual(again, completed)
                    submit.assert_not_called()
            finally:
                store.pool.shutdown()

    def test_restarted_job_requires_a_new_key_for_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.stored_state(root, 'job-interrupted', 'old-key', 'RUNNING')
            store = server.Store(root)
            try:
                with mock_patch.object(store.pool, 'submit') as submit:
                    old = store.submit(self.request(), 'old-key')
                    self.assertEqual(old['job_id'], 'job-interrupted')
                    self.assertEqual(old['error']['code'], 'SERVER_RESTARTED')
                    submit.assert_not_called()
                    retry = store.submit(self.request(), 'new-key')
                    self.assertNotEqual(retry['job_id'], old['job_id'])
                    self.assertEqual(retry['status'], 'QUEUED')
                    self.assertEqual(retry['request_hash'], old['request_hash'])
                    submit.assert_called_once_with(store.work, retry['job_id'],
                                                   self.request())
            finally:
                store.pool.shutdown()

    @staticmethod
    def draft_success(project, candidate, output, expected_output, timeout):
        # This test checks report consumption; real Docker builds run separately.
        result = {'status': 'SUCCEEDED'}
        pipeline.save(output / 'result.json', result)
        return result

    def test_e12_rejects_wrong_report_kind_before_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project'
            fixture(project)
            base = run(['git', 'rev-parse', 'HEAD'], project).strip()
            main = project / 'main.c'
            main.write_text('#include "extra.h"\n' + main.read_text())
            target = commit(project, 'include extra header')
            before = (project / 'Makefile').read_bytes()
            request = {
                'mode': 'e12', 'repo': str(project), 'base': base,
                'target': target, 'candidate': str(root / 'unused.Dockerfile'),
            }
            load = pipeline.load_artifact

            def wrong_kind(path, expected_sha256):
                report = load(path, expected_sha256)
                report['kind'] = 'fixed-md'
                return report

            output = root / 'result'
            with mock_patch('draft.autobuild.auto_build', side_effect=self.draft_success), \
                    mock_patch.object(pipeline, 'load_artifact', side_effect=wrong_kind), \
                    mock_patch.object(pipeline, 'patch', wraps=patch) as repair:
                result = pipeline.execute(request, output)
                self.assertEqual(result['status'], 'FAILED')
                self.assertEqual(result['error']['code'], 'ARTIFACT_TYPE_MISMATCH')
                repair.assert_not_called()
            self.assertEqual([stage['name'] for stage in result['stages']],
                             ['draft', 'full-check', 'incremental-check'])
            self.assertFalse((output / 'candidate.patch').exists())
            self.assertEqual((project / 'Makefile').read_bytes(), before)
            self.assertEqual((output / 'target-project' / 'Makefile').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
