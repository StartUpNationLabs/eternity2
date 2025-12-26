//
// Created by appad on 10/02/2024.
//

#ifndef ETERNITY2_PIECE_LOADER_H
#define ETERNITY2_PIECE_LOADER_H

#include <vector>
#include <string>
#include "types.h"
#include "piece_utils.h"

// Forward declarations - board types are in v1 but used by both
struct Board;

// Use types from eternity2_common namespace
using eternity2_common::Piece;

/**
 * @brief Load board and pieces from a CSV file
 * 
 * The CSV file format should be:
 * - First line: board size (integer)
 * - Subsequent lines: piece data in format: top,bottom,left,right,isHint,x,y
 *   where top/bottom/left/right are binary strings representing piece parts
 * 
 * @param filename Path to the CSV file
 * @return std::pair containing the Board and vector of Pieces
 * @throws std::runtime_error if file cannot be opened, is empty, or contains invalid data
 */
std::pair<Board, std::vector<Piece>> load_from_csv(const std::string& filename);

/**
 * @brief Load pieces from a CSV string
 * 
 * Parses a CSV string containing piece data. Each line should contain:
 * top,bottom,left,right,isHint,x,y
 * 
 * @param csv_string CSV-formatted string containing piece data
 * @return Vector of Pieces parsed from the string
 * @throws std::runtime_error if the string format is invalid
 */
std::vector<Piece> load_from_csv_string(std::string &csv_string);

#endif //ETERNITY2_PIECE_LOADER_H
