//
// Created by appad on 10/02/2024.
//

#include "piece_search.h"

#include "../format/format.h"

auto match_piece_mask(const std::vector<Query> &query,
                      const std::vector<PieceWAvailability> &piecesWAvailability) -> std::vector<RotatedPiece>
{
    std::vector<RotatedPiece> results;
    for (size_t piece_index = 0; piece_index < piecesWAvailability.size(); piece_index++)
    {
        const PieceWAvailability piece_w_availability = piecesWAvailability[piece_index];
        if (!piece_w_availability.available)
        {
            continue;
        }
        const Piece piece = piece_w_availability.piece;
        for (int i = 0; i < 4; i++)
        {
            Piece rotated_piece = rotate_piece_right(piece, i);
            bool keep           = true;
            for (auto const &q : query)
            {
                const auto match = match_piece_mask_internal(q.piece, q.mask, rotated_piece);
                if (q.type == QueryType::POSITIVE && !match)
                {
                    keep = false;
                }
                if (q.type == QueryType::NEGATIVE && match)
                {
                    keep = false;
                }
            }
            if (keep)
            {
                results.push_back({piece, i, static_cast<int>(piece_index)});
            }
        }
    }
    return results;
}

auto match_piece_mask_internal(Piece piece_data, Piece piece_mask, Piece rotated_piece) -> bool
{
    Piece XOR = piece_data ^ rotated_piece;
    log_piece(rotated_piece, "rotated piece");
    log_piece(XOR, "XOR");
    log_piece((XOR & piece_mask), "XOR & mask");
    return (XOR & piece_mask) == 0;
}

auto apply_rotation(RotatedPiece piece) -> Piece
{
    return rotate_piece_right(piece.piece, piece.rotation);
}

auto create_pieces_with_availability(const std::vector<Piece> &pieces) -> std::vector<PieceWAvailability>
{
    std::vector<PieceWAvailability> pieces_w_availability;
    pieces_w_availability.reserve(pieces.size());
    for (auto piece : pieces)
    {
        pieces_w_availability.push_back({piece, true});
    }
    return pieces_w_availability;
}

auto csv_piece(RotatedPiece piece) -> std::string
{
    // convert the piece to a csv string like this <first 16 bits>,<second 16 bits>,<third 16 bits>,<fourth 16 bits>
    Piece rpiece = apply_rotation(piece);
    std::bitset<64> bits(rpiece);
    return format("{},{},{},{},{},{}",
                  bits.to_string().substr(0, 16),
                  bits.to_string().substr(16, 16),
                  bits.to_string().substr(32, 16),
                  bits.to_string().substr(48, 16),
                  piece.index,
                  piece.rotation);
}
