#!/usr/bin/env python3
"""Regression tests using temporary repositories, a private tmux socket and fake tools."""
import importlib.util, json, os, re, runpy, shlex, shutil, subprocess, sys, tempfile, time, unittest, uuid, pty, fcntl, termios, struct
from pathlib import Path
from unittest.mock import patch

BUNDLE = Path(__file__).resolve().parents[1]
ASSETS = BUNDLE/'assets/home'
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='workbench regression ')
        cls.home = Path(cls.scratch.name)/'home with spaces'
        shutil.copytree(ASSETS, cls.home)
        cls.socket = 'workbench-test-' + uuid.uuid4().hex[:10]
        cls.bin = cls.home/'test-bin'; cls.bin.mkdir()
        (cls.bin/'tmux').write_text('#!/bin/sh\nexec /usr/bin/tmux -L '+shlex.quote(cls.socket)+' -f /dev/null "$@"\n')
        (cls.bin/'tmux').chmod(0o755)
        fake = '#!/usr/bin/python3\nimport os,signal\nprint("READY "+os.getcwd(),flush=True)\nsignal.pause()\n'
        for path in (cls.bin/'lazygit', cls.home/'.local/bin/btm'):
            path.write_text(fake); path.chmod(0o755)
        cls.env = dict(os.environ, HOME=str(cls.home), PATH=str(cls.bin)+':'+os.environ['PATH'], TERM='xterm-256color')
        cls.env.pop('TMUX', None); cls.env.pop('TMUX_PANE', None)
        cls.environment = patch.dict(os.environ, cls.env, clear=True); cls.environment.start()
        cls.path_patch = patch.object(sys, 'path', [str(cls.home/'.local/lib/terminal-workbench'), *sys.path]); cls.path_patch.start()
        import workbench_context
        cls.context = workbench_context
        cls.sidebar = runpy.run_path(str(cls.home/'.local/bin/terminal-sidebar'))
        cls.repo = cls.home/'project A'; cls.repo.mkdir()
        cls.git(cls.repo, 'init', '-q', '-b', 'main')
        cls.git(cls.repo, 'config', 'user.name', 'Workbench Test')
        cls.git(cls.repo, 'config', 'user.email', 'workbench@example.invalid')
        for name in ('staged.txt', 'modified.txt', 'both.txt', 'rename old.txt', 'conflict.txt'):
            (cls.repo/name).write_text('base\n')
        cls.git(cls.repo, 'add', '.'); cls.git(cls.repo, 'commit', '-qm', 'baseline')
        for name in ('staged.txt', 'modified.txt', 'both.txt'):
            (cls.repo/name).write_text('changed\n')
        cls.git(cls.repo, 'add', 'staged.txt', 'both.txt')
        (cls.repo/'both.txt').write_text('changed again\n')
        cls.git(cls.repo, 'mv', 'rename old.txt', 'rename new.txt')
        (cls.repo/'new\nfile.txt').write_text('new\n')
        # Create an actual unmerged index entry without changing any user repository.
        blob = cls.git(cls.repo, 'rev-parse', 'HEAD:conflict.txt').strip()
        cls.git(cls.repo, 'update-index', '--force-remove', 'conflict.txt')
        stages = ''.join(f'100644 {blob} {stage}\tconflict.txt\n' for stage in (1, 2, 3))
        subprocess.run(['git', '-C', str(cls.repo), 'update-index', '--index-info'], input=stages, text=True, check=True, env=cls.env)
        for name in ('src', 'backend', 'node_modules', 'dist', 'docs'):
            (cls.repo/name).mkdir()
        (cls.repo/'AGENTS.md').write_text('instructions\n')
        (cls.repo/'.gitignore').write_text('node_modules/\ndist/\n')
        for index in range(200):
            (cls.repo/f'folder-{index:03}').mkdir()
        cls.other = cls.home/'project B'; cls.other.mkdir()
        cls.git(cls.other, 'init', '-q', '-b', 'other')
        cls.pane = cls.tm('new-session', '-d', '-P', '-F', '#{pane_id}', '-s', 'test', '-x', '90', '-y', '30', '-c', str(cls.repo), '/bin/bash --noprofile --norc').strip()
        cls.window = cls.tm('display-message', '-p', '-t', cls.pane, '#{window_id}').strip()
        cls.tm('set-option', '-w', '-t', cls.window, '@work-main', cls.pane)

    @classmethod
    def git(cls, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True, env=cls.env)

    @classmethod
    def tm(cls, *args):
        return subprocess.check_output([str(cls.bin/'tmux'), *args], text=True, env=cls.env)

    @classmethod
    def tearDownClass(cls):
        subprocess.run([str(cls.bin/'tmux'), 'kill-server'], env=cls.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.path_patch.stop(); cls.environment.stop(); cls.scratch.cleanup()

    def tool(self, kind):
        subprocess.run([str(self.home/'.local/bin/terminal-tool'), kind, str(self.repo), self.pane], env=self.env, check=True)
        return self.tm('display-message', '-p', '#{pane_id}').strip()

    def wait_for(self, predicate):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(.05)
        self.fail('Timed out waiting for isolated tool state')

    def test_01_git_summary_and_priority(self):
        info = self.context.git_info(str(self.repo))
        self.assertEqual((info['staged'], info['modified'], info['untracked'], info['conflicts']), (3, 2, 3, 1))
        rename = next(item for item in info['changes'] if item['path']=='rename new.txt')
        self.assertEqual(rename['old'], 'rename old.txt')
        self.assertTrue(any(item['path']=='new\nfile.txt' for item in info['changes']))
        names = [entry.name for entry, _, _ in self.context.files(str(self.repo), info)]
        self.assertLess(names.index('modified.txt'), names.index('src'))
        self.assertLess(names.index('src'), names.index('folder-000'))
        self.assertLess(names.index('AGENTS.md'), names.index('folder-000'))
        self.assertGreater(names.index('node_modules'), names.index('folder-199'))
        self.assertGreater(names.index('dist'), names.index('folder-199'))

    def test_02_sidebar_height_and_context(self):
        for height in (10, 12, 16, 18, 24, 47, 80):
            with self.subTest(height=height), patch('shutil.get_terminal_size', return_value=os.terminal_size((60, height))):
                text = ANSI.sub('', self.sidebar['draw'](self.window))
                self.assertLessEqual(len(text.split('\r\n'))-1, height-1)
                for key in ('项目状态', 'Ctrl+b f', 'Ctrl+b p', 'Ctrl+b g', 'Ctrl+b m'):
                    self.assertIn(key, text)
                if height >= 16:
                    self.assertIn('已暂存 3', text)
                    self.assertIn('冲突 1', text)
                if height >= 24:
                    self.assertIn('[冲突] conflict.txt', text)

    def test_02_readable_file_states(self):
        label = self.sidebar['change_label']
        for code, expected in [('??', '新增'), (' M', '未暂存·修改'), ('M ', '已暂存·修改'),
                               ('MM', '暂存后又改动'), ('R ', '已暂存·重命名'), (' D', '未暂存·删除'), ('UU', '冲突')]:
            with self.subTest(code=code):
                self.assertEqual(label({'code': code, 'conflict': code=='UU'}), expected)
        # One untracked file should read as a new file, not a pair of question marks.
        info = dict(root=str(self.repo), branch='main', staged=0, modified=0, untracked=1,
                    conflicts=0, error=False, changes=[{'code':'??', 'path':'new.txt', 'old':None, 'conflict':False, 'mtime':0}])
        with patch.dict(self.sidebar['draw'].__globals__, git_info=lambda cwd:info), patch('shutil.get_terminal_size', return_value=os.terminal_size((60, 47))):
            text = ANSI.sub('', self.sidebar['draw'](self.window))
        self.assertIn('待提交 1 个文件', text)
        self.assertIn('[新增] new.txt', text)
        self.assertNotIn('??', text)

    def test_02_filename_truncation(self):
        fit = self.sidebar['fit']
        for width in (0, 1, 2, 8, 25, 55):
            with self.subTest(width=width):
                text = fit('src/views/textformat/' + 'ChapterIssuesPanel'*10 + '.vue', width)
                self.assertLessEqual(len(text), width)
                self.assertLessEqual(text.count('…'), 1)
        self.assertEqual(fit('文件.txt', 8), '文件.txt')
        self.assertEqual(fit('中文文件名.txt', 8), '中文文…')
        self.assertEqual(fit('e\u0301'*20, 5), 'e\u0301'*4+'…')
        # A long Git path must not wrap or leave repeated ellipses in the rendered pane.
        info = dict(root=str(self.repo), branch='main', staged=0, modified=1, untracked=0,
                    conflicts=0, error=False, changes=[{'code':' M', 'path':'src/'+'long-file-name'*20+'.vue', 'old':None, 'conflict':False, 'mtime':0}])
        for width in (30, 60, 100):
            with self.subTest(pane_width=width), patch.dict(self.sidebar['draw'].__globals__, git_info=lambda cwd:info), patch('shutil.get_terminal_size', return_value=os.terminal_size((width, 47))):
                text = ANSI.sub('', self.sidebar['draw'](self.window))
                for row in text.split('\r\n'):
                    self.assertNotIn('……', row)
                    # All emitted rows fit, counting Chinese glyphs as two cells.
                    import unicodedata
                    cells = sum(0 if unicodedata.combining(c) else (2 if unicodedata.east_asian_width(c) in 'WF' else 1) for c in row)
                    self.assertLessEqual(cells, width)

    def test_03_tool_recovery_and_project_switch(self):
        first = self.tool('git')
        self.wait_for(lambda: 'READY '+str(self.repo) in self.tm('capture-pane', '-p', '-t', first))
        self.assertEqual(first, self.tool('git'))
        self.tm('send-keys', '-t', first, 'C-c')
        self.wait_for(lambda: self.tm('display-message', '-p', '-t', first, '#{pane_dead}').strip()=='1')
        self.assertEqual(first, self.tool('git'))
        self.wait_for(lambda: self.tm('display-message', '-p', '-t', first, '#{pane_dead}').strip()=='0')
        self.tm('send-keys', '-t', self.pane, 'cd '+shlex.quote(str(self.other)), 'Enter')
        self.wait_for(lambda: self.tm('display-message', '-p', '-t', self.pane, '#{pane_current_path}').strip()==str(self.other))
        second = self.tool('git')
        self.assertNotEqual(first, second)
        self.wait_for(lambda: 'READY '+str(self.other) in self.tm('capture-pane', '-p', '-t', second))
        self.assertEqual(self.tm('display-message', '-p', '-t', first, '#{pane_dead}').strip(), '0')
        status = subprocess.check_output([str(self.home/'.local/bin/terminal-status'), second], env=self.env, text=True)
        self.assertIn('project B › other', status)
        monitor = self.tool('monitor')
        self.wait_for(lambda: 'READY' in self.tm('capture-pane', '-p', '-t', monitor))
        self.tm('send-keys', '-t', monitor, 'C-c')
        self.wait_for(lambda: self.tm('display-message', '-p', '-t', monitor, '#{pane_dead}').strip()=='1')
        self.assertEqual(monitor, self.tool('monitor'))
        self.wait_for(lambda: self.tm('display-message', '-p', '-t', monitor, '#{pane_dead}').strip()=='0')
        # Restore the main directory for later checks.
        self.tm('send-keys', '-t', self.pane, 'cd '+shlex.quote(str(self.repo)), 'Enter')
        self.wait_for(lambda: self.tm('display-message', '-p', '-t', self.pane, '#{pane_current_path}').strip()==str(self.repo))

    def test_04_legacy_shell_is_preserved(self):
        pane = self.tm('new-window', '-d', '-P', '-F', '#{pane_id}', '-n', 'monitor', '-c', str(self.repo), '/bin/bash --noprofile --norc').strip()
        pid = self.tm('display-message', '-p', '-t', pane, '#{pane_pid}').strip()
        self.tool('monitor')
        self.assertEqual(pid, self.tm('display-message', '-p', '-t', pane, '#{pane_pid}').strip())
        self.assertEqual(self.tm('display-message', '-p', '-t', pane, '#{pane_current_command}').strip(), 'bash')

    def test_05_configuration_and_theme(self):
        subprocess.run([sys.executable, str(self.home/'.local/bin/terminal-theme')], env=dict(self.env, TERMINAL_THEME_NO_RELOAD='1'), check=True, capture_output=True)
        self.tm('source-file', str(self.home/'.tmux.conf'))
        self.assertIn('terminal-status', self.tm('show-options', '-gv', 'status-left'))
        self.assertIn('@work-role', self.tm('show-options', '-gwv', 'window-status-format'))
        self.assertEqual(self.tm('show-options', '-gv', 'status-left-length').strip(), '70')
        # Render the real status line with an attached pseudo-terminal client.
        self.tm('select-window', '-t', self.window)
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        client = subprocess.Popen([str(self.bin/'tmux'), 'attach-session', '-t', 'test'],
                                  stdin=slave, stdout=slave, stderr=slave, env=self.env, start_new_session=True)
        os.close(slave); os.set_blocking(master, False)
        captured = b''
        try:
            deadline = time.monotonic()+4
            while time.monotonic() < deadline:
                try: captured += os.read(master, 65536)
                except BlockingIOError: pass
                if 'project A › main' in captured.decode('utf-8', errors='replace'): break
                time.sleep(.05)
            self.assertIn('project A › main', captured.decode('utf-8', errors='replace'))
        finally:
            client.terminate(); client.wait(timeout=3); os.close(master)
        # The generator must not undo the project-aware status line on repeated use.
        subprocess.run([sys.executable, str(self.home/'.local/bin/terminal-theme')], env=dict(self.env, TERMINAL_THEME_NO_RELOAD='1'), check=True, capture_output=True)
        self.assertIn('terminal-status', (self.home/'.config/tmux/claude-colors.conf').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
