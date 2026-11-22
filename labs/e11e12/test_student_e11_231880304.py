import tempfile
import unittest
from pathlib import Path

import pipeline
from lab import fixture, scan, patch


class StudentE11B231880304(unittest.TestCase):
    def test_macro_style_patch_updates_definition_only(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p, 'macro')
            before = (p / 'Makefile').read_text()
            diff, plan = patch(p, scan(p))
            self.assertEqual(
                plan,
                [{'target': 'main.o', 'dependency': 'config.h', 'style': 'macro'}])
            self.assertIn('+DEPS = main.c unused.h config.h', diff)
            self.assertIn('main.o: $(DEPS)', before)
            self.assertNotIn('-\tgcc', diff)
            self.assertEqual((p / 'Makefile').read_text(), before)

    def test_fixed_md_commit_mismatch_rejected(self):
        report = {'schema_version': 'e11e12-1', 'kind': 'fixed-md',
                  'commit': '0' * 40, 'status': 'SUCCEEDED'}
        with self.assertRaisesRegex(pipeline.Failure, 'another commit'):
            pipeline.check_envelope(report, 'a' * 40, 'fixed-md')


if __name__ == '__main__':
    unittest.main()
