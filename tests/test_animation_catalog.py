import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from animation_catalog import export, save

class Client:
    def __init__(self, corrupt=False):
        self.rows = [dict(group=0, category=1, no=i, groupName='一般', categoryName='日常', name='歩き', origin='unknown', warnings=[]) for i in range(103)]
        digest = hashlib.sha256(json.dumps(self.rows, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
        self.metadata = dict(catalogHash=digest, environment={'runtimeSession':'1:123'}, exportedAt='2026-10-28T00:00:00Z', entries=103, complete=True, namesComplete=True, warnings=[])
        self.corrupt = corrupt
    def call(self, name, **args):
        offset=args.get('offset',0)
        metadata=copy.deepcopy(self.metadata)
        if offset and self.corrupt: metadata['catalogHash']='changed'
        return dict(type='success',data=dict(metadata=metadata,animations=self.rows[offset:offset+100],total=103,nextOffset=100 if offset==0 else None))

class Tests(unittest.TestCase):
    def test_export_hash_paging_csv_metadata_and_no_overwrite(self):
        snapshot=export(Client())
        self.assertEqual(len(snapshot['animations']),103)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'catalog.json'
            save(snapshot,target)
            self.assertEqual(json.loads(target.read_text())['metadata']['entries'],103)
            self.assertIn('歩き',target.with_suffix('.csv').read_text(encoding='utf-8-sig'))
            self.assertEqual(json.loads(target.with_suffix('.metadata.json').read_text())['environment']['runtimeSession'],'1:123')
            with self.assertRaises(ValueError):save(snapshot,target)
    def test_changed_generation_refuses_mixed_export(self):
        with self.assertRaisesRegex(ValueError,'changed'): export(Client(corrupt=True))

if __name__=='__main__':unittest.main()
