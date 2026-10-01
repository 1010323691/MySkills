"""Read-only structural checks. Does not validate project semantics or execute commands."""
import argparse
import json
from pathlib import Path
import re
import sys

PROTOCOL = 'context-protocol/v2'
CORE = {'README.md': 60, 'PROJECT.md': 120, 'CURRENT.md': 100, 'ROUTES.md': 80}

def check(project_root, context_dir='docs/agent-context', limit=20):
    root = Path(project_root).resolve()
    raw = Path(context_dir)
    if raw.is_absolute() or '..' in raw.parts:
        raise ValueError('context-dir must be a relative path without ..')
    docs = (root / raw).resolve()
    if not docs.is_relative_to(root) or docs == root:
        raise ValueError('context directory escapes or equals project root')
    if not root.is_dir():
        raise ValueError('project root does not exist')
    issues, checked, total_lines = [], 0, 0
    def issue(level, code, path, line=None):
        item = {'level':level, 'code':code, 'path':str(path)}
        if line is not None:
            item['line'] = line
        issues.append(item)
    for name in CORE:
        if (docs / name).is_symlink():
            issue('error', 'core_symlink_not_supported', name)
        elif not (docs / name).is_file():
            issue('error', 'missing_core', name)
    if docs.is_dir():
        # Do not follow directory symlinks or inspect other project files.
        paths = []
        stack = [docs]
        while stack:
            current = stack.pop()
            for item in sorted(current.iterdir()):
                if item.is_symlink():
                    issue('warning', 'symlink_not_scanned', item.relative_to(docs))
                    continue
                if item.is_dir():
                    stack.append(item)
                elif item.is_file() and item.suffix == '.md':
                    paths.append(item)
        for path in paths:
            rel = path.relative_to(docs)
            if path.stat().st_size > 512 * 1024:
                issue('warning', 'large_file_not_scanned', rel)
                continue
            try:
                content = path.read_text(encoding='utf-8')
            except (UnicodeError, OSError):
                issue('error', 'unreadable_markdown', rel)
                continue
            checked += 1
            lines = content.splitlines()
            total_lines += len(lines)
            if rel.as_posix() in CORE:
                if f'协议：{PROTOCOL}' not in content:
                    issue('warning', 'unknown_or_old_protocol', rel)
                if len(lines) > CORE[rel.as_posix()]:
                    issue('warning', 'core_line_budget', rel)
            if rel.as_posix() == 'CURRENT.md':
                state = re.search(r'^交接保存状态：[ \t]*(complete|partial)[ \t]*$', content, re.M)
                if not state:
                    issue('error', 'invalid_save_state', rel)
                elif state.group(1) == 'partial':
                    issue('warning', 'partial_handoff', rel)
            fence = None
            for number, line in enumerate(lines, 1):
                marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
                if marker:
                    mark = marker.group(1)
                    if fence is None:
                        fence = mark
                    elif mark[0] == fence[0] and len(mark) >= len(fence):
                        fence = None
                    continue
                if fence:
                    continue
                # Supports simple inline file links; anchors/complex Markdown are not validated.
                for match in re.finditer(r'\[[^\]\n]*\]\(([^()\s]+)\)', line):
                    target = match.group(1)
                    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                        continue
                    filename = target.split('#', 1)[0]
                    if not filename:
                        continue
                    if '<' in filename or '>' in filename:
                        issue('warning', 'unfilled_link_placeholder', rel, number)
                        continue
                    resolved = (path.parent / filename).resolve()
                    if Path(filename).is_absolute() or not resolved.is_relative_to(root):
                        issue('warning', 'nonportable_or_external_file_link', rel, number)
                    elif not resolved.exists():
                        issue('error', 'missing_link_target', rel, number)
            if fence is not None:
                issue('error', 'unclosed_code_fence', rel)
    return {
        'protocol':PROTOCOL, 'scope':str(docs), 'markdown_files_checked':checked,
        'lines_checked':total_lines, 'issues':issues[:limit], 'issue_count':len(issues),
        'has_more_issues':len(issues)>limit, 'errors':sum(x['level']=='error' for x in issues),
        'warnings':sum(x['level']=='warning' for x in issues),
        'limitations':['no_semantic_validation','no_token_count','no_id_or_anchor_validation',
                       'simple_inline_file_links_only','no_secret_detection','no_command_execution']
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True)
    p.add_argument('--context-dir', default='docs/agent-context')
    p.add_argument('--limit', type=int, default=20)
    a = p.parse_args()
    if not 1 <= a.limit <= 100:
        p.error('--limit must be 1..100')
    try:
        result = check(a.root, a.context_dir, a.limit)
    except (OSError, ValueError) as exc:
        print(json.dumps({'error':str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['errors'] else 0

if __name__ == '__main__':
    sys.exit(main())
