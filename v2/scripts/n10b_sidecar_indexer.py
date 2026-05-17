#!/usr/bin/env python3
"""Vol-122 N10b sidecar — tail a raw binary file and bulk-index into SQLite.

Reads the n10b_raw_writer output (28 bytes/row, little-endian):
  1 byte   position_idx
  9 cells × (2 bytes pid LE, 1 byte rot) = 27 bytes
Total: 28 bytes.

Tails the file (re-reads new bytes), inserts in batches of 100k rows.
Stops when the Rust process is done (file no longer growing AND
producer-PID is dead).

Usage:
  python3 scripts/n10b_sidecar_indexer.py \\
    --raw output/vol-122/n10b_raw.bin \\
    --db  output/vol-122/n10b_indexed.sqlite \\
    --producer-pid 12345
"""
import argparse
import os
import sqlite3
import struct
import sys
import time

ROW_SIZE = 28
BATCH = 100_000


def is_pid_alive(pid):
    if pid is None:
        return True  # if not tracking, assume alive
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="Raw binary input file")
    ap.add_argument("--db", required=True, help="SQLite output DB")
    ap.add_argument("--producer-pid", type=int, default=None,
        help="PID of producer; stop when both file is stable AND PID is dead")
    ap.add_argument("--poll-interval", type=float, default=1.0)
    args = ap.parse_args()

    # Ensure raw file exists (wait if not)
    while not os.path.exists(args.raw):
        time.sleep(args.poll_interval)
        if not is_pid_alive(args.producer_pid):
            print(f"raw file never appeared and producer is dead. exiting.", file=sys.stderr)
            return

    # Open SQLite + setup
    db_dir = os.path.dirname(args.db) or '.'
    os.makedirs(db_dir, exist_ok=True)
    # delete existing
    if os.path.exists(args.db):
        os.remove(args.db)
    conn = sqlite3.connect(args.db)
    conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;
        CREATE TABLE blocks_3x3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position INTEGER NOT NULL,
            p0_pid INTEGER, p0_rot INTEGER,
            p1_pid INTEGER, p1_rot INTEGER,
            p2_pid INTEGER, p2_rot INTEGER,
            p3_pid INTEGER, p3_rot INTEGER,
            p4_pid INTEGER, p4_rot INTEGER,
            p5_pid INTEGER, p5_rot INTEGER,
            p6_pid INTEGER, p6_rot INTEGER,
            p7_pid INTEGER, p7_rot INTEGER,
            p8_pid INTEGER, p8_rot INTEGER
        );
        CREATE INDEX idx_position ON blocks_3x3(position);
    """)

    f = open(args.raw, "rb")
    total_indexed = 0
    last_size = 0
    last_total = 0
    last_t = time.time()
    print(f"[sidecar] starting; tailing {args.raw}", flush=True)

    # Insert statement
    insert_sql = (
        "INSERT INTO blocks_3x3 (position, "
        "p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot, "
        "p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot, "
        "p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot) "
        "VALUES (" + ",".join("?" * 19) + ")"
    )

    while True:
        chunk = f.read(BATCH * ROW_SIZE)
        if not chunk:
            # No new data — sleep and check again
            time.sleep(args.poll_interval)
            cur_size = os.path.getsize(args.raw)
            producer_alive = is_pid_alive(args.producer_pid)
            if cur_size == last_size and not producer_alive:
                print(f"[sidecar] producer dead + file stable. exiting.", flush=True)
                break
            last_size = cur_size
            continue
        # Process this chunk
        n_rows = len(chunk) // ROW_SIZE
        if n_rows == 0:
            continue
        rows = []
        for i in range(n_rows):
            base = i * ROW_SIZE
            pos = chunk[base]
            row = [pos]
            for j in range(9):
                cell_off = base + 1 + j * 3
                pid = chunk[cell_off] | (chunk[cell_off + 1] << 8)
                rot = chunk[cell_off + 2]
                row.append(pid)
                row.append(rot)
            rows.append(tuple(row))
        # Bulk insert
        with conn:
            conn.executemany(insert_sql, rows)
        total_indexed += n_rows
        now = time.time()
        if now - last_t >= 2.0:
            rate = (total_indexed - last_total) / (now - last_t)
            print(f"[sidecar] indexed={total_indexed} rate={rate:.0f}/s file_size={os.path.getsize(args.raw)/1_000_000:.1f}MB",
                  flush=True)
            last_t = now
            last_total = total_indexed
        # If we got a full batch, immediately try again
        if n_rows < BATCH:
            time.sleep(0.05)

    f.close()
    n_rows_in_db = conn.execute("SELECT COUNT(*) FROM blocks_3x3").fetchone()[0]
    print(f"[sidecar] TOTAL indexed: {n_rows_in_db}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
