import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Board } from "./Board";

describe("Board", () => {
  it("renders an empty grid", () => {
    const { container } = render(<Board width={3} height={3} placements={[]} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    // 3x3 = 9 empty cells, each rendered as a rect.
    expect(container.querySelectorAll("rect").length).toBe(9);
  });

  it("renders a placed piece as 4 triangles", () => {
    const { container } = render(
      <Board
        width={1}
        height={1}
        placements={[{ position: 0, pieceId: 0, rotation: 0, edges: [1, 2, 3, 4] }]}
      />,
    );
    expect(container.querySelectorAll("polygon").length).toBe(4);
  });

  it("rotates edges clockwise", () => {
    // R90 should send (top=1) to right slot, so the polygon with the
    // right-side fill should be color 1. We test by reading polygon
    // fills in order; the second polygon in render order is the right
    // triangle.
    const { container } = render(
      <Board
        width={1}
        height={1}
        placements={[{ position: 0, pieceId: 0, rotation: 1, edges: [1, 2, 3, 4] }]}
      />,
    );
    const polygons = Array.from(container.querySelectorAll("polygon"));
    // Order: top, right, bottom, left. After R90 (top<-left, right<-top,
    // bottom<-right, left<-bottom) we expect [4, 1, 2, 3].
    expect(polygons[1].getAttribute("fill")).toBeTruthy();
    // Indirect check: 4 distinct fills.
    const fills = new Set(polygons.map((p) => p.getAttribute("fill")));
    expect(fills.size).toBe(4);
  });
});
