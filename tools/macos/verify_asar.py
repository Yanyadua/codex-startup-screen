"""Read and verify Electron ASAR integrity metadata without unpacking the app."""
import hashlib
import json
import struct
from pathlib import Path


def header(path):
    with Path(path).open('rb') as stream:
        prefix = stream.read(16)
        if len(prefix) != 16:
            raise ValueError('Truncated ASAR header')
        size, span, payload, length = struct.unpack('<4I', prefix)
        if size != 4 or payload + 4 != span or length > payload - 4:
            raise ValueError('Invalid ASAR header framing')
        raw = stream.read(length)
        if len(raw) != length:
            raise ValueError('Truncated ASAR header JSON')
    return json.loads(raw), raw, 8 + span


def entries(node, prefix=''):
    for name, item in node.get('files', {}).items():
        path = f'{prefix}/{name}'.lstrip('/')
        if 'files' in item:
            yield from entries(item, path)
        elif not item.get('unpacked') and 'link' not in item:
            yield path, item


def verify(path):
    tree, raw, start = header(path)
    count = 0
    size = Path(path).stat().st_size
    with Path(path).open('rb') as stream:
        for name, item in entries(tree):
            offset, length = int(item['offset']), item['size']
            if offset < 0 or length < 0 or start + offset + length > size:
                raise ValueError(f'{name}: file outside ASAR bounds')
            integrity = item.get('integrity', {})
            if integrity.get('algorithm') != 'SHA256':
                raise ValueError(f'{name}: missing or unsupported file integrity')
            block_size = integrity.get('blockSize', 0)
            if not isinstance(block_size, int) or block_size <= 0:
                raise ValueError(f'{name}: invalid block size')
            stream.seek(start + offset)
            digest, blocks, left = hashlib.sha256(), [], length
            while left:
                data = stream.read(min(block_size, left))
                if not data:
                    raise ValueError(f'{name}: truncated data')
                left -= len(data)
                digest.update(data)
                blocks.append(hashlib.sha256(data).hexdigest())
            expected_blocks = integrity.get('blocks')
            if length == 0 and expected_blocks == [hashlib.sha256(b'').hexdigest()]:
                blocks = expected_blocks
            if digest.hexdigest() != integrity.get('hash') or blocks != expected_blocks:
                raise ValueError(f'{name}: file or block checksum mismatch')
            count += 1
    return {'packedFiles': count, 'headerSha256': hashlib.sha256(raw).hexdigest()}


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(sys.argv[1]), indent=2))
