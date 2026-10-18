"""Read-only project context shared by the terminal workbench helpers."""
import os, subprocess
from pathlib import Path


def output(args, timeout=2):
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL, timeout=timeout)
    except (subprocess.SubprocessError, OSError):
        return None


def tm(*args):
    result = output(['tmux', *args])
    return os.fsdecode(result).rstrip('\n') if result is not None else ''


def resolve(pane, follow_source=True):
    fields = tm('display-message', '-p', '-t', pane,
                '#{window_id}\t#{session_id}\t#{@work-main}\t#{@work-source-window}\t#{pane_current_path}\t#{@work-tool-root}').split('\t')
    if len(fields) != 6:
        raise RuntimeError('Cannot resolve the originating tmux pane')
    window, session, main, source, cwd, tool_root = fields
    if follow_source:
        if source:
            main = tm('show-options', '-wv', '-t', source, '@work-main')
        if main:
            cwd = tm('display-message', '-p', '-t', main, '#{pane_current_path}') or cwd
    elif tool_root:
        cwd = tool_root
    elif main:
        cwd = tm('display-message', '-p', '-t', main, '#{pane_current_path}') or cwd
    return {'window': window, 'source': source or window, 'session': session, 'main': main, 'cwd': cwd}


def git_info(cwd, with_changes=True):
    raw = output(['git', '-C', cwd, 'rev-parse', '--show-toplevel'])
    if raw is None:
        return None
    root = os.fsdecode(raw).rstrip('\n')
    raw = output(['git', '-C', root, 'symbolic-ref', '--quiet', '--short', 'HEAD'])
    branch = os.fsdecode(raw).rstrip('\n') if raw is not None else ''
    if not branch:
        raw = output(['git', '-C', root, 'rev-parse', '--short', 'HEAD'])
        branch = 'detached:' + os.fsdecode(raw).strip() if raw else 'unborn'
    result = {'root': root, 'branch': branch, 'staged': 0, 'modified': 0,
              'untracked': 0, 'conflicts': 0, 'changes': [], 'error': False}
    if not with_changes:
        return result
    raw = output(['git', '-C', root, 'status', '--porcelain=v1', '-z', '--untracked-files=all'], timeout=3)
    if raw is None:
        result['error'] = True
        return result
    records = iter(raw.split(b'\0'))
    for record in records:
        if len(record) < 4:
            continue
        code = record[:2].decode('ascii', errors='replace')
        name = os.fsdecode(record[3:])
        if code == '!!':
            continue
        conflict = code in {'DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU'}
        if conflict:
            result['conflicts'] += 1
        elif code == '??':
            result['untracked'] += 1
        else:
            result['staged'] += code[0] != ' '
            result['modified'] += code[1] != ' '
        previous = os.fsdecode(next(records, b'')) if 'R' in code or 'C' in code else None
        try:
            changed_at = (Path(root) / name).lstat().st_mtime_ns
        except OSError:
            changed_at = 0
        result['changes'].append({'code': code, 'path': name, 'old': previous,
                                  'conflict': conflict, 'mtime': changed_at})
    result['changes'].sort(key=lambda item: (not item['conflict'], -item['mtime'], item['path']))
    return result


GENERATED = {'node_modules', 'dist', 'build', 'coverage', 'target', 'vendor',
             '.venv', 'venv', '__pycache__', '.next', '.nuxt', 'logs', '.cache'}
SOURCE = {'src', 'app', 'apps', 'backend', 'frontend', 'lib', 'packages', 'tests', 'test', 'scripts'}
ENTRY = {'agents.md', 'claude.md', 'readme.md', 'readme', 'package.json', 'pyproject.toml',
         'cargo.toml', 'go.mod', 'makefile', 'dockerfile', 'compose.yml', 'compose.yaml'}


def files(cwd, info):
    changed = set()
    if info:
        for item in info['changes']:
            for name in (item['path'], item['old']):
                if not name:
                    continue
                try:
                    changed.add((Path(info['root']) / name).relative_to(cwd).parts[0])
                except (ValueError, IndexError):
                    pass
    with os.scandir(cwd) as scan:
        entries = [entry for entry in scan if not entry.name.startswith('.') or entry.name in {'.github', '.gitignore', '.venv', '.next'}]
    def rank(entry):
        name = entry.name
        if name in GENERATED:
            return (4, 0, name.casefold())
        if name in changed:
            try:
                modified = -entry.stat(follow_symlinks=False).st_mtime_ns
            except OSError:
                modified = 0
            return (0, modified, name.casefold())
        if name in SOURCE and entry.is_dir(follow_symlinks=False):
            return (1, 0, name.casefold())
        if name.casefold() in ENTRY:
            return (2, 0, name.casefold())
        return (3, not entry.is_dir(follow_symlinks=False), name.casefold())
    return [(entry, entry.name in GENERATED, entry.name in changed) for entry in sorted(entries, key=rank)]


def clean(value):
    return ''.join(c if ord(c) >= 32 and ord(c) != 127 else ' ' for c in str(value)).encode('utf-8', errors='replace').decode('utf-8')
