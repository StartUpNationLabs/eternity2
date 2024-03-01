//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_H
#define ETERNITY2_PIECE_H

#include <bitset>
#include <iostream>
#include <vector>

using Piece                = unsigned long long;
using PiecePart            = unsigned short;
constexpr Piece TRUE       = 0b1111111111111111;
constexpr Piece UP_MASK    = 0b1111111111111111000000000000000000000000000000000000000000000000;
constexpr Piece RIGHT_MASK = 0b0000000000000000111111111111111100000000000000000000000000000000;
constexpr Piece DOWN_MASK  = 0b0000000000000000000000000000000011111111111111110000000000000000;
constexpr Piece LEFT_MASK  = 0b0000000000000000000000000000000000000000000000001111111111111111;
constexpr PiecePart WALL   = 0b1111111111111111;
constexpr Piece EMPTY      = 0b0000000000000000;
constexpr Piece FULLWALL   = UP_MASK | RIGHT_MASK | DOWN_MASK | LEFT_MASK;

auto get_piece_part(Piece piece, Piece mask) -> PiecePart;

auto piece_to_string(Piece piece) -> std::vector<std::string>;

auto make_piece(PiecePart top, PiecePart right, PiecePart down, PiecePart left) -> Piece;

auto rotate_piece_right(Piece piece, int n) -> Piece;

auto rotate_piece_left(Piece piece, int n) -> Piece;

void log_piece(Piece piece, const std::string &description);

#endif //ETERNITY2_PIECE_H
