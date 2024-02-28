import random
import urllib.parse
from enum import Enum

BUCAS_E2_PIECES = ["aabd", "aabe", "aacd", "aadc", "abgb", "abhc", "abjb", "abjf", "abmd", "aboe", "abpc", "abte",
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
                   "rtus", "suvu", "swuw", "twvw"]


class BucasBoardEdgeValue(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"


class BucasBoardEdge:
    def __init__(self, top, right, bottom, left):
        self.top: BucasBoardEdgeValue = BucasBoardEdgeValue(top)
        self.right: BucasBoardEdgeValue = BucasBoardEdgeValue(right)
        self.bottom: BucasBoardEdgeValue = BucasBoardEdgeValue(bottom)
        self.left: BucasBoardEdgeValue = BucasBoardEdgeValue(left)


class BucasBoardPieceId:
    def __init__(self, piece_id: int):
        self.id: int = piece_id


class BoardTypes(Enum):
    NONE = "a"
    CORNER = "b"
    BORDER = "c"
    CENTER = "d"
    FIXED = "e"


class BucasUrlParams(Enum):
    BOARD_W = "board_w"
    BOARD_H = "board_h"
    BOARD_EDGES = "board_edges"
    BOARD_PIECES = "board_pieces"
    SHOW_CONFLICTS = "show_conflicts"
    SHOW_PIECENUMBER = "show_piecenumber"
    SHOW_PIECETYPE = "show_piecetype"
    SHOW_COORDINATES = "show_coordinates"
    BOARD_TYPES = "board_types"


class BucasBoardPiece:
    def __init__(self, piece_id: BucasBoardPieceId, edges: BucasBoardEdge):
        self.id: BucasBoardPieceId = piece_id
        self.edges: BucasBoardEdge = edges


def parse_edges(edges_string):
    edges = []
    for i in range(0, len(edges_string), 4):
        edge = BucasBoardEdge(edges_string[i], edges_string[i + 1], edges_string[i + 2], edges_string[i + 3])
        edges.append(edge)
    return edges


def parse_pieces(pieces_string):
    pieces = []
    for i in range(0, len(pieces_string), 3):
        piece_id: str = pieces_string[i:i + 3]
        piece_id_int: int = int(piece_id)
        piece = BucasBoardPieceId(piece_id_int)

        pieces.append(piece)
    return pieces


class Bucas:
    """
    Interface with the website Bucas available at https://e2.bucas.name/
    """
    BASE_URL = "https://e2.bucas.name"
    # BEST SOLUTION
    PUZZLE_LINK = f"{BASE_URL}/#"

    def __init__(self, edges_string=None, pieces_string=None):
        if edges_string is not None and pieces_string is not None:
            edges = parse_edges(edges_string)
            pieces = parse_pieces(pieces_string)
            self.pieces = [BucasBoardPiece(piece_id=pieces[i], edges=edges[i]) for i in range(len(pieces))]

        else:
            self.generate_random_puzzle(16)

    def generate_random_puzzle(self, size=16):
        number_of_pieces = size * size
        edges_string = ''.join(random.choice(list(BucasBoardEdgeValue)).value for _ in range(number_of_pieces * 4))
        pieces_string = ''.join(str(random.randint(0, number_of_pieces - 1)).zfill(3) for _ in range(number_of_pieces))
        self.__init__(edges_string, pieces_string)

    def generate_url(self, show_conflicts=False, show_piecenumber=False, show_piecetype=False, show_coordinates=False,
                     board_types: list[BoardTypes] | None = None, puzzle_name: str | None = None):
        board_w = board_h = int(len(self.pieces) ** 0.5)
        board_edges = ''.join(
            piece.edges.top.value + piece.edges.right.value + piece.edges.bottom.value + piece.edges.left.value for
            piece in self.pieces)
        board_pieces = ''.join(str(piece.id.id).zfill(3) for piece in self.pieces)
        params = {
            BucasUrlParams.BOARD_W.value: board_w,
            BucasUrlParams.BOARD_H.value: board_h,
            BucasUrlParams.BOARD_EDGES.value: board_edges,
            BucasUrlParams.BOARD_PIECES.value: board_pieces,
            BucasUrlParams.SHOW_CONFLICTS.value: int(show_conflicts),
            BucasUrlParams.SHOW_PIECENUMBER.value: int(show_piecenumber),
            BucasUrlParams.SHOW_PIECETYPE.value: int(show_piecetype),
            BucasUrlParams.SHOW_COORDINATES.value: int(show_coordinates),
            BucasUrlParams.BOARD_TYPES.value: board_types,
        }
        url = self.PUZZLE_LINK + puzzle_name + urllib.parse.urlencode(params)
        return url


if __name__ == "__main__":
    bucas = Bucas()
    sorted_pieces = sorted(bucas.pieces, key=lambda piece_lambda: piece_lambda.id.id)
    print(len(sorted_pieces))
    for piece in sorted_pieces:
        print("Piece id:", piece.id.id, "Edges:", piece.edges.top.value, piece.edges.right.value,
              piece.edges.bottom.value, piece.edges.left.value)

    bucas.generate_random_puzzle()
    url = bucas.generate_url(
        show_conflicts=True,
        show_piecenumber=True,
        show_piecetype=True,
        show_coordinates=True,
        puzzle_name="nice-puzzle"
    )
    print(url)
