import json, tempfile, unittest
from pathlib import Path
from lab import fixture,scan,patch,commit

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_independent_known_edges(self):
        r=scan(self.p)
        self.assertEqual(r['actual']['main.o'],['config.h','main.c'])
        self.assertEqual({(f['type'],f['dependency']) for f in r['findings']},{('MISSING','config.h'),('REDUNDANT','unused.h')})

    def test_unchanged_reuses_both_targets(self):
        r=scan(self.p,scan(self.p));self.assertEqual(r['reused'],['main.o','helper.o']);self.assertEqual(r['refreshed'],[])

    def test_include_added_invalidates_cache(self):
        old=scan(self.p)
        (self.p/'main.c').write_text('#include "extra.h"\n'+(self.p/'main.c').read_text());commit(self.p,'new include')
        r=scan(self.p,old)
        self.assertIn(['MISSING','main.o','extra.h'],r['added']);self.assertEqual(len(r['refreshed']),2)

    def test_patch_preserves_redundant_dependency(self):
        r=scan(self.p);diff,plan=patch(self.p,r)
        self.assertIn('+main.o: main.c unused.h config.h',diff)
        self.assertNotIn('-\tgcc',diff)
        self.assertNotIn('config.h',(self.p/'Makefile').read_text())

    def test_old_report_rejected(self):
        r=scan(self.p);r['commit']='0'*40
        with self.assertRaisesRegex(ValueError,'STALE_REPORT'):patch(self.p,r)

    def test_unsafe_dependency_rejected(self):
        r=scan(self.p);r['findings']=[{'type':'MISSING','target':'main.o','dependency':'../outside.h'}]
        with self.assertRaisesRegex(ValueError,'UNSAFE_PATH'):patch(self.p,r)

    def test_unsupported_configuration_rejected(self):
        (self.p/'Makefile').write_text((self.p/'Makefile').read_text().replace('-O0','-include unknown.h'))
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_FLAGS'):scan(self.p)

class StudentE8B(unittest.TestCase):
    def test_only_redundant_keeps_makefile_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p)

            # 补齐 config.h 声明，只保留 unused.h 冗余依赖。
            makefile = p / 'Makefile'
            makefile.write_text(
                makefile.read_text().replace(
                    'main.o: main.c unused.h',
                    'main.o: main.c unused.h config.h'
                )
            )
            commit(p, 'student: declare config.h')

            before = makefile.read_bytes()
            report = scan(p)
            self.assertEqual(report['findings'], [
                {
                    'type': 'REDUNDANT',
                    'target': 'main.o',
                    'dependency': 'unused.h'
                }
            ])

            diff, plan = patch(p, report)
            after = makefile.read_bytes()

            self.assertEqual(diff, '')
            self.assertEqual(plan, [])
            self.assertEqual(before, after)


