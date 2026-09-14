"""Download FAFB v783 CSV exports directly from FlyWire's official GCS bucket.

The URL template is published by murthylab/codex in
codex/data/local_data_loader.py. No simulation project's data is used.
"""
import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

BASE = 'https://storage.googleapis.com/flywire-data/codex/data/fafb/783/'
FILES = ('neurons.csv.gz', 'classification.csv.gz', 'coordinates.csv.gz', 'connections.csv.gz')


def download(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = {}
    for name in FILES:
        url = BASE + name
        print('Downloading', url, flush=True)
        path = destination / name
        partial = destination / (name + '.part')
        sha = hashlib.sha256()
        md5 = hashlib.md5()
        try:
            with urlopen(url, timeout=120) as response, partial.open('wb') as output:
                expected_size = int(response.headers['Content-Length'])
                hashes = ','.join(response.headers.get_all('x-goog-hash', []))
                expected_md5 = next((x.strip()[4:] for x in hashes.split(',') if x.strip().startswith('md5=')), None)
                if not expected_md5:
                    raise ValueError('Official object has no MD5 checksum: ' + name)
                size = 0
                for chunk in iter(lambda: response.read(1024 * 1024), b''):
                    output.write(chunk)
                    sha.update(chunk)
                    md5.update(chunk)
                    size += len(chunk)
                if size != expected_size or base64.b64encode(md5.digest()).decode() != expected_md5:
                    raise ValueError('Official download checksum/length mismatch: ' + name)
                records[name] = dict(url=url, bytes=size, sha256=sha.hexdigest(),
                                     md5=md5.hexdigest(), generation=response.headers.get('x-goog-generation'))
            partial.replace(path)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
    record = dict(provider='FlyWire Codex official GCS', version='783',
                  downloaded_at=datetime.now(timezone.utc).isoformat(), files=records)
    (destination / 'download_manifest.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', nargs='?', default='data/raw/783')
    download(parser.parse_args().destination)
