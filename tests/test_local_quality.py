"""Host-quality falsifiers run without Docker, Entire, or Sims installed."""
from __future__ import annotations
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from scripts import local_quality as q


class HostQualityTests(unittest.TestCase):
    def manifest(self):
        return {'schema': q.SCHEMA, 'default_image': q.IMAGE,
                'checks': [{'id': 'check-' + str(i), 'argv': ['python', '-m', 'unittest', 'tests.test_' + str(i)],
                            'timeout_seconds': 120} for i in range(49)]}

    def test_required_contract_and_single_check_validation(self):
        m = self.manifest()
        self.assertEqual(len(q.validate_contract(m)), 49)
        m['checks'][0]['argv'] = ['git', 'reset', '--hard']
        with self.assertRaisesRegex(ValueError, 'EXECUTABLE_NOT_ALLOWLISTED'):
            q.validate_contract(m)

    def test_legacy_workflow_commands_are_exact_and_base_aware(self):
        wf = '''run: python -m scripts.check_ontology\n    python -m scripts.check_ontology --base-ref "$PR_BASE_SHA"\n    python -m scripts.host_eval --out dist/out.json > /dev/null\n    python -m pip install Pillow\n    git diff --check "$BASE...HEAD"\n'''
        self.assertEqual(q.legacy_commands(wf), [
            ('python', '-m', 'scripts.check_ontology'),
            ('python', '-m', 'scripts.check_ontology', '--base-ref', '{base_sha}'),
            ('python', '-m', 'scripts.host_eval', '--out', 'dist/out.json'),
            ('git', 'diff', '--check', '{base_sha}...HEAD')])

    def test_added_or_removed_ci_check_fails_closed(self):
        m = self.manifest()
        wf = '\n'.join('run: ' + ' '.join(c['argv']) for c in m['checks'])
        q.validate_contract(m, workflow_text=wf)
        with self.assertRaisesRegex(ValueError, 'WORKFLOW_PARITY_FAIL'):
            q.validate_contract(m, workflow_text=wf + '\nrun: python -m scripts.new_guard\n')
        with self.assertRaisesRegex(ValueError, 'WORKFLOW_PARITY_FAIL'):
            q.validate_contract(m, workflow_text='\n'.join(wf.splitlines()[:-1]))

    def test_host_cannot_be_tricked_into_worker_execution(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'WORKER_NEEDS_SANDBOX'):
                q.worker(Path('.'), self.manifest(), 'a' * 40)

    def test_git_archive_refuses_traversal_and_link_entries(self):
        def archive(name, *, link=False):
            f = io.BytesIO()
            with tarfile.open(fileobj=f, mode='w') as t:
                item = tarfile.TarInfo(name)
                item.type = tarfile.SYMTYPE if link else tarfile.REGTYPE
                item.size = 0
                t.addfile(item)
            return f.getvalue()
        with tempfile.TemporaryDirectory() as dest:
            for candidate in ('../outside.txt', '/tmp/absolute.txt', 'a/../../out.txt',
                              r'..\outside.txt', r'C:\Windows\bad.txt',
                              r'a\..\..\out.txt', 'bad:name.txt'):
                with self.subTest(candidate=candidate), self.assertRaisesRegex(ValueError, 'UNSAFE_ARCHIVE_PATH'):
                    q.safe_extract_git_archive(archive(candidate), dest)
            with self.assertRaisesRegex(ValueError, 'UNSAFE_ARCHIVE_ENTRY'):
                q.safe_extract_git_archive(archive('linked', link=True), dest)

    def test_entire_missing_disabled_or_upload_unconfirmed_denies(self):
        correct = [
            {'code': 0, 'stdout': '{}'},
            {'code': 0, 'stdout': '{"enabled":true,"checkpoint_push_disabled":true}'},
            {'code': 0, 'stdout': '[]'}]
        def fake(args, **kw):
            n = {'agent-help': 0, 'status': 1, 'checkpoint': 2}[args[1]]
            x = dict(correct[n]); x['stdout_hash'] = q.digest(x['stdout']); return x
        with mock.patch.object(q, 'run_command', side_effect=fake):
            self.assertTrue(q.entire_probe(Path('.'))['ready'])
        correct[1]['stdout'] = '{"enabled":true}'
        with mock.patch.object(q, 'run_command', side_effect=fake):
            self.assertEqual(q.entire_probe(Path('.'))['reason'], 'CHECKPOINT_PRIVACY_UNCONFIRMED')
        correct[1]['stdout'] = '{"enabled":false,"checkpoint_push_disabled":true}'
        with mock.patch.object(q, 'run_command', side_effect=fake):
            self.assertEqual(q.entire_probe(Path('.'))['reason'], 'ENTIRE_DISABLED')
        correct[1]['stdout'] = '{"enabled":true,"checkpoint_push_disabled":true}'
        correct[2]['code'] = 1
        with mock.patch.object(q, 'run_command', side_effect=fake):
            self.assertEqual(q.entire_probe(Path('.'))['reason'], 'ENTIRE_COMMAND_FAILED')

    def test_disposable_sandbox_is_networkless_nonprivileged_and_readonly(self):
        manifest = self.manifest()
        calls = []
        def fake(args, **kw):
            calls.append(args)
            return {'code': 0, 'stdout': 'sha256:'+'a'*64 if 'inspect' in args else '',
                    'stderr': '', 'stdout_hash': 'x', 'stderr_hash': 'y'}
        with mock.patch.object(q, 'git_info', return_value={'git_dir': '/safe/git', 'common_dir': '/safe/common'}), \
             mock.patch.object(q, 'run_command', side_effect=fake):
            q.sandbox(Path('/safe/repo'), Path('/safe/stage'), manifest, 'a' * 40,
                      engine='docker', image=q.IMAGE)
        joined = ' '.join(calls[-1])
        self.assertIn('sha256:'+'a'*64, joined)
        for token in ('--network=none', '--read-only', '--cap-drop=ALL',
                      '--security-opt=no-new-privileges', '--user=65534:65534',
                      '--pull=never', 'BI_LOCAL_QUALITY_ISOLATED=1',
                      'GIT_CONFIG_COUNT=1', 'GIT_CONFIG_KEY_0=safe.directory',
                      'GIT_CONFIG_VALUE_0=/work',
                      'type=bind,src=/safe/stage,dst=/src,readonly'):
            self.assertIn(token, joined)
        for forbidden in ('--privileged', '--network=host', 'entire enable', 'git push'):
            self.assertNotIn(forbidden, joined)

    def test_receipt_stays_out_of_repository(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict('os.environ', {'XDG_STATE_HOME': tmp}):
            path = q.private_receipt(Path('/repo'), {'head': 'a' * 40, 'status': 'FAIL_CLOSED'})
            self.assertEqual(path.parent, Path(tmp) / 'BetterInstincts' / 'host-quality')
            self.assertEqual(json.loads(path.read_text())['status'], 'FAIL_CLOSED')

    def test_exact_safe_base_reference_command_only(self):
        m = self.manifest()
        m['checks'][0]['argv'] = ['git', 'diff', '--check', '{base_sha}...HEAD']
        q.validate_contract(m)
        m['checks'][0]['argv'] = ['git', 'clean', '-fdx']
        with self.assertRaisesRegex(ValueError, 'EXECUTABLE_NOT_ALLOWLISTED'):
            q.validate_contract(m)


    def test_actual_repository_matrix_covers_every_existing_actions_check(self):
        root = q.ROOT
        manifest = json.loads((root / q.CONTRACT).read_text(encoding='utf-8'))
        workflow = root / '.github/workflows/ci.yml'
        checks = q.validate_contract(
            manifest, workflow_text=workflow.read_text(encoding='utf-8') if workflow.exists() else None)
        self.assertEqual(len(checks), 49)
        self.assertEqual(sum(c['argv'][0] == 'git' for c in checks), 2)
        self.assertEqual(sum(c['argv'][0] == 'python' for c in checks), 47)



    def test_real_subprocess_stdout_cap_and_timeout(self):
        import sys
        too_much = q.run_command([sys.executable, '-c', "print('x'*2000000)"], timeout=5)
        self.assertEqual(too_much['code'], 124)
        self.assertEqual(too_much['stderr'], 'OUTPUT_LIMIT')
        self.assertEqual(too_much['stdout'], '')
        slow = q.run_command([sys.executable, '-c', 'import time;time.sleep(3)'], timeout=1)
        self.assertEqual(slow['code'], 124)
        self.assertEqual(slow['stderr'], 'TIMEOUT')



    def test_repo_executable_shadowing_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'docker'
            fake.write_text('not a trusted binary')
            with mock.patch.object(q.shutil, 'which', return_value=str(fake)):
                with self.assertRaisesRegex(ValueError, 'UNTRUSTED_HOST_EXECUTABLE'):
                    q.trusted_executable('docker', Path(tmp))

    def test_image_identity_must_be_immutable(self):
        data = self.manifest()
        def bad(args, **kw):
            return {'code': 0, 'stdout': 'unverified:latest', 'stderr': '',
                    'stdout_hash': 'x', 'stderr_hash': 'y'}
        with mock.patch.object(q, 'git_info', return_value={'git_dir': '/gitdir', 'common_dir': '/gitcommon'}), \
             mock.patch.object(q, 'run_command', side_effect=bad):
            with self.assertRaisesRegex(ValueError, 'LOCAL_SANDBOX_IMAGE_ID_UNVERIFIED'):
                q.sandbox(Path('/repo'), Path('/stage'), data, 'a'*40,
                          engine='docker', image=q.IMAGE)



    def test_minimum_baseline_cannot_shrink_after_actions_sunset(self):
        m = self.manifest()
        m['checks'] = m['checks'][:48]
        with self.assertRaisesRegex(ValueError, 'REQUIRED_CHECKS_MISSING'):
            q.validate_contract(m)

    def test_readonly_plan_does_not_execute_entire_or_docker(self):
        import contextlib
        import io as _io
        original = q.ROOT
        report = _io.StringIO()
        with mock.patch.object(q, '__file__', '/trusted/operator/local_quality.py'), \
             mock.patch.object(q, 'git_info', return_value={'head': 'a' * 40}), \
             mock.patch.object(q, 'entire_probe', side_effect=AssertionError('entire must not run')), \
             mock.patch.object(q, 'sandbox', side_effect=AssertionError('sandbox must not run')), \
             contextlib.redirect_stdout(report):
            self.assertEqual(q.main(['plan']), 0)
        self.assertEqual(json.loads(report.getvalue())['check_count'], 49)
        self.assertEqual(original, q.ROOT)



    def test_host_run_cannot_execute_agent_editable_repo_launcher(self):
        with mock.patch.object(q, 'git_info', return_value={'head': 'a'*40}), \
             mock.patch.object(q, 'entire_probe', side_effect=AssertionError('Entire must not run')):
            with self.assertRaisesRegex(ValueError, 'TRUSTED_RUNNER_OUTSIDE_REPOSITORY_REQUIRED'):
                q.main(['run', '--authorize', '--base-sha', 'b'*40,
                        '--expected-head', 'a'*40])



    def test_even_plan_refuses_untrusted_mutable_checkout_script(self):
        with mock.patch.object(q, 'git_info', side_effect=AssertionError('must deny before git')):
            with self.assertRaisesRegex(ValueError, 'TRUSTED_RUNNER_OUTSIDE_REPOSITORY_REQUIRED'):
                q.main(['plan'])



if __name__ == '__main__':
    unittest.main()
