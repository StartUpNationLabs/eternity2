import os

from svg_ultralight import write_svg

from eternity2.direction import Direction
from bucas_e2_pieces import BUCAS_E2_PIECES
from eternity2.pattern_utils import create_pattern_svg, merge_svg_into_one
from eternity2.official_patterns import OfficialPatterns


def convert_bucas_piece_to_svg(piece_string):
    # Each piece is described by 4 characters representing the pattern on the pieces
    pieces_svg = []
    for index, letter in enumerate(piece_string):
        capitalized_letter = letter.capitalize()

        for pattern in OfficialPatterns:
            if pattern.value.bucas_letter == capitalized_letter:
                motif = pattern.value.svg
                direction = Direction(index)
                pieces_svg.append(create_pattern_svg(motif, direction))

    # Save the piece
    svg = merge_svg_into_one(pieces_svg)
    return svg


def generate_eternity_2_official_pieces():
    full_sets = []
    for pieces_string in BUCAS_E2_PIECES:
        svg = convert_bucas_piece_to_svg(pieces_string)
        full_sets.append(svg)
    return full_sets


def save_official_pieces():
    output_dir = "official_pieces"
    os.makedirs(output_dir, exist_ok=True)

    full_sets = generate_eternity_2_official_pieces()
    pieces_string = BUCAS_E2_PIECES
    for index, svg in enumerate(full_sets):
        svg_filename = f'{output_dir}/{index}-{pieces_string[index]}.svg'
        write_svg(svg_filename, svg)


if __name__ == "__main__":
    save_official_pieces()
