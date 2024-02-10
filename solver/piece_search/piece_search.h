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

bool match_piece_mask_internal(PIECE piece_data, PIECE piece_mask, PIECE rotated_piece);

std::vector<RotatedPiece> match_piece_mask(const std::vector<Query> &query, const std::vector<PIECE> &pieces);

PIECE apply_rotation(RotatedPiece piece);

#endif //ETERNITY2_PIECE_SEARCH_H
