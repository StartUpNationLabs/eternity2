from enum import Enum

from eternity2.pattern import Pattern
from eternity2.pattern_svg_definition import PatternSvgDefinition


class OfficialPatterns(Enum):
    """
    The official patterns for the Eternity II puzzle.
    """
    GREY = Pattern(
        name="GREY",
        binary="0000000000000000",
        bucas_letter="A",
        svg=PatternSvgDefinition(
            "A",
            "#9a9a9a",
            "black",
            None,
            None,
            None
        )
    )
    BG_ORANGE_CONCAVE_FORT = Pattern(
        name="BG_ORANGE_CONCAVE_FORT",
        binary="0000000000000001",
        bucas_letter="B",
        svg=PatternSvgDefinition(
            "B",
            "#f88512",
            "black",
            "m-128,-80 h 16 a64,64 30 0,0 64,64 v 32 a64,64 30 0,0 -64,64 h -16",
            "#80d5f8",
            "#9ea599"
        )
    )
    BG_BLUE_FLOWER = Pattern(
        name="BG_BLUE_FLOWER",
        binary="0000000000000010",
        bucas_letter="C",
        svg=PatternSvgDefinition(
            "C",
            "#155c8c",
            "black",
            "m-128,-64 a32,32 30 0,1 32,32 a32,32 30 0,1 0,64 a32,32 30 0,1 -32,32 v -32 a32,32 30 0,0 0,-64",
            "#fef102",
            "#7c8c48"
        )
    )
    BG_PINK_HOLLOW_CONCAVE_FORT = Pattern(
        name="BG_PINK_CONCAVE_FORT_HOLLOW",
        binary="0000000000000011",
        bucas_letter="D",
        svg=PatternSvgDefinition(
            "D",
            "#ec35a0",
            "black",
            "m-128,-80 h 16 a64,64 30 0,0 64,64 v 32 a64,64 30 0,0 -64,64 h -16 v -48 a32,32 30 1,0 0,-64",
            "#81d1f0",
            "#af4f8d"
        )
    )
    BG_GREEN_HOLLOW_SQUARE = Pattern(
        name="BG_GREEN_SQUARE_HOLLOW",
        binary="0000000000000100",
        bucas_letter="E",
        svg=PatternSvgDefinition(
            "E",
            "#33b441",
            "black",
            "m-128,-64 h 32 l 32,32 v  64 l -32,32 h -32 v -16 a48,48 30 1,0 0,-96",
            "#265e93",
            "#3b6c8c"
        )
    )
    BG_RED_ROUND_FORT = Pattern(
        name="BG_RED_ROUND_FORT",
        binary="0000000000000101",
        bucas_letter="F",
        svg=PatternSvgDefinition(
            "F",
            "#831b43",
            "black",
            "m-128,0 m-8,-40 a16,16 30 1,1 16,0 l 32,32 a16,16 30 1,1 0,16 l -32,32 a16,16 30 1,1 -16,0 l 8,-16 l 24,-24 l -24,-24",
            "#f48614",
            "#b76742"
        )
    )
    BG_PINK_ROUND_CROSS = Pattern(
        name="BG_PINK_ROUND_CROSS",
        binary="0000000000000110",
        bucas_letter="G",
        svg=PatternSvgDefinition(
            "G",  # O6
            "#ee3ea8",
            "black",
            "m-8,0 m-128,0 v -8 v -32 a16,16 30 1,1 16,0 v 32 h 32 a16,16 30 1,1 0,16 h -32 v 32 a16,16 30 1,1 -16,0 v -32",
            "#f0ed24",
            "#d7ad60"
        )
    )
    BG_PURPLE_POINTY_CROSS = Pattern(
        name="BG_PURPLE_POINTY_CROSS",
        binary="0000000000000111",
        bucas_letter="H",
        svg=PatternSvgDefinition(
            "H",  # O7
            "#864ba3",
            "black",
            "m-128,-96 l 32,32 l -8,40 l 40,-8 l 32,32 l -32,32 l -40,-8 l 8,40 l -32,32",
            "#b6e8f9",
            "#8d8db2"
        )
    )
    BG_YELLOW_STAR = Pattern(
        name="BG_YELLOW_STAR",
        binary="0000000000001000",
        bucas_letter="I",
        svg=PatternSvgDefinition(
            "I",
            "#eded25",
            "black",
            "m-128,-32 l 32,-32 v 48 l 32,16 l -32,16 v 48 l -32,-32",
            "#43aee6",
            "#92ad65"
        )
    )
    BG_PURPLE_CROSS = Pattern(
        name="BG_PURPLE_CROSS",
        binary="0000000000001001",
        bucas_letter="J",
        svg=PatternSvgDefinition(
            "J",
            "#854aa3",
            "black",
            "m-128,-32 v -32 a64,64 30 0,1 0,128 v -40 l 24, 24 l 24,-24 l -24,-24 l 24,-24 l -24,-24 l -24,24",
            "#eced25",
            "#c9bb4b"
        )
    )
    BG_GREEN_ROUND_CROSS = Pattern(
        name="BG_GREEN_ROUND_CROSS",
        binary="0000000000001010",
        bucas_letter="K",
        svg=PatternSvgDefinition(
            "K",
            "#32b459",
            "black",
            "m-128,0 m-8,0 v -8 v -32 a16,16 30 1,1 16,0 v 32 h 32 a16,16 30 1,1 0,16 h -32 v 32 a16,16 30 1,1 -16,0 v -32",
            "#ee3ea8",
            "#698367"
        )
    )
    BG_RED_CROSS = Pattern(
        name="BG_RED_CROSS",
        binary="0000000000001011",
        bucas_letter="L",
        svg=PatternSvgDefinition(
            "L",
            "#ac3c6b",
            "black",
            "m-128,-32 v -32 a64,64 30 0,1 0,128 v -40 l 24, 24 l 24,-24 l -24,-24 l 24,-24 l -24,-24 l -24,24",
            "#2bb35a",
            "#76615e"
        )
    )
    BG_GREEN_POINTY_CROSS = Pattern(
        name="BG_GREEN_POINTY_CROSS",
        binary="0000000000001100",
        bucas_letter="M",
        svg=PatternSvgDefinition(
            "M",
            "#2bb35a",
            "black",
            "m-128,-96 l 32,32 l -8,40 l 40,-8 l 32,32 l -32,32 l -40,-8 l 8,40 l -32,32",
            "#f4892a",
            "#778e3d"
        )
    )
    BG_RED_STAR = Pattern(
        name="BG_RED_STAR",
        binary="0000000000001101",
        bucas_letter="N",
        svg=PatternSvgDefinition(
            "N",
            "#ac3c6b",
            "black",
            "m-128,-32 l 32,-32 v 48 l 32,16 l -32,16 v 48 l -32,-32",
            "#eced29",
            "#944b53"
        )
    )
    BG_BLUE_SQUARE_FORT = Pattern(
        name="BG_BLUE_SQUARE_FORT",
        binary="0000000000001110",
        bucas_letter="O",
        svg=PatternSvgDefinition(
            "O",
            "#5cc9f2",
            "black",
            "m-128,-96 l 32,32 l -8,8 l 32,32 l 8,-8 l 32,32 l -32,32 l -8,-8 l -32,32 l 8,8 l -32,32",
            "#ee3fa8",
            "#8682bc"
        )
    )
    BG_YELLOW_SQUARE = Pattern(
        name="BG_YELLOW_SQUARE",
        binary="0000000000001111",
        bucas_letter="P",
        svg=PatternSvgDefinition(
            "P",
            "#eded25",
            "black",
            "m-128,-96 l 96,96 l -96, "
            "96 v -32 l 64,-64 l -64,-64",
            "#2bb356",
            "#cbcd2a"
        )
    )
    BG_BLUE_POINTY_CROSS = Pattern(
        name="BG_BLUE_POINTY_CROSS",
        binary="0000000000010000",
        bucas_letter="Q",
        svg=PatternSvgDefinition(
            "Q",
            "#5cc9f2",
            "black",
            "m-128,-96 l 32,32 l -8,40 l 40,-8 l 32,32 l -32,32 l -40,-8 l 8,40 l -32,32",
            "#ee3fa8",
            "#8682bc"
        )
    )
    BG_YELLOW_SQUARE_FORT = Pattern(
        name="BG_YELLOW_SQUARE_FORT",
        binary="0000000000010001",
        bucas_letter="R",
        svg=PatternSvgDefinition(
            "R",
            "#eded25",
            "black",
            "m-128,-96 l 32,32 l -8,8 l 32,32 l 8,-8 l 32,32 l -32,32 l -8,-8 l -32,32 l 8,8 l -32,32",
            "#2bb356",
            "#cbcd2a"
        )
    )
    BG_ORANGE_STAR = Pattern(
        name="BG_ORANGE_STAR",
        binary="0000000000010010",
        bucas_letter="S",
        svg=PatternSvgDefinition(
            "S",
            "#f88826",
            "black",
            "m-128,-32 l 32,-32 v 48 l 32,16 l -32,16 v 48 l -32,-32",
            "#864ca4",
            "#b56844"
        )
    )
    BG_BLUE_ROUND_CROSS = Pattern(
        name="BG_BLUE_ROUND_CROSS",
        binary="0000000000010011",
        bucas_letter="T",
        svg=PatternSvgDefinition(
            "T",
            "#26638e",
            "black",
            "m-8,0 m-128,0 v -8 v -32 a16,16 30 1,1 16,0 v 32 h 32 a16,16 30 1,1 0,16 h -32 v 32 a16,16 30 1,1 -16,0 v -32",
            "#f38622",
            "#c1732d"
        )
    )
    BG_BLUE_SQUARE = Pattern(
        name="BG_BLUE_SQUARE",
        binary="0000000000010100",
        bucas_letter="U",
        svg=PatternSvgDefinition(
            "U",  # 14
            "#265e92",
            "black",
            "m-128,-96 l 96,96 l -96, "
            "96 v -32 l 64,-64 l -64,-64",
            "#75cff2",
            "#4585ad"
        )
    )
    BG_PINK_SQUARE_FORT = Pattern(
        name="BG_PINK_SQUARE_FORT",
        binary="0000000000010101",
        bucas_letter="V",
        svg=PatternSvgDefinition(
            "V",
            "#ed3da5",
            "black",
            "m-128,-96 l 32,32 l -8,8 l 32,32 l 8,-8 l 32,32 l -32,32 l -8,-8 l -32,32 l 8,8 l -32,32",
            "#fdf102",
            "#edc524"
        )
    )
    BG_BLUE_CROSS = Pattern(
        name="BG_BLUE_CROSS",
        binary="0000000000010110",
        bucas_letter="W",
        svg=PatternSvgDefinition(
            "W",
            "#145c8c",
            "black",
            "m-128,-32 v -32 a64,64 30 0,1 0,128 v -40 l 24, 24 l 24,-24 l -24,-24 l 24,-24 l -24,-24 l -24,24",
            "#ec359e",
            "#a95397"
        )
    )
