from pathlib import Path
import json,struct,hashlib,plistlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
ORIGINAL=Path(sys.argv[1]).resolve()
APP=Path(sys.argv[2]).resolve()
BASE=Path(sys.argv[3]).resolve()
SOURCE=ORIGINAL/'Contents/Resources/app.asar'
with SOURCE.open('rb') as f:
 a,b,c,d=struct.unpack('<4I',f.read(16));raw=f.read(d);header=json.loads(raw);start=8+b
expected='b276579474c7f0413ae388aaf39d00337f7615a858774156f1268c68519ebab1'
assert hashlib.sha256(raw).hexdigest()==expected
changes={};anchors=[]
def member(path):
 e=header
 for name in path.split('/'):e=e['files'][name]
 return e
def read(path):
 e=member(path)
 with SOURCE.open('rb') as f:f.seek(start+int(e['offset']));return f.read(e['size'])
def patch(path,old,new):
 s=changes.get(path,read(path)).decode();assert s.count(old)==1,(path,old)
 changes[path]=s.replace(old,new).encode();anchors.append({'path':path,'anchor':old,'replacement':new})
def add(path,data):
 n=header
 for part in path.split('/')[:-1]:n=n.setdefault('files',{}).setdefault(part,{'files':{}})
 assert path.split('/')[-1] not in n['files'];n['files'][path.split('/')[-1]]={};changes[path]=data
# No data path, auth, updater, protocol, name, or installer behavior changes.
early='.vite/build/early-bootstrap.js'
changes[early]=b'globalThis.__codexStartupSessionId=process.pid+"-"+Date.now();\n'+read(early)
main='.vite/build/main-CLu1A25j.js'
patch(main,'F={preload:this.options.preloadPath,','F={additionalArguments:[`--codex-startup-eligible=${d===`primary`&&!globalThis.__codexStartupClaimed?`1`:`0`}`,`--codex-startup-session=${globalThis.__codexStartupSessionId}`],preload:this.options.preloadPath,')
patch(main,'z=new D.BrowserWindow(R);r&&','z=new D.BrowserWindow(R);if(d===`primary`)globalThis.__codexStartupClaimed=true;r&&')
preload='.vite/build/preload.js'
changes[preload]=read(preload)+b'\n;require("electron").contextBridge.exposeInMainWorld("codexStartupBoot",{eligible:process.argv.includes("--codex-startup-eligible=1"),sessionId:process.argv.find(a=>a.startsWith("--codex-startup-session="))?.split("=").slice(1).join("=")||"unknown"});\n'
s=read('webview/index.html').decode();needle='    <script type="module" crossorigin';assert s.count(needle)==1
injection='''<link rel="stylesheet" href="./codex-startup/splash.css">
<style>html[data-codex-startup-pending]::before{content:"";position:fixed;inset:0;background:#000;z-index:2147483001;animation:codex-pending-expire 0s 8s forwards}@keyframes codex-pending-expire{to{visibility:hidden;pointer-events:none}}</style>
<script src="./codex-startup/config.js"></script><script src="./codex-startup/boot.js"></script>
'''
changes['webview/index.html']=s.replace(needle,injection+needle,1).encode()
for name in ['splash.css','splash.js','config.js']:
 add('webview/codex-startup/'+name,(ROOT/'lib'/name).read_bytes())
add('webview/codex-startup/boot.js',(ROOT/'integration/electron/boot.js').read_bytes())
files=[]
def walk(node,path=''):
 for n,e in node.get('files',{}).items():
  p=f'{path}/{n}'.lstrip('/')
  if 'files' in e:walk(e,p)
  elif not e.get('unpacked') and 'link' not in e:files.append((p,e))
walk(header);files.sort(key=lambda x:int(x[1].get('offset',10**20)))
old={p:dict(e) for p,e in files};offset=0
for path,e in files:
 if path in changes:
  data=changes[path];bs=e.get('integrity',{}).get('blockSize',4194304)
  e.update(size=len(data),integrity={'algorithm':'SHA256','hash':hashlib.sha256(data).hexdigest(),'blockSize':bs,'blocks':[hashlib.sha256(data[i:i+bs]).hexdigest() for i in range(0,len(data),bs)]})
 e['offset']=str(offset);offset+=e['size']
js=json.dumps(header,ensure_ascii=False,separators=(',',':')).encode();pad=(-len(js))%4;payload=4+len(js)+pad;hp=4+payload
out=APP/'Contents/Resources/app.asar';temp=out.with_suffix('.new')
with SOURCE.open('rb') as fi,temp.open('wb') as fo:
 fo.write(struct.pack('<4I',4,hp,payload,len(js)));fo.write(js);fo.write(b'\0'*pad)
 for path,e in files:
  if path in changes:fo.write(changes[path]);continue
  oe=old[path];fi.seek(start+int(oe['offset']));left=oe['size']
  while left:
   data=fi.read(min(left,8*1024*1024));assert data;fo.write(data);left-=len(data)
temp.replace(out)
pl=APP/'Contents/Info.plist';info=plistlib.load(pl.open('rb'));info['ElectronAsarIntegrity']['Resources/app.asar']['hash']=hashlib.sha256(js).hexdigest();plistlib.dump(info,pl.open('wb'))
patched=BASE/'patched'
for path,data in changes.items():
 dest=patched/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
manifest={'sourceVersion':info['CFBundleShortVersionString'],'bundleId':info['CFBundleIdentifier'],'originalHeaderSha256':expected,'patchedHeaderSha256':hashlib.sha256(js).hexdigest(),'app':str(APP),'backup':str(ORIGINAL),'changedMembers':[{'path':p,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)} for p,data in changes.items()],'anchors':anchors,'dataPathsChanged':False,'authOrSettingsFilesChanged':False,'updaterBehaviorChanged':False}
(BASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('Production animation patch prepared:',len(changes),'ASAR members; original identity and data paths kept')