class StudentE9B(unittest.TestCase):
    def test_duplicate_prerequisites_are_deduplicated(self):
        from lab import run
        for style in ('direct', 'macro', 'mixed'):
            with self.subTest(style=style):
                with tempfile.TemporaryDirectory() as directory:
                    p = Path(directory) / 'sample'
                    fixture(p, style)
                    makefile = p / 'Makefile'
                    text = makefile.read_text()
                    if style == 'mixed':
                        text = text.replace(
                            'HEADERS = unused.h',
                            'HEADERS = unused.h unused.h'
                        ).replace(
                            'main.o: main.c $(HEADERS)',
                            'main.o: main.c $(HEADERS) main.c'
                        )
                    else:
                        text = text.replace(
                            'main.c unused.h',
                            'main.c unused.h main.c unused.h'
                        )
                    makefile.write_text(text)
                    commit(p, 'student: add duplicate prerequisites')
                    before = makefile.read_bytes()
                    self.assertEqual(before.count(b'unused.h'), 2)

                    report = scan(p)
                    self.assertEqual(report['declared'], {
                        'main.o': ['main.c', 'unused.h'],
                        'helper.o': ['helper.c']
                    })
                    self.assertEqual(report['findings'], [
                        {'type': 'MISSING', 'target': 'main.o',
                         'dependency': 'config.h'},
                        {'type': 'REDUNDANT', 'target': 'main.o',
                         'dependency': 'unused.h'}
                    ])

                    diff, plan = patch(p, report)
                    self.assertEqual(plan, [
                        {'target': 'main.o', 'dependency': 'config.h',
                         'style': style}
                    ])
                    self.assertEqual(makefile.read_bytes(), before)
                    candidate = Path(directory) / 'candidate.patch'
                    candidate.write_text(diff)
                    run(['git', 'apply', str(candidate.resolve())], p)
                    after = makefile.read_bytes()
                    self.assertEqual(after.count(b'config.h'), 1)
                    recipes = lambda data: [
                        line for line in data.splitlines()
                        if line.startswith(b'\t')
                    ]
                    self.assertEqual(recipes(before), recipes(after))
                    if style == 'macro':
                        self.assertIn(b'main.o: $(DEPS)\n', after)
                    elif style == 'mixed':
                        self.assertIn(b'$(HEADERS)', after)
                    repaired = scan(p)
                    self.assertEqual(repaired['declared']['main.o'],
                                     ['config.h', 'main.c', 'unused.h'])
                    self.assertEqual(repaired['findings'], [
                        {'type': 'REDUNDANT', 'target': 'main.o',
                         'dependency': 'unused.h'}
                    ])


class StudentE10B(unittest.TestCase):
    def test_buildable_candidate_with_missing_dependency_is_rejected(self):
        import difflib
        from lab import validate
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'sample'
            fixture(p)
            makefile = p / 'Makefile'
            before = makefile.read_bytes()

            # 候选能构建，但没有补齐 main.o 的 config.h 依赖。
            proposed = before.decode().replace(
                'helper.o: helper.c\n',
                'helper.o: helper.c extra.h\n'
            )
            self.assertNotEqual(proposed, before.decode())
            diff = ''.join(difflib.unified_diff(
                before.decode().splitlines(True),
                proposed.splitlines(True),
                fromfile='a/Makefile', tofile='b/Makefile'
            ))
            candidate = root / 'candidate.patch'
            candidate.write_text(diff)
            evidence = root / 'validation'
            result = validate(p, candidate, evidence)

            self.assertEqual(result['checks'], {
                'patch_applies': True,
                'build': True,
                'test': True,
                'header_change': False,
                'no_missing': False
            })
            self.assertIsNone(result['error'])
            self.assertFalse(result['accepted'])
            self.assertTrue(result['rollback'])
            self.assertTrue(result['source_unchanged'])
            self.assertEqual(makefile.read_bytes(), before)
            self.assertEqual((p / 'config.h').read_text(),
                             '#define VALUE 1\n')
            recheck = json.loads((evidence / 'recheck.json').read_text())
            self.assertEqual(
                {(f['type'], f['target'], f['dependency'])
                 for f in recheck['findings']},
                {('MISSING', 'main.o', 'config.h'),
                 ('REDUNDANT', 'main.o', 'unused.h'),
                 ('REDUNDANT', 'helper.o', 'extra.h')}
            )


