//
// Created by appad on 10/02/2024.
//

#include "piece_search.h"
#include "../format/format.h"

std::vector<RotatedPiece>
match_piece_mask(const std::vector<Query> &query, const std::vector<PieceWAvailability> &piecesWAvailability) {
    std::vector<RotatedPiece> results;
    for (size_t pieceIndex = 0; pieceIndex < piecesWAvailability.size(); pieceIndex++) {
        const PieceWAvailability pieceWAvailability = piecesWAvailability[pieceIndex];
        if (!pieceWAvailability.available) {
            continue;
        }
        const Piece piece = pieceWAvailability.piece;
        for (int i = 0; i < 4; i++) {
            Piece rotated_piece = rotate_piece_right(piece, i);
            bool keep = true;
            for (auto const &q: query) {
                const auto match =  match_piece_mask_internal(q.piece, q.mask, rotated_piece);
                if (q.type == QueryType::POSITIVE && !match) {
                    keep = false;
                }
                if (q.type == QueryType::NEGATIVE && match) {
                    keep = false;
                }

            }
            if (keep) {
                results.push_back({piece, i, pieceIndex});
            }

        }
    }
    return results;
}

bool match_piece_mask_internal(Piece piece_data, Piece piece_mask, Piece rotated_piece) {
    Piece XOR = piece_data ^ rotated_piece;
    log_piece(rotated_piece, "rotated piece");
    log_piece(XOR, "XOR");
    log_piece((XOR & piece_mask), "XOR & mask");
    if ((XOR & piece_mask) == 0) {

        return true;
    }
    return false;
}


Piece apply_rotation(RotatedPiece piece) {
    return rotate_piece_right(piece.piece, piece.rotation);
}

std::vector<PieceWAvailability> create_pieces_with_availability(const std::vector<Piece> &pieces) {
    std::vector<PieceWAvailability> piecesWAvailability;
    piecesWAvailability.reserve(pieces.size());
    for (auto piece: pieces) {
        piecesWAvailability.push_back({piece, true});
    }
    return piecesWAvailability;
}

std::string csv_piece(RotatedPiece piece) {
    // convert the piece to a csv string like this <first 16 bits>,<second 16 bits>,<third 16 bits>,<fourth 16 bits>
    Piece rpiece = apply_rotation(piece);
    std::bitset<64> bits(rpiece);
    return format("{},{},{},{},{},{}", bits.to_string().substr(0, 16), bits.to_string().substr(16, 16),
                       bits.to_string().substr(32, 16), bits.to_string().substr(48, 16), piece.index, piece.rotation);
}
