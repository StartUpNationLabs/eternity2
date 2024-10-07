from eternity2.direction import Direction
from eternity2.pattern_svg_definition import PatternSvgDefinition


class Pattern:
    name: str
    binary: str
    bucas_letter: str
    svg: PatternSvgDefinition

    def __init__(self, name: str, binary: str, bucas_letter: str, svg: PatternSvgDefinition):
        self.name = name
        self.binary = binary
        self.bucas_letter = bucas_letter
        self.svg = svg

    def set_svg_direction(self, direction: Direction):
        self.svg.direction = direction

    def copy(self):
        return Pattern(self.name, self.binary, self.bucas_letter, self.svg.copy())
