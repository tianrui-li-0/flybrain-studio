"""Convert verified official FlyWire FAFB v783 CSVs. Run download_data.py first.

No third-party binary or fallback is accepted. Coordinates are annotation points,
not skeletons. Model signs are assumptions, separate from unsigned synapse counts.
"""
import csv
import gzip
import hashlib
import json
import sys
from array import array
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix

BASE = 'https://storage.googleapis.com/flywire-data/codex/data/fafb/783/'
FILES = ('neurons.csv.gz', 'classification.csv.gz', 'coordinates.csv.gz', 'connections.csv.gz')


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((source/'download_manifest.json').read_text(encoding='utf-8'))
    if receipt['provider'] != 'FlyWire Codex official GCS' or receipt['version'] != '783':
        raise ValueError('Expected official FlyWire FAFB v783 downloads')
    hashes = {}
    for name in FILES:
        record = receipt['files'][name]
        with (source/name).open('rb') as stream:
            hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if record['url'] != BASE+name or hashes[name] != record['sha256']:
            raise ValueError('Source URL or checksum mismatch: '+name)

    def rows(name):
        with gzip.open(source/name, 'rt', encoding='utf-8') as stream:
            yield from csv.DictReader(stream)

    ids, nt, groups = [], [], []
    for row in rows('neurons.csv.gz'):
        ids.append(row['root_id']); nt.append(row['nt_type']); groups.append(row['group'])
    n = len(ids)
    if not n or len(set(ids)) != n:
        raise ValueError('Missing or duplicate neuron IDs')
    index = {rid: i for i, rid in enumerate(ids)}
    pre, post, raw_counts = array('I'), array('I'), array('q')
    for row in rows('connections.csv.gz'):
        if row['pre_root_id'] not in index or row['post_root_id'] not in index:
            raise ValueError('Connection endpoint missing from official neuron table')
        count = int(row['syn_count'])
        if count <= 0:
            raise ValueError('Nonpositive official synapse count')
        pre.append(index[row['pre_root_id']]); post.append(index[row['post_root_id']]); raw_counts.append(count)
    source_rows = len(pre)
    graph = coo_matrix((np.asarray(raw_counts, dtype=np.int64), (pre, post)), shape=(n,n)).tocsr().tocoo()
    pre, post, synapse_count = graph.row, graph.col, graph.data
    m = len(pre)
    # Unsigned counts are preserved. Signs are a separate educational assumption.
    sign = np.where(np.asarray(nt)[pre] == 'GABA', -1, 1)
    weights = (synapse_count * sign).astype(np.float32)
    xyz = np.zeros((n, 3), np.float64)
    counts = np.zeros(n, np.int32)
    for row in rows('coordinates.csv.gz'):
        i = index.get(row['root_id'])
        if i is None: raise ValueError('Coordinate ID absent from neuron table')
        point = np.fromstring(row['position'].strip('[]'), sep=' ')
        if len(point) != 3 or not np.isfinite(point).all():
            raise ValueError('Invalid annotation coordinate')
        xyz[i] += point; counts[i] += 1
    valid = counts > 0
    if not valid.any(): raise ValueError('No valid annotation coordinates')
    xyz[valid] /= counts[valid, None]
    centre = (xyz[valid].min(axis=0) + xyz[valid].max(axis=0)) / 2
    span = np.ptp(xyz[valid], axis=0).max()
    positions = ((xyz - centre) / max(span, 1) * 200).astype(np.float32)
    positions[~valid] = 0
    positions = positions[:, [0, 2, 1]] * np.array([1, 1, -1], np.float32)
    labels = np.full(n, '', dtype='<U64'); subclasses = labels.copy()
    sides = np.full(n, '', dtype='<U8'); category = np.full(n, 6, np.uint8)
    sensory = []
    for row in rows('classification.csv.gz'):
        i = index.get(row['root_id'])
        if i is None: raise ValueError('Classification ID absent from neuron table')
        c, sub = row['class'], row['sub_class']
        labels[i], subclasses[i], sides[i] = c, sub, row['side']
        if sub == 'photo_receptor': category[i] = 0; sensory.append(i)
        elif c in ('optic_lobe_intrinsic', 'visual', 'optic_lobes', 'ocellar'): category[i] = 1
        elif c in ('Kenyon_Cell', 'MBON', 'MBIN', 'DAN'): category[i] = 2
        elif c in ('CX', 'TuBu'): category[i] = 3
        elif row['flow'] == 'efferent' or c == 'brain_motor_neuron': category[i] = 4
        elif row['super_class'] == 'sensory': category[i] = 5
    temp = destination/'flywire.pending.npz'
    np.savez_compressed(temp, ids=np.array(ids), nt=np.array(nt), annotation=np.array(groups),
        labels=labels, subclasses=subclasses, sides=sides, positions=positions,
        has_position=valid, category=category, sensory=np.array(sensory, np.int32),
        pre=pre, post=post, weight=weights, synapse_count=synapse_count)
    manifest = dict(dataset='FlyWire FAFB v783 / official CSV exports', neurons=n,
        directed_edges=m, positioned_neurons=int(valid.sum()), photoreceptors=len(sensory),
        source='https://codex.flywire.ai/', source_kind='official_flywire_csv', version='783',
        downloads=receipt, connection_rows=source_rows, synapses=int(synapse_count.sum()),
        paper='https://doi.org/10.1038/s41586-024-07558-y', input_sha256=hashes,
        output_sha256=hashlib.sha256(temp.read_bytes()).hexdigest(),
        geometry='Mean of available annotation coordinates per root_id; no skeletons or meshes.',
        edges='All rows in official connections.csv.gz summed across neuropils by directed pair without an extra count threshold. The export itself may be filtered; not all biological synapses.',
        model_signs='GABA=-1, all other/unknown transmitters=+1 using presynaptic neurons.csv.gz nt_type. Educational assumption, not measured receptor effects.',
        license='Scientific data: CC BY-NC 4.0; application code does not relicense data.',
        sensory_mapping='Approximate coordinate-based screen sampling, not measured receptive fields.')
    temp.replace(destination/'flywire.npz')
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if isinstance(v,int)}))


if __name__ == '__main__': prepare(*sys.argv[1:])
