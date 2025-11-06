"""Read a CSV and extract journey info for each row.

Usage:
    python scripts/extract_from_csv.py data/sample_journeys.csv output/journeys.jsonl --text-column description

If --text-column is not provided, the script will concatenate all columns as the text to analyze.
"""
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.journey_tools import extract_journey_info


def process(csv_path: Path, out_path: Path, text_column: str | None = None):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open(newline='', encoding='utf-8') as fh_in, out_path.open('w', encoding='utf-8') as fh_out:
        reader = csv.DictReader(fh_in)
        for row in reader:
            if text_column and text_column in row:
                text = row[text_column]
            else:
                # merge all columns
                text = " ".join([str(v) for v in row.values() if v])

            json_out = extract_journey_info(text)
            # attach original row id if exists
            try:
                uid = row.get('id') or row.get('journey_id')
            except Exception:
                uid = None

            payload = {
                'source_id': uid,
                'extracted': json.loads(json_out),
            }
            fh_out.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--text-column', type=str, default=None)
    args = parser.parse_args()
    process(args.csv, args.out, args.text_column)


if __name__ == '__main__':
    main()
