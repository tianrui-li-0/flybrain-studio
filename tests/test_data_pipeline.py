"""Small synthetic CSV fixtures validate conversion, never serve as app data."""
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_data import prepare, BASE


class PipelineTests(unittest.TestCase):
    def fixture(self, path):
        # IDs exceed float64's exact integer range; preserve strings end to end.
        a, b = '720575940596125868', '720575940596125869'
        tables = {
            'neurons.csv.gz': [['root_id','group','nt_type'],[a,'test','GABA'],[b,'test','ACH']],
            'classification.csv.gz': [['root_id','class','sub_class','side','flow','super_class'],
                [a,'sensory','photo_receptor','left','afferent','sensory'],[b,'visual','','right','intrinsic','optic']],
            'coordinates.csv.gz': [['root_id','position'],[a,'[0 0 0]'],[a,'[2 0 0]'],[b,'[4 4 4]']],
            'connections.csv.gz': [['pre_root_id','post_root_id','neuropil','syn_count','nt_type'],
                [a,b,'A','7','GABA'],[a,b,'B','3','ACH'],[b,a,'A','1','ACH']],
        }
        files = {}
        for name, rows in tables.items():
            with gzip.open(path/name, 'wt', newline='') as stream:
                csv.writer(stream).writerows(rows)
            files[name] = dict(url=BASE+name,sha256=hashlib.sha256((path/name).read_bytes()).hexdigest())
        (path/'download_manifest.json').write_text(json.dumps(dict(provider='FlyWire Codex official GCS',version='783',files=files)))
        return a,b

    def test_count_conservation_direction_and_exact_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder); a,b=self.fixture(path); prepare(path,path/'output')
            with np.load(path/'output/flywire.npz') as data:
                self.assertEqual(data['ids'].tolist(),[a,b])
                self.assertEqual(data['synapse_count'].tolist(),[10,1])
                self.assertEqual(data['weight'].tolist(),[-10,1])
                self.assertEqual(list(zip(data['pre'],data['post'])),[(0,1),(1,0)])
            manifest=json.loads((path/'output/manifest.json').read_text())
            self.assertEqual(manifest['connection_rows'],3)
            self.assertEqual(manifest['synapses'],11)

    def test_modified_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder); self.fixture(path)
            with (path/'neurons.csv.gz').open('ab') as stream: stream.write(b'altered')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                prepare(path,path/'output')
            self.assertFalse((path/'output/flywire.npz').exists())

    def test_nonofficial_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder); self.fixture(path)
            receipt=json.loads((path/'download_manifest.json').read_text())
            receipt['files']['neurons.csv.gz']['url']='https://example.com/neurons.csv.gz'
            (path/'download_manifest.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'Source URL'):
                prepare(path,path/'output')


if __name__ == '__main__': unittest.main()
