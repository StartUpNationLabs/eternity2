//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_H
#define ETERNITY2_PIECE_H

#include <bitset>
#include <iostream>
#include <vector>


using Piece = unsigned long long;
using PiecePart = unsigned short;
const Piece TRUE = 0b1111111111111111;
const Piece UP_MASK = 0b1111111111111111000000000000000000000000000000000000000000000000;
const Piece RIGHT_MASK = 0b0000000000000000111111111111111100000000000000000000000000000000;
const Piece DOWN_MASK = 0b0000000000000000000000000000000011111111111111110000000000000000;
const Piece LEFT_MASK = 0b0000000000000000000000000000000000000000000000001111111111111111;
const PiecePart WALL = 0b1111111111111111;
const Piece EMPTY = 0b0000000000000000;
const Piece FULLWALL = UP_MASK | RIGHT_MASK | DOWN_MASK | LEFT_MASK;

PiecePart get_piece_part(Piece piece, Piece mask);

std::vector<std::string> piece_to_string(Piece piece);

Piece make_piece(PiecePart top, PiecePart right, PiecePart down, PiecePart left);

Piece rotate_piece_right(Piece piece, int n);

Piece rotate_piece_left(Piece piece, int n);

void log_piece(Piece piece, const std::string &description);


#endif //ETERNITY2_PIECE_H
