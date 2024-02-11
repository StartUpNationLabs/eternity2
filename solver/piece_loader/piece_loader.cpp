//
// Created by appad on 10/02/2024.
//

#include "piece_loader.h"

std::vector<PIECE> load_from_csv(const std::string &filename) {
    io::CSVReader<4> in(filename);


    std::vector<PIECE> pieces = {};
    char *a;
    char *b;
    char *c;
    char *d;
    while (in.read_row(a, b, c, d)) {
        auto as = (PIECE_PART) atoi(a);
        auto bs = (PIECE_PART) atoi(b);
        auto cs = (PIECE_PART) atoi(c);
        auto ds = (PIECE_PART) atoi(d);
        if (as == 0) {
            as = WALL;
        }

        if (bs == 0) {
            bs = WALL;
        }

        if (cs == 0) {
            cs = WALL;
        }

        if (ds == 0) {
            ds = WALL;
        }

        PIECE piece = make_piece(as, bs, cs, ds);
        pieces.push_back(piece);
    }
    for (auto piece: pieces) {
        log_piece(piece, "Loaded piece");
    }
    return pieces;
}
