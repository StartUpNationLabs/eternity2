//
// Created by appad on 10/02/2024.
//

#include "piece_search.h"

std::vector<RotatedPiece>
match_piece_mask(const std::vector<Query> &query, const std::vector<PieceWAvailability> &piecesWAvailability) {
    std::vector<RotatedPiece> results;
    for (size_t pieceIndex = 0; pieceIndex < piecesWAvailability.size(); pieceIndex++) {
        const PieceWAvailability pieceWAvailability = piecesWAvailability[pieceIndex];
        if (!pieceWAvailability.available) {
            continue;
        }
        const PIECE piece = pieceWAvailability.piece;
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
                results.push_back({piece, i, pieceIndex});
            }

        }
    }
    return results;
}

bool match_piece_mask_internal(PIECE piece_data, PIECE piece_mask, PIECE rotated_piece) {
    PIECE XOR = piece_data ^ rotated_piece;
    log_piece(rotated_piece, "rotated piece");
    log_piece(XOR, "XOR");
    log_piece((XOR & piece_mask), "XOR & mask");
    if ((XOR & piece_mask) == 0) {

        return true;
    }
    return false;
}


PIECE apply_rotation(RotatedPiece piece) {
    return rotate_piece_right(piece.piece, piece.rotation);
}

std::vector<PieceWAvailability> create_pieces_with_availability(const std::vector<PIECE> &pieces) {
    std::vector<PieceWAvailability> piecesWAvailability;
    piecesWAvailability.reserve(pieces.size());
    for (auto piece: pieces) {
        piecesWAvailability.push_back({piece, true});
    }
    return piecesWAvailability;
}
