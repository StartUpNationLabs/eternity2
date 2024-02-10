//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_SEARCH_H
#define ETERNITY2_PIECE_SEARCH_H

#include <vector>
#include "../piece/piece.h"

struct PieceResult {
    PIECE piece;
    int rotation;
};
std::vector<PieceResult> match_piece_mask(PIECE piece_data, PIECE piece_mask, const std::vector<PIECE> &pieces) {
    std::vector<PieceResult> results;
    for (auto piece: pieces) {
        for (int i = 0; i < 4; i++) {
            PIECE rotated_piece = rotate_piece_right(piece, i);
            PIECE XOR = piece_data ^ rotated_piece;
            log_piece(rotated_piece, "rotated piece");
            log_piece(XOR, "XOR");
            if ((XOR & piece_mask) == 0) {
                results.push_back({piece, i});
            }
        }
    }
    return results;
}

#endif //ETERNITY2_PIECE_SEARCH_H
