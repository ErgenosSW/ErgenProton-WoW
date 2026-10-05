#!/usr/bin/env python3
"""Compare matched MangoHud captures; reject short or malformed captures."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

METRICS = ['Average FPS', '1% Min FPS', '0.1% Min FPS', 'Average Frame Time', 'GPU Load']


def read_capture(summary):
    summary = Path(summary)
    if not summary.name.endswith('_summary.csv'):
        raise ValueError('Expected a MangoHud _summary.csv file')
    raw = summary.with_name(summary.name.removesuffix('_summary.csv') + '.csv')
    lines = raw.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('fps,frametime,'))
    rows = list(csv.DictReader(lines[start:]))
    elapsed = [float(row['elapsed']) / 1e9 for row in rows]
    if len(elapsed) < 100 or not all(math.isfinite(v) for v in elapsed):
        raise ValueError(f'Insufficient/invalid samples: {raw}')
    if elapsed[-1] - elapsed[0] < 55 or any(a >= b for a, b in zip(elapsed, elapsed[1:])):
        raise ValueError(f'Short/non-monotonic capture: {raw}')
    with summary.open() as f:
        values = list(csv.DictReader(f))
    if len(values) != 1:
        raise ValueError(f'Expected one summary row: {summary}')
    metrics = {key: float(values[0][key]) for key in METRICS}
    if not all(math.isfinite(v) and v > 0 for v in metrics.values()):
        raise ValueError(f'Invalid metrics: {summary}')
    return {'file': str(summary), 'seconds': elapsed[-1] - elapsed[0], 'samples': len(rows), **metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a', nargs='+', required=True)
    parser.add_argument('--b', nargs='+', required=True)
    args = parser.parse_args()
    a, b = [read_capture(p) for p in args.a], [read_capture(p) for p in args.b]
    if len(a) != len(b):
        raise SystemExit('Use the same number of captures in each group')
    result = {'A': a, 'B': b, 'replicates_per_group': len(a), 'metrics': {},
              'limitations': ['Manual scene/focus consistency must be confirmed separately.',
                              'A static scene does not establish raid or long-session stability.']}
    if len(a) < 3:
        result['limitations'].append('Pilot only: fewer than three captures per group.')
    if any(r['GPU Load'] >= 95 for r in a+b):
        result['limitations'].append('GPU saturation: this scene cannot isolate CPU scheduling benefits.')
    for key in METRICS:
        x, y = statistics.mean(r[key] for r in a), statistics.mean(r[key] for r in b)
        result['metrics'][key] = {'A_mean': x, 'B_mean': y, 'change_percent': (y/x-1)*100}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
