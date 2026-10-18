#!/usr/bin/env python3
"""Deterministic deployment for Claude Terminal Workbench. Python 3.11+."""
import argparse,hashlib,json,os,platform,re,shlex,shutil,subprocess,sys,tarfile,tempfile,urllib.request,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path

BUNDLE=Path(__file__).resolve().parents[1]
MANIFEST=BUNDLE/'assets/manifest.json'

def digest(data):return hashlib.sha256(data).hexdigest()
def filehash(path):return digest(path.read_bytes()) if path.is_file() else None

def load_manifest():
 data=json.loads(MANIFEST.read_text())
 if digest((BUNDLE/'assets/bash-integration.bash').read_bytes())!=data['bash_integration_sha256']:raise RuntimeError('Bash integration integrity mismatch')
 for rel,sha in data['template_sha256'].items():
  p=BUNDLE/'assets/home'/rel
  if not p.is_file() or digest(p.read_bytes())!=sha:raise RuntimeError('Template integrity mismatch: '+rel)
 return data

def system():
 info={}
 if Path('/etc/os-release').exists():
  for line in Path('/etc/os-release').read_text().splitlines():
   if '=' in line:
    k,v=line.split('=',1);info[k]=v.strip('"')
 return {'os':info.get('ID',platform.system()),'version':info.get('VERSION_ID',''),'architecture':platform.machine()}

def compatible():
 s=system()
 return s['os']=='ubuntu' and s['version']=='26.04' and s['architecture']=='x86_64'

def environment(home):
 return dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_DATA_HOME=str(home/'.local/share'),XDG_CACHE_HOME=str(home/'.cache'),TERMINAL_THEME_NO_RELOAD='1',TERM='xterm-256color')

def strip_block(text,name):
 return re.sub(r'(?ms)^# BEGIN '+re.escape(name)+r'\n.*?^# END '+re.escape(name)+r'\n?', '',text)

def bashrc(home):
 path=home/'.bashrc';text=path.read_text() if path.exists() else ''
 for name in ['Claude workbench integration','Claude workbench','Claude terminal studio']:
  text=strip_block(text,name)
 integration=(BUNDLE/'assets/bash-integration.bash').read_text().rstrip()
 suffix='# BEGIN Claude workbench\n[[ -r "$HOME/.config/terminal-workbench/shell.bash" ]] && source "$HOME/.config/terminal-workbench/shell.bash"\n# END Claude workbench\n'
 return integration+'\n'+text.strip('\n')+'\n\n'+suffix

def desktop_arg(value):
 if not re.search(r'[\s"\\`$]',value):return value
 for char in ['\\','"','`','$']:value=value.replace(char,'\\'+char)
 return '"'+value+'"'

def render(home):
 result={}
 for p in sorted((BUNDLE/'assets/home').rglob('*')):
  if not p.is_file():continue
  rel=str(p.relative_to(BUNDLE/'assets/home'));text=p.read_text()
  if p.suffix=='.desktop':
   lines=[]
   for line in text.splitlines():
    if line.startswith('Exec='):
     argv=shlex.split(line[5:]);line='Exec='+' '.join(desktop_arg(a.replace('__WORKBENCH_HOME__',str(home))) for a in argv)
    lines.append(line)
   text='\n'.join(lines)+'\n'
  else:text=text.replace('__WORKBENCH_HOME__',str(home))
  mode=0o755 if rel.startswith('.local/bin/') else ((home/rel).stat().st_mode & 0o777 if (home/rel).is_file() else 0o644)
  result[rel]=(text.encode(),mode)
 result['.bashrc']=(bashrc(home).encode(),((home/'.bashrc').stat().st_mode & 0o777) if (home/'.bashrc').is_file() else 0o644)
 return result

def privileged(argv):
 if os.geteuid()==0:command=argv
 elif sys.stdin.isatty():command=['sudo',*argv]
 elif shutil.which('pkexec'):command=['pkexec',*argv]
 else:raise RuntimeError('System package installation requires an interactive sudo terminal or polkit authentication.')
 subprocess.run(command,check=True)

def dependencies(m):
 if not compatible():raise RuntimeError('Bundled dependency installation supports Ubuntu 26.04 x86_64 only. Inspect and adapt other platforms before deployment.')
 apt='/usr/bin/apt-get'
 privileged([apt,'update'])
 privileged([apt,'install','-y',*m['apt_packages']])

