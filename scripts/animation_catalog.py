"""Export/lookup installed animation snapshots. Only export/validate contact Studio."""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path

from mcp_client import Client


def checked(client, **args):
    result = client.call('character_animation_list', **args)
    if result.get('type') != 'success':
        raise ValueError(result)
    data = result['data']
    if 'metadata' not in data:
        raise ValueError('Game plugin is too old: install/load KKStudioSocket 1.2.1 or later')
    return data


def export(client):
    first = checked(client, limit=100, refresh=True)
    metadata = first['metadata']
    rows = list(first['animations'])
    page = first
    while page['nextOffset'] is not None:
        offset = page['nextOffset']
        if offset != len(rows):
            raise ValueError('Invalid pagination; export aborted')
        page = checked(client, offset=offset, limit=100)
        for key in ('catalogHash', 'environment', 'exportedAt'):
            if page['metadata'][key] != metadata[key]:
                raise ValueError('Runtime catalog changed during export; retry refresh')
        if page['total'] != first['total'] or not page['animations']:
            raise ValueError('Inconsistent page; export aborted')
        rows.extend(page['animations'])
    if len(rows) != first['total'] or len(rows) != metadata['entries']:
        raise ValueError('Export count mismatch')
    encoding = metadata.get('hashEncoding', 'ascii-json')
    if encoding not in ('ascii-json', 'utf8-json'):
        raise ValueError('Unsupported catalog hash encoding')
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=encoding == 'ascii-json').encode('utf-8')).hexdigest()
    if digest != metadata['catalogHash']:
        raise ValueError('Catalog hash mismatch')
    return {'metadata': metadata, 'animations': rows,
            'downloadedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}


def save(snapshot, path):
    """A new filename is required; never overwrite an existing user export."""
    csv_path = path.with_suffix('.csv')
    metadata_path = path.with_suffix('.metadata.json')
    if any(p.exists() for p in (path, csv_path, metadata_path)):
        raise ValueError('Choose a new filename; an output already exists')
    fields = ['group', 'category', 'no', 'groupName', 'categoryName', 'name', 'origin', 'warnings']
    # Metadata sidecar makes the CSV's scope/completeness explicit when shared separately.
    with metadata_path.open('x', encoding='utf-8') as f:
        json.dump(snapshot['metadata'], f, ensure_ascii=False, indent=2)
    with csv_path.open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in snapshot['animations']:
            writer.writerow(dict(row, warnings=';'.join(row['warnings'])))
    with path.open('x', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'find', 'validate'])
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8766/')
    parser.add_argument('--search', default='')
    parser.add_argument('--group', type=int)
    parser.add_argument('--category', type=int)
    args = parser.parse_args()
    if args.action == 'export':
        snapshot = export(Client(args.url))
        save(snapshot, args.cache)
        print(json.dumps(snapshot['metadata'], ensure_ascii=False, indent=2))
        return
    snapshot = json.loads(args.cache.read_text(encoding='utf-8'))
    if args.action == 'validate':
        current = checked(Client(args.url), limit=1, refresh=True)['metadata']
        old = snapshot['metadata']
        valid = current['environment'] == old['environment'] and current['catalogHash'] == old['catalogHash']
        print(json.dumps({'validForCurrentRuntime': valid,
                          'catalogContentMatches': current['catalogHash'] == old['catalogHash'],
                          'refreshRequired': not valid}, indent=2))
        if not valid:
            raise SystemExit(2)
        return
    rows = [row for row in snapshot['animations']
            if (args.group is None or row['group'] == args.group)
            and (args.category is None or row['category'] == args.category)
            and args.search.lower() in ' '.join(row.get(k) or '' for k in ('groupName', 'categoryName', 'name')).lower()]
    print(json.dumps({'liveValidation': 'not performed; validate before reusing runtime IDs',
                      'metadata': snapshot['metadata'], 'matches': rows}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
