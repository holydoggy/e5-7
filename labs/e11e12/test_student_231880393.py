import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

import pipeline
from lab import commit, fixture, patch, run, scan


class StudentE11B(unittest.TestCase):
    def sample(self, directory):
        root = Path(directory)
        project = root / 'project'
        fixture(project, style='macro')
        base = run(['git', 'rev-parse', 'HEAD'], project).strip()
        main = project / 'main.c'
        main.write_text('#include "extra.h"\n' + main.read_text())
        target = commit(project, 'include extra header')
        report = {
            'schema_version': 'e11e12-1',
            'kind': 'fixed-md',
            'status': 'SUCCEEDED',
            'commit': target,
            'data': scan(project),
        }
        fixed = root / 'fixed-md.json'
        pipeline.save(fixed, report)
        request = {
            'mode': 'e11-b',
            'repo': str(project),
            'base': base,
            'target': target,
            'candidate': str(root / 'candidate.Dockerfile'),
            'fixed_report': str(fixed),
            'expected_output': '1',
        }
        return project, request, report

    @staticmethod
    def draft_success(project, candidate, output, expected_output, timeout):
        # These tests isolate the fixed-report/repair boundary from Docker builds.
        result = {'status': 'SUCCEEDED'}
        pipeline.save(output / 'result.json', result)
        return result

    def test_macro_pipeline_changes_deps_and_keeps_recipe_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            project, request, _ = self.sample(directory)
            before = (project / 'Makefile').read_bytes()
            output = Path(directory) / 'result'
            with mock_patch('draft.autobuild.auto_build', side_effect=self.draft_success):
                result = pipeline.execute(request, output)

            self.assertEqual(result['status'], 'SUCCEEDED', result.get('error'))
            self.assertEqual(
                [stage['name'] for stage in result['stages']],
                ['draft', 'fixed-md', 'repair', 'recheck'],
            )
            plan = json.loads((output / 'repair-plan.json').read_text())
            self.assertEqual(plan, [
                {'target': 'main.o', 'dependency': 'config.h', 'style': 'macro'},
                {'target': 'main.o', 'dependency': 'extra.h', 'style': 'macro'},
            ])
            diff = (output / 'candidate.patch').read_text().splitlines()
            changes = [line for line in diff if line.startswith(('+', '-'))
                       and not line.startswith(('+++', '---'))]
            self.assertEqual(changes, [
                '-DEPS = main.c unused.h',
                '+DEPS = main.c unused.h config.h extra.h',
            ])
            after = (output / 'target-project' / 'Makefile').read_bytes()
            recipes = lambda data: [line for line in data.splitlines()
                                    if line.startswith(b'\t')]
            self.assertEqual(recipes(before), recipes(after))
            self.assertIn(b'main.o: $(DEPS)', after)
            self.assertEqual((project / 'Makefile').read_bytes(), before)
            verdict = json.loads((output / 'validation' / 'validation.json').read_text())
            self.assertTrue(verdict['accepted'])
            self.assertEqual(verdict['checks'], {
                'patch_applies': True, 'build': True, 'test': True,
                'header_change': True, 'no_missing': True,
            })
            recheck = json.loads((output / 'recheck.json').read_text())
            self.assertFalse(any(f['type'] == 'MISSING'
                                 for f in recheck['data']['findings']))

    def assert_stale_report_stops_before_patch(self, field):
        with tempfile.TemporaryDirectory() as directory:
            project, request, report = self.sample(directory)
            before = (project / 'Makefile').read_bytes()
            if field == 'envelope':
                report['commit'] = '0' * 40
            else:
                report['data']['commit'] = '0' * 40
            pipeline.save(Path(request['fixed_report']), report)
            output = Path(directory) / 'result'
            with mock_patch('draft.autobuild.auto_build', side_effect=self.draft_success), \
                    mock_patch.object(pipeline, 'patch', wraps=patch) as repair:
                result = pipeline.execute(request, output)
                repair.assert_not_called()

            self.assertEqual(result['status'], 'FAILED')
            self.assertEqual(result['error']['code'], 'STALE_REPORT')
            self.assertEqual([s['name'] for s in result['stages']], ['draft'])
            self.assertFalse((output / 'candidate.patch').exists())
            self.assertFalse((output / 'repair.json').exists())
            self.assertFalse((output / 'validation').exists())
            self.assertEqual((project / 'Makefile').read_bytes(), before)
            self.assertEqual((output / 'target-project' / 'Makefile').read_bytes(), before)

    def test_stale_envelope_stops_before_patch(self):
        self.assert_stale_report_stops_before_patch('envelope')

    def test_stale_payload_stops_before_patch(self):
        self.assert_stale_report_stops_before_patch('payload')


if __name__ == '__main__':
    unittest.main()
