//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_LOADER_H
#define ETERNITY2_PIECE_LOADER_H

#include <vector>
#include "../piece/piece.h"

std::vector<Piece> load_from_csv(const std::string& filename);
std::vector<Piece> load_from_csv_string(std::string &csv_string);

#endif //ETERNITY2_PIECE_LOADER_H
