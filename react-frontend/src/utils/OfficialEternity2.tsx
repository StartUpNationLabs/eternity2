import {EternityPattern} from "./EternityPattern.tsx";
import {Direction} from "./Constants.tsx";
import {Hint} from "../proto/solver/v1/solver.ts";
import {Board} from "./interface.tsx";
import {boardRearrangedWithHints, convertBucasBoardToRotatedPieces} from "./utils.tsx";

/**
 * Those are the official pieces for the puzzle
 * Each piece is a string of 4 characters, each character can be a letter from 'a' to 'v'.
 * Each letter then corresponds to a specific pattern.
 */
export const ETERNITY_II_PIECES = [
    "aabd", "aabe", "aacd", "aadc", "abgb", "abhc", "abjb", "abjf", "abmd", "aboe", "abpc", "abte",
    "abtf", "abve", "achb", "acid", "ackf", "acnf", "acoc", "acpc", "acqe", "acrb", "acrf", "acsb",
    "acvb", "adgc", "adgd", "adhd", "adid", "adof", "adpc", "adsd", "adtc", "adte", "aduf", "adwe",
    "aeib", "aelf", "aemf", "aenc", "aend", "aepb", "aepc", "aepd", "aeqb", "aese", "aete", "aeue",
    "afgf", "afhb", "afhc", "afjb", "afoe", "afqe", "afqf", "aftd", "afub", "afuf", "afvc", "afwd",
    "ggji", "ggko", "ghhl", "gigt", "giiw", "gikk", "gimh", "gisj", "giwt", "gllo", "glor", "gmki",
    "gmpq", "gmsp", "gmtl", "gnkp", "gnnp", "golu", "gosl", "gouv", "gpni", "gqii", "gqmq", "grin",
    "grjk", "grtr", "grus", "gsgv", "gsjw", "gsqu", "gtmr", "gtnp", "gtnq", "gtqv", "gtrk", "gvvl",
    "gwqn", "gwst", "gwvj", "gwwv", "hhrp", "hhru", "hhun", "hhwj", "hiqp", "hjlt", "hjnt", "hjqp",
    "hjum", "hkpr", "hkrp", "hlsn", "hlsu", "hmkq", "hmor", "hmrm", "hmwu", "hnlv", "hour", "hptw",
    "hqkw", "hsju", "hskn", "hssp", "htrw", "htvp", "hukj", "hunv", "huql", "hust", "hvjs", "hvrk",
    "hwku", "hwmq", "hwql", "hwus", "iiso", "ijjl", "ijjm", "ijjr", "ijnv", "ijpj", "ijur", "ijvv",
    "iklq", "ilir", "iliw", "illk", "ilpr", "injm", "inqw", "iomm", "iomn", "iowu", "iqoo", "iqor",
    "iqwo", "isou", "istj", "itvv", "iujs", "iuks", "iwpm", "iwqu", "jklq", "jkqt", "jmll", "jnmp",
    "jnnv", "joqt", "josu", "jovm", "jppp", "jprs", "jqov", "jron", "jskq", "jtru", "jttp", "juou",
    "jvmu", "jvom", "kknt", "klwo", "kmnr", "kmtt", "knvo", "kokv", "koln", "koun", "kpll", "kpps",
    "kqmo", "krvm", "krvw", "krwp", "ksmw", "ksnt", "ksss", "ktnl", "kuvt", "kuwo", "kvrn", "kvrt",
    "kvul", "kvwv", "llwo", "lmnw", "lmtp", "lomn", "loup", "lplu", "lqtt", "lrls", "lrqw", "lrwv",
    "lsnp", "luqr", "lvmq", "lwmu", "lwvv", "lwvw", "mmrw", "mmso", "mmup", "monp", "morr", "mqnt",
    "msow", "msut", "mtrs", "mtrv", "nnns", "nouq", "nqoq", "nqos", "nqrp", "nrqu", "nspw", "nsvp",
    "ntov", "ntqv", "oppr", "opst", "oqws", "ovuw", "ppvw", "pqrq", "prqv", "psuv", "qqwt", "qrtr",
    "rtus", "suvu", "swuw", "twvw"
]

/**
 * index : piece position
 * x : x coordinate
 * y : y coordinate
 * rotation : 0, 1, 2, 3
 */
// starts counting from 1 in : https://groups.io/g/eternity2/topic/47714652?p=Created,,,20,2,0,0::recentpostdate%2Fsticky,,,20,2,0,47714652 so added -1
export const ETERNITY_II_HINTS: Hint[] = [
    {
        index: 138, // from website : 139
        x: 7,
        y: 8,
        rotation: 2
    },
    {
        index: 248, // from website : 249
        x: 13,
        y: 13,
        rotation: 0
    },
    {
        index: 180, // from website : 181
        x: 2,
        y: 13,
        rotation: 3
    },
    {
        index: 254, // from website : 255
        x: 13,
        y: 2,
        rotation: 3
    },
    {
        index: 207, // from website : 208
        x: 2,
        y: 2,
        rotation: 3
    }
]

