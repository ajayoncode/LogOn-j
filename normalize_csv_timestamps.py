import csv
from datetime import datetime
from pathlib import Path


def normalize_iso_seconds(dt_str: str) -> str:
    if not dt_str:
        return ''
    # Try parse with datetime.fromisoformat (handles with/without microseconds)
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        # Fallback: strip microseconds if present by splitting on '.' before timezone
        core = dt_str
        if '.' in dt_str:
            core = dt_str.split('.')[0]
        # Try parse again without micros
        try:
            dt = datetime.fromisoformat(core)
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        except Exception:
            # If still not parsable, return original string unchanged
            return dt_str


def normalize_csv(csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return

    # Read all rows
    with csv_path.open('r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("CSV is empty; nothing to normalize.")
        return

    header = rows[0]
    # Expected columns
    try:
        start_idx = header.index('start_time')
        end_idx = header.index('end_time')
    except ValueError:
        print("Header missing 'start_time' or 'end_time'; aborting.")
        return

    # Normalize times
    for i in range(1, len(rows)):
        row = rows[i]
        if not row:
            continue
        if len(row) <= max(start_idx, end_idx):
            continue
        row[start_idx] = normalize_iso_seconds(row[start_idx])
        row[end_idx] = normalize_iso_seconds(row[end_idx])
        rows[i] = row

    # Write back
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print("Normalization complete.")


if __name__ == '__main__':
    base_dir = Path(__file__).parent.resolve()
    csv_file = base_dir / 'logger_data' / 'sessions.csv'
    normalize_csv(csv_file)


