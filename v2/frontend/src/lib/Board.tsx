// Board.svg primitive (V2_DESIGN.md "Stays — SVG board/piece rendering").
// Renders a width×height grid of pieces. Each piece is a 4-triangle SVG
// where the triangle colors are taken from `edges` after applying the
// requested rotation.

import { useMemo } from "react";

export type Edges = [number, number, number, number]; // [top,right,bottom,left]

export interface PiecePlacement {
  position: number;        // row-major: y*width + x
  pieceId: number;
  rotation: number;        // 0..3 quarter-turns clockwise
  edges: Edges;            // edges as defined on the piece (before rotation)
}

export interface BoardProps {
  width: number;
  height: number;
  cellSize?: number;
  placements: PiecePlacement[];
  colorPalette?: string[];
}

const DEFAULT_PALETTE = [
  "#444444", // 0 = border (gray)
  "#ef4444", "#3b82f6", "#22c55e", "#eab308",
  "#a855f7", "#ec4899", "#06b6d4", "#f97316",
  "#84cc16", "#14b8a6", "#6366f1",
];

function rotateEdges([t, r, b, l]: Edges, rot: number): Edges {
  // Match Edges::rotated in core/src/piece.rs (clockwise rotation:
  // R90 sends top<-left, right<-top, bottom<-right, left<-bottom).
  switch (rot & 3) {
    case 0: return [t, r, b, l];
    case 1: return [l, t, r, b];
    case 2: return [b, l, t, r];
    default: return [r, b, l, t];
  }
}

export function Board({ width, height, cellSize = 60, placements, colorPalette = DEFAULT_PALETTE }: BoardProps) {
  const byPos = useMemo(() => {
    const m = new Map<number, PiecePlacement>();
    for (const p of placements) m.set(p.position, p);
    return m;
  }, [placements]);

  const W = width * cellSize;
  const H = height * cellSize;
  const color = (c: number) => colorPalette[c] ?? "#cccccc";

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="bg-zinc-100 rounded">
      {Array.from({ length: height }, (_, y) =>
        Array.from({ length: width }, (_, x) => {
          const pos = y * width + x;
          const placed = byPos.get(pos);
          const cx = x * cellSize;
          const cy = y * cellSize;
          if (!placed) {
            return (
              <rect
                key={pos}
                x={cx}
                y={cy}
                width={cellSize}
                height={cellSize}
                fill="white"
                stroke="#e5e7eb"
              />
            );
          }
          const [t, r, b, l] = rotateEdges(placed.edges, placed.rotation);
          const mx = cx + cellSize / 2;
          const my = cy + cellSize / 2;
          return (
            <g key={pos}>
              <polygon points={`${cx},${cy} ${cx + cellSize},${cy} ${mx},${my}`} fill={color(t)} stroke="#000" strokeWidth={0.5} />
              <polygon points={`${cx + cellSize},${cy} ${cx + cellSize},${cy + cellSize} ${mx},${my}`} fill={color(r)} stroke="#000" strokeWidth={0.5} />
              <polygon points={`${cx + cellSize},${cy + cellSize} ${cx},${cy + cellSize} ${mx},${my}`} fill={color(b)} stroke="#000" strokeWidth={0.5} />
              <polygon points={`${cx},${cy + cellSize} ${cx},${cy} ${mx},${my}`} fill={color(l)} stroke="#000" strokeWidth={0.5} />
            </g>
          );
        }),
      )}
    </svg>
  );
}
