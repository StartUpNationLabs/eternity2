//
// Created by appad on 10/02/2024.
//

#include "piece.h"

#include "../format/format.h"
#include "common/logger.h"

// Piece utility functions are now in common/piece_utils.cpp
// This file only contains v1-specific functions

auto piece_to_string(Piece piece) -> std::vector<std::string>
{
    std::bitset<64> bits(piece);

    // print ascii art of the piece to the console with 4 corners
    // --------
    // |            piece[0]              |
    // |  piece[3]              piece[1]  |
    // |            piece[2]              |
    // --------

    const std::string s  = bits.to_string();
    const std::string s0 = s.substr(0, 16);
    const std::string s1 = s.substr(16, 16);
    const std::string s2 = s.substr(32, 16);
    const std::string s3 = s.substr(48, 16);
    return {eternity2::format("-----------------------------------------------------"),
            eternity2::format("|                 {}                  |", s0),
            eternity2::format("|  {}               {}  |", s3, s1),
            eternity2::format("|                 {}                  |", s2),
            eternity2::format("-----------------------------------------------------")};
}

void log_piece(Piece piece, const std::string &description)
{
#ifndef DISABLE_LOGGING
    eternity2_logger::info(description);
    for (auto const &line: piece_to_string(piece)) {
        eternity2_logger::info(line);
    }
#endif
}

// get_piece_part is now in common/piece_utils.cpp
