"""Build a signed local copy. Never quits or replaces the installed application."""
import argparse
import datetime
import hashlib
import json
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from verify_asar import header, verify

REPO = Path(__file__).resolve().parents[2]
SUPPORTED_VERSION = '26.1013.40934'
SUPPORTED_BUILD = '20770'
ORIGINAL_HEADER = 'b276579474c7f0413ae388aaf39d00337f7615a858774156f1268c68519ebab1'


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def check_source(app):
    with (app / 'Contents/Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    if (info.get('CFBundleIdentifier'), info.get('CFBundleShortVersionString'), str(info.get('CFBundleVersion'))) != (
        'com.openai.codex', SUPPORTED_VERSION, SUPPORTED_BUILD
    ):
        raise ValueError('Unsupported application/version. No application files were changed.')
    _, raw, _ = header(app / 'Contents/Resources/app.asar')
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_HEADER:
        raise ValueError('Expected an unmodified supported ASAR. Do not reuse the patch on an update.')
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', app)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=Path('/Applications/ChatGPT.app'))
    parser.add_argument('--output', type=Path, help='New local build directory; must not already exist')
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('The native patch supports only Apple Silicon macOS. The web preview is cross-platform.')
    source = args.app.expanduser().resolve()
    check_source(source)
    if not shutil.which('xcrun') or not shutil.which('python3'):
        parser.error('Install Apple Command Line Tools (xcode-select --install) and Python 3 first.')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    work = (args.output or REPO / 'local-build' / stamp).expanduser().resolve()
    if work.exists() or work == source or source in work.parents or work in source.parents:
        parser.error('Use a new output directory outside the application bundle.')
    work.mkdir(parents=True)
    backup = work / 'original.app'
    staged = work / 'ChatGPT-ready.app'
    # ditto preserves extended attributes, symlinks and the original backup signature.
    run('/usr/bin/ditto', source, backup)
    run('/usr/bin/ditto', backup, staged)
    check_source(backup)
    tools = REPO / 'tools/macos'
    run(sys.executable, tools / 'build.py', backup, staged, work)
    result = verify(staged / 'Contents/Resources/app.asar')
    (work / 'asar-verification.json').write_text(json.dumps(result, indent=2))
    run(sys.executable, tools / 'sign.py', staged, backup, work)
    run('/usr/bin/xcrun', 'swiftc', tools / 'Deploy.swift', '-o', work / 'codex-startup-deploy')
    config = {
        'target': str(source), 'staged': str(staged), 'backup': str(backup),
        'archivedInstalledOriginal': str(work / 'installed-original.app'),
        'workspace': str(work), 'status': str(work / 'status.json'),
        'originalAsarHash': sha256(backup / 'Contents/Resources/app.asar'),
        'stagedAsarHash': sha256(staged / 'Contents/Resources/app.asar'),
    }
    (work / 'deployment.json').write_text(json.dumps(config, indent=2))
    print('\nBuild ready. The installed application has not been replaced.')
    print(f'Build directory: {work}')
    print('See docs/MACOS.md for explicit check/apply/restore commands and signing limitations.')


if __name__ == '__main__':
    main()