def downloads(home,m):
 cache=home/'.cache/terminal-workbench/downloads';cache.mkdir(parents=True,exist_ok=True)
 files={}
 for item in m['assets']:
  archive=cache/item['name']
  if not archive.exists() or filehash(archive)!=item['sha256']:
   temporary=archive.with_suffix(archive.suffix+'.part')
   print('Downloading pinned asset:',item['name'],flush=True)
   request=urllib.request.Request(item['url'],headers={'User-Agent':'Claude-Terminal-Workbench/1.0'})
   with urllib.request.urlopen(request,timeout=90) as response,temporary.open('wb') as out:shutil.copyfileobj(response,out)
   if filehash(temporary)!=item['sha256']:temporary.unlink();raise RuntimeError('Release checksum mismatch: '+item['name'])
   os.replace(temporary,archive)
  if item['kind']=='font':
   with zipfile.ZipFile(archive) as z:
    selected=[]
    for member in z.namelist():
     name=Path(member).name
     if name.startswith('MapleMonoNormal-NF-CN-') and any(name.endswith('-'+style+'.ttf') for style in ['Regular','Bold','Italic','BoldItalic']):
      files['.local/share/fonts/MapleMonoNormalNFCN/'+name]=(z.read(member),0o644);selected.append(name)
    if len(selected)!=4:raise RuntimeError('Expected four pinned font faces.')
  elif item['kind']=='bottom':
   with tarfile.open(archive) as tar:
    member=next(x for x in tar.getmembers() if x.isfile() and Path(x.name).name=='btm')
    files['.local/bin/btm']=(tar.extractfile(member).read(),0o755)
 return files

def safe_path(home,rel):
 if Path(rel).is_absolute() or '..' in Path(rel).parts:raise RuntimeError('Invalid managed path')
 return home/rel

def save_backup(home,changes):
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
 folder=home/'.local/state/terminal-workbench/backups'/stamp
 folder.mkdir(parents=True,mode=0o700)
 entries=[]
 for rel,(content,mode) in changes.items():
  path=safe_path(home,rel);entry={'path':rel,'after':digest(content),'existed':path.exists() or path.is_symlink()}
  if path.is_symlink():entry.update(kind='symlink',link=os.readlink(path))
  elif path.exists():
   if not path.is_file():raise RuntimeError('Expected a file at '+str(path))
   dest=folder/'files'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);entry['kind']='file'
  entries.append(entry)
 journal={'home':str(home),'entries':entries,'version':'1.0.0','complete':False}
 (folder/'journal.json').write_text(json.dumps(journal,indent=2))
 return folder,journal

def atomic_write(path,data,mode):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='.workbench-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as out:out.write(data)
  os.chmod(temp,mode);os.replace(temp,path)
 finally:
  if Path(temp).exists():Path(temp).unlink()

def restore(folder,home,check=True,only=None):
 journal=json.loads((folder/'journal.json').read_text())
 if journal['home']!=str(home):raise RuntimeError('Backup belongs to another target home.')
 entries=[e for e in journal['entries'] if only is None or e['path'] in only]
 if check:
  drift=[e['path'] for e in entries if filehash(safe_path(home,e['path']))!=e['after']]
  if drift:raise RuntimeError('Files changed since this deployment; preserve those edits before rollback: '+', '.join(drift))
 for e in reversed(entries):
  path=safe_path(home,e['path'])
  if e.get('kind')=='file':
   before=folder/'files'/e['path'];atomic_write(path,before.read_bytes(),before.stat().st_mode & 0o777)
  elif e.get('kind')=='symlink':
   if path.exists() or path.is_symlink():path.unlink()
   path.symlink_to(e['link'])
  elif not e['existed'] and (path.exists() or path.is_symlink()):path.unlink()
 print('Restored configuration backup:',folder)

def doctor(home,staging=False):
 import tomllib
 errors=[]
 for rel in ['.config/starship.toml','.config/bottom/bottom.toml','.config/terminal-workbench/palette.toml']:
  try:tomllib.loads((home/rel).read_text())
  except Exception as exc:errors.append(rel+': '+str(exc))
 for rel in ['.bashrc','.config/terminal-workbench/shell.bash','.local/bin/ghostty-tmux','.local/bin/terminal-dev','.local/bin/terminal-studio','.local/bin/terminal-studio-pane']:
  if subprocess.run(['bash','-n',str(home/rel)],capture_output=True).returncode:errors.append('Bash syntax: '+rel)
 for path in (home/'.local/bin').glob('terminal-*'):
  if not path.is_file() or not path.read_bytes().startswith(b'#!/usr/bin/python3'):continue
  try:compile(path.read_text(),str(path),'exec')
  except Exception as exc:errors.append(str(exc))
 ghostty=shutil.which('ghostty')
 if ghostty:
  result=subprocess.run([ghostty,'+validate-config'],env=environment(home),capture_output=True,text=True)
  if result.returncode or result.stderr.strip():errors.append('Ghostty validation: '+result.stderr.strip())
 elif not staging:errors.append('Missing ghostty')
 if not staging:
  for cmd in ['tmux','eza','fastfetch','micro','starship','fzf','zoxide','batcat','fdfind','rg','lazygit','wl-copy']:
   if not shutil.which(cmd):errors.append('Missing command: '+cmd)
  if not (home/'.local/bin/btm').is_file():errors.append('Missing pinned bottom binary')
  fonts=home/'.local/share/fonts/MapleMonoNormalNFCN'
  if len(list(fonts.glob('*.ttf')))!=4:errors.append('Missing pinned Maple Mono font faces')
 state=home/'.local/state/terminal-workbench/install.json'
 if state.exists():
  data=json.loads(state.read_text())
  drift=[rel for rel,sha in data['files'].items() if filehash(safe_path(home,rel))!=sha]
  if drift:errors.append('Local changes since install (review before replacing): '+', '.join(drift))
 for e in errors:print('CHECK:',e)
 print('Doctor:', 'PASS' if not errors else 'NEEDS ATTENTION')
 return not errors

