//
// Created by appad on 03/03/2024.
//

#ifndef ETERNITY2_HASH_STORE_LOAD_H
#define ETERNITY2_HASH_STORE_LOAD_H

#include "board/board.h"

#include <fstream>
#include <string>
#include <unordered_set>
#include <vector>

void store_hash(std::unordered_set<BoardHash> &hashes, const std::string &filename);

void load_hash(std::unordered_set<BoardHash> &hashes, const std::string &filename);
#endif //ETERNITY2_HASH_STORE_LOAD_H
