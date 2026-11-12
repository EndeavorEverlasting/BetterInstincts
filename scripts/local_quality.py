"""BetterInstincts offline quality harness: local, Entire-observed, sandbox-only.

No agent or repository tests run with desktop privileges. Entire provides session
provenance, not execution authority or an OS sandbox. No Entire settings change.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path('contracts/local-quality-checks.v1.json')
IMAGE = 'betterinstincts-policy:py311-pillow'
SCHEMA = 'betterinstincts.local-quality/v1'
BOOTSTRAP = ("import os,runpy,shutil,sys; "
             "shutil.copytree('/src','/work',dirs_exist_ok=True,symlinks=False); "
             "os.chdir('/work'); sys.path.insert(0,'/work'); "
             "runpy.run_module('scripts.local_quality',run_name='__main__')")


def digest(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8', 'replace')).hexdigest()


def run_command(argv, *, cwd=ROOT, timeout=30):
    try:
        p = subprocess.run(argv, cwd=cwd, timeout=timeout, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors='replace', shell=False)
        return {'code': p.returncode, 'stdout_hash': digest(p.stdout),
                'stderr_hash': digest(p.stderr), 'stdout': p.stdout, 'stderr': p.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'code': 124 if isinstance(exc, subprocess.TimeoutExpired) else 127,
                'stdout_hash': digest(''), 'stderr_hash': digest(type(exc).__name__),
                'stdout': '', 'stderr': type(exc).__name__}


def normalized(tokens):
    """Compare old CI command coverage, normalizing only variable base SHA."""
    a = list(tokens)
    if '--base-ref' in a:
        ix = a.index('--base-ref')
        if ix + 1 != len(a) - 1:
            raise ValueError('BAD_BASE_REF_FORM')
        a[ix + 1] = '{base_sha}'
    return tuple(a)


def legacy_commands(text):
    cmds = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('run: '):
            line = line[5:]
        if not (line.startswith('python ') or line.startswith('git diff --check')):
            continue
        if line.startswith('python -m pip install'):
            continue  # Build-time dependency provision, not a quality check.
        if ' > /dev/null' in line:
            line = line.split(' > /dev/null', 1)[0]
        parts = shlex.split(line)
        if parts[:2] == ['git', 'diff']:
            cmds.append(('git', 'diff', '--check', '{base_sha}...HEAD'))
        else:
            cmds.append(normalized(parts))
    return cmds


def validate_contract(manifest, *, workflow_text=None):
    if manifest.get('schema') != SCHEMA or manifest.get('default_image') != IMAGE:
        raise ValueError('CONTRACT_OR_IMAGE_INVALID')
    checks = manifest.get('checks')
    if not isinstance(checks, list) or len(checks) < 30:
        raise ValueError('REQUIRED_CHECKS_MISSING')
    names = set()
    for row in checks:
        if not isinstance(row, dict) or set(row) != {'id', 'argv', 'timeout_seconds'}:
            raise ValueError('CHECK_SHAPE_INVALID')
        name, argv, timeout = row['id'], row['argv'], row['timeout_seconds']
        if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9-]{3,64}', name) or name in names:
            raise ValueError('DUPLICATE_OR_INVALID_CHECK_ID')
        names.add(name)
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x or '\x00' in x for x in argv):
            raise ValueError('CHECK_ARGV_INVALID')
        if argv[0] != 'python' and argv != ['git', 'diff', '--check', '{base_sha}...HEAD']:
            raise ValueError('CHECK_EXECUTABLE_NOT_ALLOWLISTED')
        if argv[0] == 'python' and (len(argv) < 2 or (argv[1] == '-m' and len(argv) < 3) or (argv[1] != '-m' and not argv[1].startswith('scripts/'))):
            raise ValueError('CHECK_PYTHON_FORM_INVALID')
        if not isinstance(timeout, int) or not 1 <= timeout <= 300:
            raise ValueError('CHECK_TIMEOUT_INVALID')
    if workflow_text is not None:
        expected = legacy_commands(workflow_text)
        actual = [tuple(c['argv']) for c in checks]
        from collections import Counter
        if Counter(expected) != Counter(actual):
            missing = Counter(expected) - Counter(actual)
            extra = Counter(actual) - Counter(expected)
            raise ValueError('WORKFLOW_PARITY_FAIL: missing=' + repr(dict(missing)) + ' extra=' + repr(dict(extra)))
    return checks


def git_info(root):
    def exact(args):
        r = run_command(['git', '-C', str(root), *args], cwd=root, timeout=20)
        if r['code']:
            raise ValueError('GIT_EVIDENCE_UNAVAILABLE:' + ' '.join(args))
        return r['stdout'].strip()
    head = exact(['rev-parse', 'HEAD'])
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('INVALID_GIT_HEAD')
    if exact(['status', '--porcelain']):
        raise ValueError('DIRTY_TREE_DENIED:commit a reviewed candidate first')
    # No git fetch/push/rebase/checkout or remote network request.
    return {'head': head,
            'git_dir': exact(['rev-parse', '--absolute-git-dir']),
            'common_dir': exact(['rev-parse', '--path-format=absolute', '--git-common-dir'])}


def entire_probe(root):
    commands = [['entire', 'agent-help', '--json'], ['entire', 'status', '--json'],
                ['entire', 'checkpoint', 'list', '--json']]
    out = [run_command(c, cwd=root) for c in commands]
    evidence = [{'argv': c[1:], 'code': r['code'], 'stdout_sha256': r['stdout_hash']}
                for c, r in zip(commands, out)]
    try:
        help_json = json.loads(out[0]['stdout'])
        status = json.loads(out[1]['stdout'])
        checkpoint_json = json.loads(out[2]['stdout'])
    except (ValueError, TypeError):
        return {'ready': False, 'reason': 'ENTIRE_DISCOVERY_UNAVAILABLE', 'probes': evidence}
    if any(r['code'] for r in out) or not isinstance(help_json, (dict, list)) or not isinstance(checkpoint_json, (dict, list)):
        return {'ready': False, 'reason': 'ENTIRE_COMMAND_FAILED', 'probes': evidence}
    if not isinstance(status, dict) or status.get('enabled') is not True:
        return {'ready': False, 'reason': 'ENTIRE_DISABLED', 'probes': evidence}
    # BetterInstincts is a public repository: prevent incidental transcript publication.
    # Never enable/configure/uploads from this program.
    if status.get('checkpoint_push_disabled') is not True:
        return {'ready': False, 'reason': 'CHECKPOINT_PRIVACY_UNCONFIRMED', 'probes': evidence}
    return {'ready': True, 'reason': 'LOCAL_ONLY', 'probes': evidence,
            'checkpoint_snapshot_sha256': out[2]['stdout_hash']}


def safe_extract_git_archive(archive, destination):
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tf:
        for member in tf.getmembers():
            p = PurePosixPath(member.name)
            if p.is_absolute() or any(part in ('..', '.') for part in p.parts):
                raise ValueError('UNSAFE_ARCHIVE_PATH')
            if not (member.isfile() or member.isdir()):
                raise ValueError('UNSAFE_ARCHIVE_ENTRY')
        tf.extractall(destination, filter='data')


def worker(root, manifest, base):
    if os.environ.get('BI_LOCAL_QUALITY_ISOLATED') != '1' or not Path('/src').is_dir():
        raise ValueError('WORKER_NEEDS_SANDBOX')
    # The host has already validated this same reviewed manifest. Verify again
    # in the disposable container; each check runs with NO host device access.
    checks = validate_contract(manifest)
    results = []
    for check in checks:
        args = [x.replace('{base_sha}', base) for x in check['argv']]
        result = run_command(args, cwd=root, timeout=check['timeout_seconds'])
        results.append({'id': check['id'], 'pass': result['code'] == 0,
                        'exit_code': result['code'], 'stdout_sha256': result['stdout_hash'],
                        'stderr_sha256': result['stderr_hash']})
    return {'schema': 'betterinstincts.local-quality-receipt/v1',
            'passed': sum(r['pass'] for r in results), 'total': len(results),
            'checks': results, 'all_pass': all(r['pass'] for r in results)}


def sandbox(root, stage, manifest, base, *, engine, image, timeout=1800):
    if engine not in ('docker', 'podman') or not re.fullmatch(r'[A-Za-z0-9_./:-]{5,128}', image):
        raise ValueError('SANDBOX_ENGINE_OR_IMAGE_INVALID')
    gi = git_info(root)
    image_check = run_command([engine, 'image', 'inspect', image], cwd=root)
    if image_check['code']:
        raise ValueError('LOCAL_SANDBOX_IMAGE_NOT_PRESENT_NO_PULL')
    argv = [engine, 'run', '--rm', '--pull=never', '--network=none', '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=256',
            '--memory=1536m', '--cpus=2', '--user=65534:65534',
            '--mount', f'type=bind,src={stage},dst=/src,readonly',
            '--mount', f'type=bind,src={gi["git_dir"]},dst=/gitdir,readonly',
            '--mount', f'type=bind,src={gi["common_dir"]},dst=/gitcommon,readonly',
            '--tmpfs', '/work:rw,nosuid,nodev,mode=1777,size=512m',
            '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777,size=256m',
            '-e', 'BI_LOCAL_QUALITY_ISOLATED=1',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'GIT_DIR=/gitdir',
            '-e', 'GIT_COMMON_DIR=/gitcommon', '-e', 'GIT_WORK_TREE=/work',
            '-e', 'HOME=/tmp', '--workdir', '/work', '--entrypoint', 'python',
            image, '-c', BOOTSTRAP, 'run', '--worker', '--base-sha', base]
    return run_command(argv, cwd=root, timeout=timeout)


def private_receipt(root, obj):
    home = os.environ.get('LOCALAPPDATA') if os.name == 'nt' else os.environ.get('XDG_STATE_HOME')
    if not home:
        home = str(Path.home() / '.local' / 'state')
    target = Path(home) / 'BetterInstincts' / 'host-quality'
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = str(obj['head'])[:12] + '-' + str(os.getpid()) + '.json'
    temp = target / (name + '.tmp')
    final = target / name
    with temp.open('x', encoding='utf-8') as f:
        json.dump(obj, f, sort_keys=True, indent=2)
    temp.replace(final)
    return final


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['plan', 'run'])
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--base-sha')
    p.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    p.add_argument('--image', default=IMAGE)
    p.add_argument('--authorize', action='store_true')
    a = p.parse_args(argv)
    manifest = json.loads((ROOT / CONTRACT).read_text(encoding='utf-8'))
    workflow = ROOT / '.github' / 'workflows' / 'ci.yml'
    checks = validate_contract(manifest, workflow_text=workflow.read_text(encoding='utf-8') if workflow.exists() else None)
    if a.worker:
        if not a.base_sha or not re.fullmatch('[a-f0-9]{40}', a.base_sha):
            raise ValueError('BASE_SHA_REQUIRED')
        data = worker(ROOT, manifest, a.base_sha)
        print(json.dumps(data, sort_keys=True))
        return 0 if data['all_pass'] else 1
    git = git_info(ROOT)
    summary = {'head': git['head'], 'check_count': len(checks),
               'checks_contract_sha256': digest((ROOT / CONTRACT).read_text(encoding='utf-8')),
               'workflow_parity': 'PASS' if workflow.exists() else 'LEGACY_WORKFLOW_ABSENT'}
    if a.command == 'plan':
        print(json.dumps(summary, sort_keys=True)); return 0
    if not a.authorize or not a.base_sha or not re.fullmatch('[a-f0-9]{40}', a.base_sha):
        raise ValueError('EXPLICIT_AUTHORIZE_AND_BASE_SHA_REQUIRED')
    if not run_command(['git', 'cat-file', '-e', a.base_sha + '^{commit}'], cwd=ROOT)['code'] == 0:
        raise ValueError('UNKNOWN_BASE_COMMIT')
    entire_before = entire_probe(ROOT)
    if not entire_before['ready']:
        raise ValueError(entire_before['reason'])
    with tempfile.TemporaryDirectory(prefix='bi-isolated-checks-') as temp:
        # The sandbox runs as an unprivileged UID: expose only staged, committed
        # source with traversable directory permissions; never the live checkout.
        os.chmod(temp, 0o755)
        stage = Path(temp) / 'source'; stage.mkdir(mode=0o755)
        os.chmod(stage, 0o755)
        proc = subprocess.run(['git', 'archive', '--format=tar', 'HEAD'], cwd=ROOT,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        if proc.returncode or len(proc.stdout) > 128 * 1024 * 1024:
            raise ValueError('GIT_ARCHIVE_UNAVAILABLE_OR_OVERSIZED')
        safe_extract_git_archive(proc.stdout, stage)
        outcome = sandbox(ROOT, stage, manifest, a.base_sha, engine=a.engine, image=a.image)
    entire_after = entire_probe(ROOT)
    try:
        report = json.loads(outcome['stdout'].strip().splitlines()[-1])
        if report.get('schema') != 'betterinstincts.local-quality-receipt/v1':
            raise ValueError()
    except (ValueError, IndexError, AttributeError):
        report = {'all_pass': False, 'reason': 'SANDBOX_REPORT_MISSING'}
    pass_state = outcome['code'] == 0 and report['all_pass'] is True and entire_after['ready']
    receipt = {**summary, 'base_sha': a.base_sha, 'sandbox': {'engine': a.engine, 'image': a.image,
               'exit_code': outcome['code'], 'stdout_sha256': outcome['stdout_hash'],
               'stderr_sha256': outcome['stderr_hash']},
               'entire_before': entire_before, 'entire_after': entire_after,
               'checks': report, 'status': 'LOCAL_OFFLINE_CHECKS_PASS' if pass_state else 'FAIL_CLOSED',
               'gameplay_certified': False, 'windows_peripherals_certified': False,
               'github_actions_required_for_execution': False}
    receipt_path = private_receipt(ROOT, receipt)
    print(json.dumps({'status': receipt['status'], 'passed': report.get('passed', 0),
                      'total': report.get('total', 0), 'private_receipt': str(receipt_path)}))
    return 0 if pass_state else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'status': 'FAIL_CLOSED', 'reason': str(exc)}), file=sys.stderr)
        sys.exit(2)
