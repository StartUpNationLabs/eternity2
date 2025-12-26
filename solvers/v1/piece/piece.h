//
// Created by appad on 10/02/2024.
// v1-specific piece utilities (debugging/formatting functions)
// Core piece types and functions are in common/types.h and common/piece_utils.h
//

#ifndef ETERNITY2_PIECE_H
#define ETERNITY2_PIECE_H

#include "common/types.h"
#include "common/piece_utils.h"
#include <bitset>
#include <iostream>
#include <vector>

// Re-export common types and constants for convenience
using eternity2_common::Piece;
using eternity2_common::PiecePart;
using eternity2_common::TRUE;
using eternity2_common::UP_MASK;
using eternity2_common::RIGHT_MASK;
using eternity2_common::DOWN_MASK;
using eternity2_common::LEFT_MASK;
using eternity2_common::WALL;
using eternity2_common::EMPTY;
using eternity2_common::FULLWALL;

// Re-export common functions for convenience
using eternity2_common::get_piece_part;
using eternity2_common::make_piece;
using eternity2_common::rotate_piece_right;
using eternity2_common::rotate_piece_left;

// v1-specific debugging/formatting functions
auto piece_to_string(Piece piece) -> std::vector<std::string>;

void log_piece(Piece piece, const std::string &description);

#endif //ETERNITY2_PIECE_H
