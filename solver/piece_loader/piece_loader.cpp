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
        // read bit strings from csv and convert them to PIECE
        auto as = (PIECE_PART) strtol(a, nullptr, 2);
        auto bs = (PIECE_PART) strtol(b, nullptr, 2);
        auto cs = (PIECE_PART) strtol(c, nullptr, 2);
        auto ds = (PIECE_PART) strtol(d, nullptr, 2);

        PIECE piece = make_piece(as, bs, cs, ds);
        pieces.push_back(piece);
    }
    for (auto piece: pieces) {
        log_piece(piece, "Loaded piece");
    }
    return pieces;
}
