from lxml.etree import _Element
from svg_ultralight import write_svg

from bucas.bucas_e2_pieces import BUCAS_E2_PIECES
from eternity2.pattern_utils import merge_svg_into_one
from eternity2.piece import Piece


def get_official_pieces_svg() -> list[_Element]:
    pieces: list[Piece] = []
    for piece_letters in BUCAS_E2_PIECES:
        pieces.append(Piece.from_bucas_letters(piece_letters))

    svg_list: list[_Element] = []
    for piece in pieces:
        svg_list.append(piece.svg)

    return svg_list


def get_official_board_svg() -> _Element:
    pieces_svg = get_official_pieces_svg()
    size = int(len(pieces_svg) ** 0.5)

    # Merge the pieces into one SVG
    puzzle = merge_svg_into_one(pieces_svg,
                                view_box=(0, 0, size * 256, size * 256),
                                width=size * 256,
                                height=size * 256
                                )

    # Set the position of each piece
    for index, element in enumerate(puzzle):
        x = (index % size) * 256
        y = (index // size) * 256
        element.set("transform", f"translate({x}, {y})")

    return puzzle


if __name__ == "__main__":
    puzzle = get_official_board_svg()
    filename = "official-puzzle.svg"
    write_svg(filename, puzzle)
