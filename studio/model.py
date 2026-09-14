from pathlib import Path
import json
import hashlib
import numpy as np
from scipy.sparse import csr_matrix

CATEGORIES = ['光感受器', '视觉回路', '蘑菇体 / 调制', '中央复合体相关', '传出通路', '其他感觉', '其他 / 未分类']
PALETTE = np.array([[.27,.92,.83], [.28,.59,1.0], [.77,.54,1.0], [1.0,.70,.34], [1.0,.39,.55], [.44,.80,.62], [.35,.43,.57]], np.float32)

class Dataset:
    def __init__(self, directory):
        directory = Path(directory)
        self.manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        if self.manifest.get('source_kind') != 'official_flywire_csv':
            raise ValueError('Please rebuild data using scripts/download_data.py and scripts/prepare_data.py; third-party snapshots are no longer supported.')
        with (directory/'flywire.npz').open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != self.manifest['output_sha256']:
                raise ValueError('Dataset checksum mismatch. Rebuild the official data.')
        with np.load(directory/'flywire.npz', allow_pickle=False) as z:
            for name in z.files: setattr(self, name, z[name])
        self.n = len(self.ids)
        assert self.n == self.manifest['neurons']
        self.id_lookup = {x:i for i,x in enumerate(self.ids)}
        self.outgoing = csr_matrix((self.weight, (self.pre, self.post)), shape=(self.n,self.n))
        self.incoming = self.outgoing.T.tocsr()
        self.category_sizes = np.bincount(self.category, minlength=len(CATEGORIES))
        self.input_ids = self.sensory[self.has_position[self.sensory]]
        # Screen coordinates are a documented approximation, independently scaled per eye.
        self.uv = np.zeros((len(self.input_ids),2), np.float32)
        for side in np.unique(self.sides[self.input_ids]):
            mask = self.sides[self.input_ids] == side
            coords = self.positions[self.input_ids[mask]][:, [1,2]]
            lo = np.percentile(coords, 1, axis=0); hi = np.percentile(coords,99,axis=0)
            self.uv[mask] = np.clip((coords-lo)/np.maximum(hi-lo,1e-6),0,1)
        self.uv[:,1] = 1-self.uv[:,1]

    def neighbours(self, index, limit=160):
        results = []
        for matrix in (self.outgoing, self.incoming):
            start,end = matrix.indptr[index:index+2]
            ids, weights = matrix.indices[start:end], matrix.data[start:end]
            mask = self.has_position[ids]; ids,weights = ids[mask], weights[mask]
            order = np.argsort(-np.abs(weights))[:limit]
            results.append((ids[order],weights[order],int(end-start)))
        return results

class LIFNetwork:
    """Dimensionless educational LIF, dt=10 ms. No biological calibration.

    Full graph, previous-step spikes, exp(-dt/30ms) leak, 20ms refractory.
    Signed log1p(synapse count) weights / sqrt(total absolute incoming count).
    Fixed current 0.02, threshold 1, reset 0. No random fake spikes.
    """
    dt = .01
    def __init__(self, data):
        self.data = data
        normalizer = np.sqrt(np.maximum(1, np.asarray(abs(data.incoming).sum(axis=1)).ravel()))
        weights = np.sign(data.weight)*np.log1p(np.abs(data.weight))/normalizer[data.post]
        self.matrix = csr_matrix((weights.astype(np.float32), (data.post,data.pre)), shape=(data.n,data.n))
        self.reset()

    def reset(self):
        self.v = np.zeros(self.data.n,np.float32)
        self.fired = np.zeros(self.data.n,np.float32)
        self.refractory = np.zeros(self.data.n,np.uint8)
        self.total = np.zeros(self.data.n,np.uint64)
        self.elapsed = 0.

    def step(self, sensory, input_gain=1., coupling=.5, audio_ids=None, audio_current=None):
        available = self.refractory == 0
        self.refractory[~available] -= 1
        drive = self.matrix @ self.fired * coupling
        drive[self.data.input_ids] += sensory * input_gain * .48
        if audio_ids is not None and audio_current is not None:
            drive[audio_ids] += audio_current
        self.v = np.maximum(-2, np.exp(-self.dt/.03)*self.v + drive + .02)
        self.v[~available] = 0
        self.fired = ((self.v >= 1) & available).astype(np.float32)
        fired = self.fired.astype(bool)
        self.v[fired] = 0; self.refractory[fired] = 2
        self.total += fired; self.elapsed += self.dt
        return fired