/**
 * ==============================================================================================================
 * export constant for patterns
 * ==============================================================================================================
 */

export const PATTERN_GREY: EternityPattern = {
    name: "GREY",
    binaryInt: 65535,
    bucasLetter: "A",
    svg: {
        name: "A",
        bg_color: "#9a9a9a",
        bg_stroke: "black",
        path: "",
        path_color: "",
        path_stroke: "",
        direction: Direction.Left,
    },
}

export const PATTERN_GREY_2: EternityPattern = {
    name: "GREY",
    binaryInt: 0,
    bucasLetter: "A",
    svg: {
        name: "A",
        bg_color: "#9a9a9a",
        bg_stroke: "black",
        path: "",
        path_color: "",
        path_stroke: "",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_ORANGE_CONCAVE_FORT: EternityPattern = {
    name: "BG_ORANGE_CONCAVE_FORT",
    binaryInt: 1,
    bucasLetter: "B",
    svg: {
        name: "B",
        bg_color: "#f88512",
        bg_stroke: "black",
        path: "m-128,-80 h 16 a64,64 30 0,0 64,64 v 32 a64,64 30 0,0 -64,64 h -16",
        path_color: "#80d5f8",
        path_stroke: "#9ea599",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_BLUE_FLOWER: EternityPattern = {
    name: "BG_BLUE_FLOWER",
    binaryInt: 2,
    bucasLetter: "C",
    svg: {
        name: "C",
        bg_color: "#155c8c",
        bg_stroke: "black",
        path: "m-128,-64 a32,32 30 0,1 32,32 a32,32 30 0,1 0,64 a32,32 30 0,1 -32,32 v -32 a32,32 30 0,0 0,-64",
        path_color: "#fef102",
        path_stroke: "#7c8c48",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_PINK_HOLLOW_CONCAVE_FORT: EternityPattern = {
    name: "BG_PINK_HOLLOW_CONCAVE_FORT",
    binaryInt: 3,
    bucasLetter: "D",
    svg: {
        name: "D",
        bg_color: "#ec35a0",
        bg_stroke: "black",
        path: "m-128,-80 h 16 a64,64 30 0,0 64,64 v 32 a64,64 30 0,0 -64,64 h -16 v -48 a32,32 30 1,0 0,-64",
        path_color: "#81d1f0",
        path_stroke: "#af4f8d",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_GREEN_HOLLOW_SQUARE: EternityPattern = {
    name: "BG_GREEN_HOLLOW_SQUARE",
    binaryInt: 4,
    bucasLetter: "E",
    svg: {
        name: "E",
        bg_color: "#33b441",
        bg_stroke: "black",
        path: "m-128,-64 h 32 l 32,32 v  64 l -32,32 h -32 v -16 a48,48 30 1,0 0,-96",
        path_color: "#265e93",
        path_stroke: "#3b6c8c",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_RED_ROUND_FORT: EternityPattern = {
    name: "BG_RED_ROUND_FORT",
    binaryInt: 5,
    bucasLetter: "F",
    svg: {
        name: "F",
        bg_color: "#831b43",
        bg_stroke: "black",
        path: "m-128,0 m-8,-40 a16,16 30 1,1 16,0 l 32,32 a16,16 30 1,1 0,16 l -32,32 a16,16 30 1,1 -16,0 l 8,-16 l 24,-24 l -24,-24",
        path_color: "#f48614",
        path_stroke: "#b76742",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_PINK_ROUND_CROSS: EternityPattern = {
    name: "BG_PINK_ROUND_CROSS",
    binaryInt: 6,
    bucasLetter: "G",
    svg: {
        name: "G",
        bg_color: "#ee3ea8",
        bg_stroke: "black",
        path: "m-8,0 m-128,0 v -8 v -32 a16,16 30 1,1 16,0 v 32 h 32 a16,16 30 1,1 0,16 h -32 v 32 a16,16 30 1,1 -16,0 v -32",
        path_color: "#f0ed24",
        path_stroke: "#d7ad60",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_PURPLE_POINTY_CROSS: EternityPattern = {
    name: "BG_PURPLE_POINTY_CROSS",
    binaryInt: 7,
    bucasLetter: "H",
    svg: {
        name: "H",
        bg_color: "#864ba3",
        bg_stroke: "black",
        path: "m-128,-96 l 32,32 l -8,40 l 40,-8 l 32,32 l -32,32 l -40,-8 l 8,40 l -32,32",
        path_color: "#b6e8f9",
        path_stroke: "#8d8db2",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_YELLOW_STAR: EternityPattern = {
    name: "BG_YELLOW_STAR",
    binaryInt: 8,
    bucasLetter: "I",
    svg: {
        name: "I",
        bg_color: "#eded25",
        bg_stroke: "black",
        path: "m-128,-32 l 32,-32 v 48 l 32,16 l -32,16 v 48 l -32,-32",
        path_color: "#43aee6",
        path_stroke: "#92ad65",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_PURPLE_CROSS: EternityPattern = {
    name: "BG_PURPLE_CROSS",
    binaryInt: 9,
    bucasLetter: "J",
    svg: {
        name: "J",
        bg_color: "#854aa3",
        bg_stroke: "black",
        path: "m-128,-32 v -32 a64,64 30 0,1 0,128 v -40 l 24, 24 l 24,-24 l -24,-24 l 24,-24 l -24,-24 l -24,24",
        path_color: "#eced25",
        path_stroke: "#c9bb4b",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_GREEN_ROUND_CROSS: EternityPattern = {
    name: "BG_GREEN_ROUND_CROSS",
    binaryInt: 10,
    bucasLetter: "K",
    svg: {
        name: "K",
        bg_color: "#32b459",
        bg_stroke: "black",
        path: "m-128,0 m-8,0 v -8 v -32 a16,16 30 1,1 16,0 v 32 h 32 a16,16 30 1,1 0,16 h -32 v 32 a16,16 30 1,1 -16,0 v -32",
        path_color: "#ee3ea8",
        path_stroke: "#698367",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_RED_CROSS: EternityPattern = {
    name: "BG_RED_CROSS",
    binaryInt: 11,
    bucasLetter: "L",
    svg: {
        name: "L",
        bg_color: "#ac3c6b",
        bg_stroke: "black",
        path: "m-128,-32 v -32 a64,64 30 0,1 0,128 v -40 l 24, 24 l 24,-24 l -24,-24 l 24,-24 l -24,-24 l -24,24",
        path_color: "#2bb35a",
        path_stroke: "#76615e",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_GREEN_POINTY_CROSS: EternityPattern = {
    name: "BG_GREEN_POINTY_CROSS",
    binaryInt: 12,
    bucasLetter: "M",
    svg: {
        name: "M",
        bg_color: "#2bb35a",
        bg_stroke: "black",
        path: "m-128,-96 l 32,32 l -8,40 l 40,-8 l 32,32 l -32,32 l -40,-8 l 8,40 l -32,32",
        path_color: "#f4892a",
        path_stroke: "#778e3d",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_RED_STAR: EternityPattern = {
    name: "BG_RED_STAR",
    binaryInt: 13,
    bucasLetter: "N",
    svg: {
        name: "N",
        bg_color: "#ac3c6b",
        bg_stroke: "black",
        path: "m-128,-32 l 32,-32 v 48 l 32,16 l -32,16 v 48 l -32,-32",
        path_color: "#eced29",
        path_stroke: "#944b53",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_BLUE_SQUARE_FORT: EternityPattern = {
    name: "BG_BLUE_SQUARE_FORT",
    binaryInt: 14,
    bucasLetter: "O",
    svg: {
        name: "O",
        bg_color: "#5cc9f2",
        bg_stroke: "black",
        path: "m-128,-96 l 32,32 l -8,8 l 32,32 l 8,-8 l 32,32 l -32,32 l -8,-8 l -32,32 l 8,8 l -32,32",
        path_color: "#ee3fa8",
        path_stroke: "#8682bc",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_YELLOW_SQUARE: EternityPattern = {
    name: "BG_YELLOW_SQUARE",
    binaryInt: 15,
    bucasLetter: "P",
    svg: {
        name: "P",
        bg_color: "#eded25",
        bg_stroke: "black",
        path: "m-128,-96 l 96,96 l -96, 96 v -32 l 64,-64 l -64,-64",
        path_color: "#2bb356",
        path_stroke: "#cbcd2a",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_BLUE_POINTY_CROSS: EternityPattern = {
    name: "BG_BLUE_POINTY_CROSS",
    binaryInt: 16,
    bucasLetter: "Q",
    svg: {
        name: "Q",
        bg_color: "#5cc9f2",
        bg_stroke: "black",
        path: "m-128,-96 l 32,32 l -8,40 l 40,-8 l 32,32 l -32,32 l -40,-8 l 8,40 l -32,32",
        path_color: "#ee3fa8",
        path_stroke: "#8682bc",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_YELLOW_SQUARE_FORT: EternityPattern = {
    name: "BG_YELLOW_SQUARE_FORT",
    binaryInt: 17,
    bucasLetter: "R",
    svg: {
        name: "R",
        bg_color: "#eded25",
        bg_stroke: "black",
        path: "m-128,-96 l 32,32 l -8,8 l 32,32 l 8,-8 l 32,32 l -32,32 l -8,-8 l -32,32 l 8,8 l -32,32",
        path_color: "#2bb356",
        path_stroke: "#cbcd2a",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_ORANGE_STAR: EternityPattern = {
    name: "BG_ORANGE_STAR",
    binaryInt: 18,
    bucasLetter: "S",
    svg: {
        name: "S",
        bg_color: "#f88826",
        bg_stroke: "black",
        path: "m-128,-32 l 32,-32 v 48 l 32,16 l -32,16 v 48 l -32,-32",
        path_color: "#864ca4",
        path_stroke: "#b56844",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_BLUE_ROUND_CROSS: EternityPattern = {
    name: "BG_BLUE_ROUND_CROSS",
    binaryInt: 19,
    bucasLetter: "T",
    svg: {
        name: "T",
        bg_color: "#26638e",
        bg_stroke: "black",
        path: "m-8,0 m-128,0 v -8 v -32 a16,16 30 1,1 16,0 v 32 h 32 a16,16 30 1,1 0,16 h -32 v 32 a16,16 30 1,1 -16,0 v -32",
        path_color: "#f38622",
        path_stroke: "#c1732d",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_BLUE_SQUARE: EternityPattern = {
    name: "BG_BLUE_SQUARE",
    binaryInt: 20,
    bucasLetter: "U",
    svg: {
        name: "U",
        bg_color: "#265e92",
        bg_stroke: "black",
        path: "m-128,-96 l 96,96 l -96, 96 v -32 l 64,-64 l -64,-64",
        path_color: "#75cff2",
        path_stroke: "#4585ad",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_PINK_SQUARE_FORT: EternityPattern = {
    name: "BG_PINK_SQUARE_FORT",
    binaryInt: 21,
    bucasLetter: "V",
    svg: {
        name: "V",
        bg_color: "#ed3da5",
        bg_stroke: "black",
        path: "m-128,-96 l 32,32 l -8,8 l 32,32 l 8,-8 l 32,32 l -32,32 l -8,-8 l -32,32 l 8,8 l -32,32",
        path_color: "#fdf102",
        path_stroke: "#edc524",
        direction: Direction.Left,
    },
}

export const PATTERN_BG_BLUE_CROSS: EternityPattern = {
    name: "BG_BLUE_CROSS",
    binaryInt: 22,
    bucasLetter: "W",
    svg: {
        name: "W",
        bg_color: "#145c8c",
        bg_stroke: "black",
        path: "m-128,-32 v -32 a64,64 30 0,1 0,128 v -40 l 24, 24 l 24,-24 l -24,-24 l 24,-24 l -24,-24 l -24,24",
        path_color: "#ec359e",
        path_stroke: "#a95397",
        direction: Direction.Left,
    },
}

export const ETERNITY_PATTERNS = [
    PATTERN_GREY,
    PATTERN_GREY_2,
    PATTERN_BG_ORANGE_CONCAVE_FORT,
    PATTERN_BG_BLUE_FLOWER,
    PATTERN_BG_PINK_HOLLOW_CONCAVE_FORT,
    PATTERN_BG_GREEN_HOLLOW_SQUARE,
    PATTERN_BG_RED_ROUND_FORT,
    PATTERN_BG_PINK_ROUND_CROSS,
    PATTERN_BG_PURPLE_POINTY_CROSS,
    PATTERN_BG_YELLOW_STAR,
    PATTERN_BG_PURPLE_CROSS,
    PATTERN_BG_GREEN_ROUND_CROSS,
    PATTERN_BG_RED_CROSS,
    PATTERN_BG_GREEN_POINTY_CROSS,
    PATTERN_BG_RED_STAR,
    PATTERN_BG_BLUE_SQUARE_FORT,
    PATTERN_BG_YELLOW_SQUARE,
    PATTERN_BG_BLUE_POINTY_CROSS,
    PATTERN_BG_YELLOW_SQUARE_FORT,
    PATTERN_BG_ORANGE_STAR,
    PATTERN_BG_BLUE_ROUND_CROSS,
    PATTERN_BG_BLUE_SQUARE,
    PATTERN_BG_PINK_SQUARE_FORT,
    PATTERN_BG_BLUE_CROSS,
]

export const ETERNITY_II_OFFICIAL_BOARD: Board = {
    label: "Eternity II Official",
    pieces: boardRearrangedWithHints(convertBucasBoardToRotatedPieces(ETERNITY_II_PIECES), ETERNITY_II_HINTS),
    nbColors: 22,
    hints: ETERNITY_II_HINTS,
}
