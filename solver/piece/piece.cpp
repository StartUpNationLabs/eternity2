//
// Created by appad on 10/02/2024.
//

#include "piece.h"
#include "../format/format.h"

Piece make_piece(PiecePart top, PiecePart right, PiecePart down, PiecePart left) {
    // concatenate the 4 parts into left single 64-bit integer
    // look at the MASKs to understand the order of the parts
    return (Piece) left | ((Piece) down << 16) | ((Piece) right << 32) | ((Piece) top << 48);
}

Piece rotate_piece_right(Piece piece, int n) {
    // rotate the piece n times
    Piece rotated_piece = piece >> (16 * n);
    // add the bits that were shifted out to the beginning
    rotated_piece |= piece << (64 - 16 * n);
    return rotated_piece;
}

Piece rotate_piece_left(Piece piece, int n) {
    // rotate the piece n times
    Piece rotated_piece = piece << (16 * n);
    // add the bits that were shifted out to the end
    rotated_piece |= piece >> (64 - 16 * n);
    return rotated_piece;
}


std::vector<std::string> piece_to_string(Piece piece) {
    std::bitset<64> bits(piece);

    // print ascii art of the piece to the console with 4 corners
    // --------
    // |            piece[0]              |
    // |  piece[3]              piece[1]  |
    // |            piece[2]              |
    // --------

    const std::string s = bits.to_string();
    const std::string s0 = s.substr(0, 16);
    const std::string s1 = s.substr(16, 16);
    const std::string s2 = s.substr(32, 16);
    const std::string s3 = s.substr(48, 16);
    return {
            format("-----------------------------------------------------"),
            format("|                 {}                  |", s0),
            format("|  {}               {}  |", s3, s1),
            format("|                 {}                  |", s2),
            format("-----------------------------------------------------")
    };
}

void log_piece(Piece piece, const std::string &description) {
#if SPDLOG_ACTIVE_LEVEL != SPDLOG_LEVEL_OFF
//    spdlog::info(description);
//    for (auto const &line: piece_to_string(piece)) {
//        spdlog::info(line);
//    }
#endif

}

PiecePart get_piece_part(Piece piece, Piece mask) {
    // get the part of the piece
    // use the MASKs to extract the part from the piece and shift it to the right position
    return (PiecePart) ((piece & mask)
            >> (mask == UP_MASK ? 48 : mask == RIGHT_MASK ? 32 : (mask == DOWN_MASK ? 16 : 0)));
}


