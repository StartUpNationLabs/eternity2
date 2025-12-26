//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_SEARCH_H
#define ETERNITY2_PIECE_SEARCH_H

#include <vector>
#include "common/types.h"
#include "common/piece_utils.h"

// Re-export common types
using eternity2_common::RotatedPiece;
using eternity2_common::Piece;

enum class QueryType {
    POSITIVE,
    NEGATIVE
};
struct Query {
    Piece piece;
    Piece mask;
    QueryType type;
};

struct PieceWAvailability {
    Piece piece;
    bool available;
};

bool match_piece_mask_internal(Piece piece_data, Piece piece_mask, Piece rotated_piece);

std::vector<RotatedPiece> match_piece_mask(const std::vector<Query> &query, const std::vector<PieceWAvailability> &piecesWAvability);

std::vector<PieceWAvailability> create_pieces_with_availability(const std::vector<Piece> &pieces);
Piece apply_rotation(RotatedPiece piece);
std::string csv_piece(RotatedPiece piece);

#endif //ETERNITY2_PIECE_SEARCH_H
