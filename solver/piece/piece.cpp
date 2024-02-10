//
// Created by appad on 10/02/2024.
//

#include "piece.h"
#include "spdlog/spdlog.h"

PIECE get_mask(int n) {
    switch (n) {
        case 0:
            return UP_MASK;
        case 1:
            return RIGHT_MASK;
        case 2:
            return DOWN_MASK;
        case 3:
            return LEFT_MASK;
        default:
            return 0;
    }
}

PIECE make_piece(PIECE_PART top, PIECE_PART right, PIECE_PART down, PIECE_PART left) {
    // concatenate the 4 parts into left single 64-bit integer
    // look at the MASKs to understand the order of the parts
    return (PIECE) left | ((PIECE) down << 16) | ((PIECE) right << 32) | ((PIECE) top << 48);
}

PIECE rotate_piece_right(PIECE piece, int n) {
    // rotate the piece n times
    PIECE rotated_piece = piece >> (16 * n);
    // add the bits that were shifted out to the beginning
    rotated_piece |= piece << (64 - 16 * n);
    return rotated_piece;
}

PIECE rotate_piece_left(PIECE piece, int n) {
    // rotate the piece n times
    PIECE rotated_piece = piece << (16 * n);
    // add the bits that were shifted out to the end
    rotated_piece |= piece >> (64 - 16 * n);
    return rotated_piece;
}


void log_piece(PIECE piece, std::string description) {
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
    spdlog::info("Log piece: {}", description);
    spdlog::info("-----------------------------------------------------");
    spdlog::info("|                 {}                  |", s0);
    spdlog::info("|  {}               {}  |", s3, s1);
    spdlog::info("|                 {}                  |", s2);
    spdlog::info("-----------------------------------------------------");
}