def install(home,m,args):
 if not args.staging and not compatible():raise RuntimeError('Unsupported platform for this tested bundle. See inspect and SKILL.md before adapting.')
 if args.with_deps:dependencies(m)
 desired=render(home)
 if args.with_assets:
  if platform.machine()!='x86_64':raise RuntimeError('The pinned bottom binary targets x86_64.')
  desired.update(downloads(home,m))
 changes={rel:item for rel,item in desired.items() if filehash(safe_path(home,rel))!=digest(item[0]) or safe_path(home,rel).is_symlink() or (safe_path(home,rel).exists() and (safe_path(home,rel).stat().st_mode & 0o777)!=item[1])}
 if not changes:
  print('Already matches bundle version',m['version'])
  return doctor(home,args.staging)
 folder,journal=save_backup(home,changes);written=[]
 try:
  for rel,(content,mode) in changes.items():atomic_write(safe_path(home,rel),content,mode);written.append(rel)
  subprocess.run([sys.executable,str(home/'.local/bin/terminal-theme')],env=environment(home),check=True,capture_output=True,text=True)
  if args.with_assets and shutil.which('fc-cache'):subprocess.run(['fc-cache','-f',str(home/'.local/share/fonts')],env=environment(home),check=True,stdout=subprocess.DEVNULL)
  if shutil.which('update-desktop-database'):subprocess.run(['update-desktop-database',str(home/'.local/share/applications')],check=True,stdout=subprocess.DEVNULL)
  journal['complete']=True
  (folder/'journal.json').write_text(json.dumps(journal,indent=2))
  state=home/'.local/state/terminal-workbench/install.json';state.parent.mkdir(parents=True,exist_ok=True)
  # Include generator outputs in drift checks; record actual bytes after rendering.
  tracked={rel:filehash(home/rel) for rel in desired}
  state.write_text(json.dumps({'version':m['version'],'backup':str(folder),'files':tracked},indent=2)+'\n')
 except Exception:
  restore(folder,home,check=False,only=written);raise
 print('Installed',len(changes),'changed files. Backup:',folder)
 okay=doctor(home,args.staging)
 if args.reload and not args.staging and okay:
  subprocess.run(['tmux','source-file',str(home/'.tmux.conf')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  print('tmux configuration reloaded without restarting sessions. Reload Ghostty with Ctrl+Shift+R.')
 return okay

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('action',choices=['inspect','plan','install','doctor','rollback'])
 parser.add_argument('--home',type=Path,default=Path.home())
 parser.add_argument('--with-deps',action='store_true')
 parser.add_argument('--with-assets',action='store_true')
 parser.add_argument('--reload',action='store_true')
 parser.add_argument('--staging',action='store_true',help='isolated file deployment tests; no package operations or live reload')
 parser.add_argument('--backup',type=Path,help='journal directory for rollback; otherwise latest installed backup')
 args=parser.parse_args();home=args.home.expanduser().resolve();m=load_manifest()
 if args.staging and (args.with_deps or args.with_assets or args.reload):parser.error('Staging excludes package installation, downloads and live reload.')
 if args.action=='inspect':print(json.dumps({'bundle_version':m['version'],'system':system(),'tested_profile':compatible(),'target_home':str(home),'apt_packages':m['apt_packages'],'pinned_assets':m['assets']},indent=2));return 0
 if args.action=='plan':
  changes=[rel for rel,(data,mode) in render(home).items() if filehash(home/rel)!=digest(data) or (home/rel).is_symlink() or ((home/rel).exists() and ((home/rel).stat().st_mode & 0o777)!=mode)]
  print(json.dumps({'version':m['version'],'target_home':str(home),'changed_files':changes,'dependencies_installed_only_with':'--with-deps','downloads_only_with':'--with-assets'},indent=2));return 0
 if args.action=='install':return 0 if install(home,m,args) else 1
 if args.action=='doctor':return 0 if doctor(home,args.staging) else 1
 if args.action=='rollback':
  state=home/'.local/state/terminal-workbench/install.json'
  folder=args.backup.resolve() if args.backup else Path(json.loads(state.read_text())['backup'])
  restore(folder,home)
  if state.exists():state.unlink()
  return 0

if __name__=='__main__':
 try:sys.exit(main())
 except (RuntimeError,OSError,subprocess.CalledProcessError,ValueError,KeyError) as exc:
  print('ERROR:',exc,file=sys.stderr);sys.exit(1)
