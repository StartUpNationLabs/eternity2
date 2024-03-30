from uuid import uuid4

from lxml.etree import _Element

from eternity2.direction import Direction
from eternity2.official_patterns import OfficialPatterns
from eternity2.pattern import Pattern
from eternity2.pattern_utils import create_piece_svg


class Piece:
    _id: int
    is_hint: bool
    svg: _Element
    pattern_top: Pattern
    pattern_right: Pattern
    pattern_bottom: Pattern
    pattern_left: Pattern

    def __init__(self,
                 pattern_top: Pattern,
                 pattern_right: Pattern,
                 pattern_bottom: Pattern,
                 pattern_left: Pattern
                 ):
        self._id = uuid4().int

        # Assert that each direction is represented by a pattern
        for direction in Direction:
            assert direction in [pattern_top.svg.direction, pattern_right.svg.direction, pattern_bottom.svg.direction,
                                 pattern_left.svg.direction], f"Pattern for direction {direction} is missing"
            self.pattern_top = pattern_top
            self.pattern_right = pattern_right
            self.pattern_bottom = pattern_bottom
            self.pattern_left = pattern_left

        self.set_svg()

    def set_hint(self):
        self.is_hint = True

    def set_svg(self):
        self.svg = create_piece_svg(
            self.pattern_top.svg,
            self.pattern_right.svg,
            self.pattern_bottom.svg,
            self.pattern_left.svg
        )

    @staticmethod
    def from_bucas_letters(letters: str):
        # The string must be of size 4
        if len(letters) != 4:
            raise ValueError(f"Invalid piece string: {letters}")

        patterns: list[Pattern] = []

        # Get the patterns from the official ones
        for index, letter in enumerate(letters):
            capitalized_letter = letter.capitalize()

            for pattern in OfficialPatterns:
                if pattern.value.bucas_letter == capitalized_letter:
                    direction = Direction(index)
                    pattern_to_use: Pattern = pattern.value.copy()
                    pattern_to_use.set_svg_direction(direction)
                    patterns.append(pattern_to_use)

        return Piece(
            pattern_top=patterns[0],
            pattern_right=patterns[1],
            pattern_bottom=patterns[2],
            pattern_left=patterns[3]
        )