class StudentE8BRedundant(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_redundant(self):
        r=scan(self.p)
        r['findings']=[f for f in r['findings'] if f['type']=='REDUNDANT']
        self.assertEqual([(f['type'],f['dependency']) for f in r['findings']],[('REDUNDANT','unused.h')])
        before=(self.p/'Makefile').read_bytes()
        diff,plan=patch(self.p,r)
        self.assertEqual(diff,'')
        self.assertEqual(plan,[])
        self.assertEqual((self.p/'Makefile').read_bytes(),before)
        self.assertIn('unused.h',(self.p/'Makefile').read_text())

class StudentE9BDedup(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_duplicate_declaration_deduped(self):
        from lab import declarations, run
        m=self.p/'Makefile'
        m.write_text(m.read_text().replace(
            'main.o: main.c unused.h',
            'main.o: main.c unused.h main.c unused.h'))
        commit(self.p,'student: duplicate declaration')
        declared,_=declarations(self.p)
        self.assertEqual(declared['main.o'],['main.c','unused.h'])
        r=scan(self.p)
        self.assertEqual([(f['type'],f['dependency']) for f in r['findings']],
                         [('MISSING','config.h'),('REDUNDANT','unused.h')])
        diff,plan=patch(self.p,r)
        self.assertEqual(diff.count('+main.o: '),1)
        self.assertEqual(diff.count('config.h'),1)
        candidate=Path(self.tmp.name)/'dup.patch';candidate.write_text(diff)
        run(['git','apply',str(candidate.resolve())],self.p)
        self.assertEqual(
            [(f['type'],f['dependency']) for f in scan(self.p)['findings']],
            [('REDUNDANT','unused.h')])

class StudentE10BPartialPatch(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.p=self.root/'sample';fixture(self.p)

    def test_md_candidate(self):
        import difflib
        from lab import validate
        m=self.p/'Makefile'
        original=m.read_text()
        patched=original.replace('helper.o: helper.c','helper.o: helper.c unused.h')
        diff=''.join(difflib.unified_diff(original.splitlines(True),patched.splitlines(True),
                                          fromfile='a/Makefile',tofile='b/Makefile'))
        candidate=self.root/'partial.patch';candidate.write_text(diff)
        before=m.read_bytes()
        r=validate(self.p,candidate,self.root/'validation')
        self.assertTrue(r['checks']['patch_applies'])
        self.assertTrue(r['checks']['build'])
        self.assertTrue(r['checks']['test'])
        self.assertFalse(r['checks']['header_change'])
        self.assertFalse(r['checks']['no_missing'])
        self.assertFalse(r['accepted'])
        self.assertTrue(r['rollback'])
        self.assertTrue(r['source_unchanged'])
        self.assertIsNone(r['error'])
        self.assertEqual(m.read_bytes(),before)
        self.assertTrue((self.root/'validation'/'validation.json').is_file())

class StudentE8BRedundant304(unittest.TestCase):
    def test_redundant_only_report_generates_no_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            report=scan(p)
            report['findings']=[f for f in report['findings'] if f['type']=='REDUNDANT']
            self.assertEqual(len(report['findings']),1)
            before=(p/'Makefile').read_bytes()
            diff,plan=patch(p,report)
            self.assertEqual(diff,'')
            self.assertEqual(plan,[])
            self.assertEqual((p/'Makefile').read_bytes(),before)
            self.assertIn(b'main.o: main.c unused.h',before)

class StudentE9BDedup304(unittest.TestCase):
    def test_duplicate_missing_findings_add_dependency_once(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            report=scan(p)
            missing=[f for f in report['findings'] if f['type']=='MISSING']
            self.assertEqual(len(missing),1)
            report['findings']=missing*2
            before=(p/'Makefile').read_bytes()
            diff,plan=patch(p,report)
            added=[l for l in diff.splitlines() if l.startswith('+') and 'config.h' in l]
            self.assertEqual(added,['+main.o: main.c unused.h config.h'])
            self.assertEqual(len(plan),1)
            self.assertEqual((p/'Makefile').read_bytes(),before)

class StudentE10BBuildFailure(unittest.TestCase):
    def test_build_failure_rejected_and_makefile_unchanged(self):
        from lab import validate
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            p=root/'sample'
            fixture(p)
            diff,plan=patch(p,scan(p))
            candidate=root/'candidate.patch'
            candidate.write_text(diff)
            before=(p/'Makefile').read_bytes()
            (p/'main.c').write_text('this is invalid C;\n')
            result=validate(p,candidate,root/'validation')
            self.assertTrue(result['checks']['patch_applies'])
            self.assertFalse(result['checks'].get('build',False))
            self.assertIn('COMMAND_FAILED',result['error'])
            self.assertFalse(result['accepted'])
            self.assertTrue(result['rollback'])
            self.assertTrue(result['source_unchanged'])
            self.assertEqual((p/'Makefile').read_bytes(),before)

if __name__=='__main__':unittest.main()
