//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_SEARCH_H
#define ETERNITY2_PIECE_SEARCH_H

#include <vector>
#include "../piece/piece.h"

struct RotatedPiece {
    PIECE piece;
    int rotation;
};
enum class QueryType {
    POSITIVE,
    NEGATIVE
};
struct Query {
    PIECE piece;
    PIECE mask;
    QueryType type;
};

bool match_piece_mask_internal(PIECE piece_data, PIECE piece_mask, PIECE rotated_piece) {
    PIECE XOR = piece_data ^ rotated_piece;
    log_piece(rotated_piece, "rotated piece");
    log_piece(XOR, "XOR");
    if ((XOR & piece_mask) == 0) {
        log_piece((XOR & piece_mask), "XOR & mask");
        return true;
    }
    return false;
}

std::vector<RotatedPiece> match_piece_mask(const std::vector<Query> query, const std::vector<PIECE> &pieces) {
    std::vector<RotatedPiece> results;
    for (auto piece: pieces) {
        for (int i = 0; i < 4; i++) {
            PIECE rotated_piece = rotate_piece_right(piece, i);
            bool keep = true;
            for (auto const &q: query) {
                if (q.type == QueryType::POSITIVE && !match_piece_mask_internal(q.piece, q.mask, rotated_piece)) {
                        keep = false;
                } else {
                    if (q.type == QueryType::NEGATIVE && match_piece_mask_internal(q.piece, q.mask, rotated_piece)) {
                        keep = false;
                    }
                }
            }
            if (keep) {
                results.push_back({piece, i});
            }

        }
    }
    return results;
}

#endif //ETERNITY2_PIECE_SEARCH_H
