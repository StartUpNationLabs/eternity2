//
// Created by appad on 03/03/2024.
//

#include "hash_store_load.h"
void store_hash(std::unordered_set<BoardHash> &hashes, const std::string &filename)
{
    std::ofstream file;
    file.open(filename);
    for (const auto &hash : hashes)
    {
        file << hash << '\n';
    }
    file.close();
}
void load_hash(std::unordered_set<BoardHash> &hashes, const std::string &filename)
{
    std::ifstream file;
    file.open(filename);
    std::string line;
    while (std::getline(file, line))
    {
        hashes.insert(line);
    }
    file.close();
}
