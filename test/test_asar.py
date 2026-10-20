import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('verify_asar', Path(__file__).resolve().parents[1] / 'tools/macos/verify_asar.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def archive(path, data=b'hello-world', empty_block=True, override=None):
    digest = lambda data: hashlib.sha256(data).hexdigest()
    blocks = [digest(data[i:i + 4]) for i in range(0, len(data), 4)]
    if not data and empty_block:
        blocks = [digest(b'')]
    item = {'size': len(data), 'offset': '0', 'integrity': {
        'algorithm': 'SHA256', 'hash': digest(data), 'blockSize': 4, 'blocks': blocks
    }}
    if override:
        override(item)
    raw = json.dumps({'files': {'demo': item}}).encode()
    pad = (-len(raw)) % 4
    payload = 4 + len(raw) + pad
    prefix = struct.pack('<4I', 4, payload + 4, payload, len(raw))
    path.write_bytes(prefix + raw + b'\0' * pad + data)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.asar'

    def tearDown(self):
        self.temp.cleanup()

    def test_multiple_blocks(self):
        archive(self.path)
        self.assertEqual(MODULE.verify(self.path)['packedFiles'], 1)

    def test_empty_file_conventions(self):
        for empty_block in [True, False]:
            archive(self.path, b'', empty_block)
            self.assertEqual(MODULE.verify(self.path)['packedFiles'], 1)

    def test_tampered_content(self):
        archive(self.path)
        data = bytearray(self.path.read_bytes())
        data[-1] ^= 1
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'checksum'):
            MODULE.verify(self.path)

    def test_tampered_block_hash_with_valid_file_hash(self):
        archive(self.path, override=lambda item: item['integrity']['blocks'].__setitem__(0, '0' * 64))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            MODULE.verify(self.path)

    def test_out_of_bounds_offset(self):
        archive(self.path, override=lambda item: item.update(offset='999999'))
        with self.assertRaisesRegex(ValueError, 'bounds'):
            MODULE.verify(self.path)

    def test_invalid_block_size(self):
        archive(self.path, override=lambda item: item['integrity'].update(blockSize=0))
        with self.assertRaisesRegex(ValueError, 'block size'):
            MODULE.verify(self.path)

    def test_truncated_header(self):
        self.path.write_bytes(b'\0' * 5)
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            MODULE.verify(self.path)


if __name__ == '__main__':
    unittest.main()
