from pathlib import Path
import plistlib,hashlib,subprocess,json,sys
app=Path(sys.argv[1]).resolve();original=Path(sys.argv[2]).resolve();base=Path(sys.argv[3]).resolve()
fw=app/'Contents/Frameworks/Codex Framework.framework';binary=fw/'Versions/Current/Codex Framework'
info=plistlib.load(open(app/'Contents/Info.plist','rb'));data=bytearray(binary.read_bytes());sentinel=b'AGbevlPCksUGKNL8TSn7wGmJEuJsXb2A';assert data.count(sentinel)==1;pos=data.find(sentinel);assert data[pos+32:pos+34]==b'\x01\x01'
new=hashlib.sha256(b''.join((k+v['algorithm']+v['hash']).encode() for k,v in sorted(info['ElectronAsarIntegrity'].items()))).digest();data[pos+34:pos+66]=new;binary.write_bytes(data)
args=['/usr/bin/codesign','--force','--sign','-','--timestamp=none','--options','runtime'];entdir=base/'entitlements';entdir.mkdir(exist_ok=True);ledger=[]
def sign(code,source):
 r=subprocess.run(['/usr/bin/codesign','-d','--entitlements',':-',str(source)],capture_output=True,check=True)
 ents=plistlib.loads(r.stdout);remove=[k for k in ents if k.startswith('com.apple.developer.') or k in ['com.apple.application-identifier','keychain-access-groups','com.apple.security.application-groups']]
 for k in remove:ents.pop(k)
 ents['com.apple.security.cs.disable-library-validation']=True
 path=entdir/(code.name.replace(' ','_')+'.plist');plistlib.dump(ents,path.open('wb'))
 subprocess.run(args+['--entitlements',str(path),str(code)],check=True)
 ledger.append({'path':str(code.relative_to(app)) if code!=app else '.','removedUnsupportedIdentityEntitlements':remove})
for helper in sorted((fw/'Versions/Current/Helpers').glob('*.app')):
 sign(helper,original/helper.relative_to(app))
subprocess.run(args+[str(fw)],check=True);sign(app,original)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
# The backend retains its original OpenAI Developer ID identity.
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app/'Contents/Resources/codex-cli/CodexCLI.app')],check=True)
(base/'sign-manifest.json').write_text(json.dumps({'signature':'ad-hoc','nativeDictionaryIntegrityDigest':new.hex(),'nativeDictionaryDigestEnabled':True,'embeddedAsarIntegrityFusePreserved':True,'restrictedIdentityEntitlementsRemoved':ledger,'backendCLIOriginalSignaturePreserved':True,'libraryValidationExceptionInModifiedExecutables':True},ensure_ascii=False,indent=2))
print('Production staged app signed and deeply verified; backend CLI retains original signature')
