#!/usr/bin/env python3
"""Represent an E2 board as pixels, waves, and a short audio trace.

The goal is not visualization for its own sake. This script extracts a
small signal fingerprint from the mismatch field of a board:

  - cell_mismatch_count[y][x]: number of bad incident edges per cell
  - row/column profiles: 1D projections of the defect field
  - 2D FFT radial energy: crude "wave" signature of defect geometry
  - PGM images: inspectable grayscale maps without external libraries
  - WAV scanline sonification: optional human-audible defect trace

Input JSON formats:
  - {"placement": [{"pos":..., "piece_id":..., "rotation":...}, ...]}
  - {"bucas_url": "...board_edges=..."}
  - {"url": "...board_edges=..."} from output/community_corpus

Usage:
  python3 scripts/board_signal_probe.py output/v17_overnight/chunk_0019/alns_board.json \
      --out-dir output/signal_probe/chunk_0019 --wav
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import wave
from pathlib import Path

try:
    import numpy as np
except Exception:  # pragma: no cover - script remains useful without FFT.
    np = None

W = 16
H = 16
BORDER = 0


def load_pieces(puzzle_path: Path) -> list[list[int]]:
    pieces: list[list[int]] = []
    with puzzle_path.open() as f:
        lines = [line.strip() for line in f if line.strip()]
    for line in lines[1:]:
        cols = line.split(",")

        def color_value(raw: str) -> int:
            value = int(raw, 2)
            return 0 if value == 65535 else value

        pieces.append([color_value(cols[i]) for i in range(4)])
    return pieces


def rotated(edges: list[int], rot: int) -> list[int]:
    rot %= 4
    if rot == 0:
        return edges
    if rot == 1:
        return [edges[3], edges[0], edges[1], edges[2]]
    if rot == 2:
        return [edges[2], edges[3], edges[0], edges[1]]
    return [edges[1], edges[2], edges[3], edges[0]]


def parse_bucas_edges(url: str) -> list[tuple[int, int, int, int]] | None:
    match = re.search(r"board_edges=([a-z]+)", url)
    if not match:
        return None
    blob = match.group(1)
    if len(blob) < W * H * 4:
        return None
    return [
        tuple(ord(blob[pos * 4 + i]) - ord("a") for i in range(4))
        for pos in range(W * H)
    ]


def board_edges(data: dict, pieces: list[list[int]]) -> list[tuple[int, int, int, int]]:
    url = data.get("bucas_url") or data.get("url")
    if isinstance(url, str):
        parsed = parse_bucas_edges(url)
        if parsed is not None:
            return parsed

    cells: list[tuple[int, int] | None] = [None] * (W * H)
    for item in data.get("placement", []):
        if item is None:
            continue
        cells[int(item["pos"])] = (int(item["piece_id"]), int(item["rotation"]))

    out: list[tuple[int, int, int, int]] = []
    for cell in cells:
        if cell is None:
            out.append((0, 0, 0, 0))
            continue
        pid, rot = cell
        out.append(tuple(rotated(pieces[pid], rot)))
    return out


def mismatch_fields(edges: list[tuple[int, int, int, int]]) -> dict:
    cell = [[0 for _ in range(W)] for _ in range(H)]
    horizontal = [[0 for _ in range(W - 1)] for _ in range(H)]
    vertical = [[0 for _ in range(W)] for _ in range(H - 1)]
    matched = 0
    mismatched = 0

    for y in range(H):
        for x in range(W):
            pos = y * W + x
            if x + 1 < W:
                a = edges[pos][1]
                b = edges[pos + 1][3]
                if a != BORDER and b != BORDER:
                    if a == b:
                        matched += 1
                    else:
                        mismatched += 1
                        horizontal[y][x] = 1
                        cell[y][x] += 1
                        cell[y][x + 1] += 1
            if y + 1 < H:
                a = edges[pos][2]
                b = edges[pos + W][0]
                if a != BORDER and b != BORDER:
                    if a == b:
                        matched += 1
                    else:
                        mismatched += 1
                        vertical[y][x] = 1
                        cell[y][x] += 1
                        cell[y + 1][x] += 1

    return {
        "cell": cell,
        "horizontal": horizontal,
        "vertical": vertical,
        "matched": matched,
        "mismatched": mismatched,
    }


def radial_fft_energy(cell: list[list[int]]) -> dict:
    if np is None:
        return {"available": False}
    a = np.array(cell, dtype=float)
    a -= a.mean()
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    cy, cx = H // 2, W // 2
    rings: dict[int, float] = {}
    for y in range(H):
        for x in range(W):
            r = int(round(math.hypot(y - cy, x - cx)))
            rings[r] = rings.get(r, 0.0) + float(spectrum[y, x])
    total = sum(rings.values()) or 1.0
    return {
        "available": True,
        "rings": {str(k): v / total for k, v in sorted(rings.items())},
        "low_freq_energy": sum(v for k, v in rings.items() if k <= 2) / total,
        "mid_freq_energy": sum(v for k, v in rings.items() if 3 <= k <= 5) / total,
        "high_freq_energy": sum(v for k, v in rings.items() if k >= 6) / total,
    }


def write_pgm(path: Path, values: list[list[int]], scale: int = 18) -> None:
    max_v = max(max(row) for row in values) or 1
    rows: list[list[int]] = []
    for row in values:
        expanded_row = [int(round(255 * v / max_v)) for v in row for _ in range(scale)]
        for _ in range(scale):
            rows.append(expanded_row)
    with path.open("w") as f:
        f.write(f"P2\n{len(rows[0])} {len(rows)}\n255\n")
        for row in rows:
            f.write(" ".join(str(v) for v in row))
            f.write("\n")


def write_wav(path: Path, row_profile: list[int], col_profile: list[int]) -> None:
    sample_rate = 44100
    duration_per_value = 0.16
    values = row_profile + col_profile
    max_v = max(values) or 1
    samples: list[int] = []
    for i, value in enumerate(values):
        freq = 220.0 + 660.0 * (value / max_v)
        amp = 0.15 + 0.75 * (value / max_v)
        n = int(sample_rate * duration_per_value)
        for t in range(n):
            env = min(1.0, t / 600.0, (n - t) / 600.0)
            s = amp * env * math.sin(2.0 * math.pi * freq * t / sample_rate)
            samples.append(int(max(-1.0, min(1.0, s)) * 32767))
        if i == 15:
            samples.extend([0] * int(sample_rate * 0.25))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json", type=Path)
    ap.add_argument(
        "--puzzle",
        type=Path,
        default=Path("../data/puzzles/size_16_official_eternity.csv"),
    )
    ap.add_argument("--out-dir", type=Path, default=Path("output/signal_probe"))
    ap.add_argument("--wav", action="store_true")
    args = ap.parse_args()

    data = json.loads(args.board_json.read_text())
    pieces = load_pieces(args.puzzle)
    edges = board_edges(data, pieces)
    fields = mismatch_fields(edges)
    cell = fields["cell"]
    row_profile = [sum(row) for row in cell]
    col_profile = [sum(cell[y][x] for y in range(H)) for x in range(W)]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_pgm(args.out_dir / "cell_mismatch.pgm", cell)
    write_pgm(args.out_dir / "row_profile.pgm", [[v] for v in row_profile], scale=18)
    if args.wav:
        write_wav(args.out_dir / "mismatch_scan.wav", row_profile, col_profile)

    summary = {
        "source": str(args.board_json),
        "matched": fields["matched"],
        "mismatched": fields["mismatched"],
        "row_profile": row_profile,
        "col_profile": col_profile,
        "cell_mismatch_count": cell,
        "fft": radial_fft_energy(cell),
    }
    (args.out_dir / "signal_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
