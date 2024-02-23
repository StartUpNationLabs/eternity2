// function to create an empty board with the given size and fill it with empty pieces
// a board is a 2D array of pieces

// function to create an empty board with the given size and fill it with empty pieces
// a board is a 2D array of pieces


#ifndef ETERNITY2_BOARD_H
#define ETERNITY2_BOARD_H

#include <vector>
#include <mutex>
#include <unordered_set>
#include "../piece_search/piece_search.h"
//#include "../piece/piece.h"

using Board = std::vector<std::vector<RotatedPiece>>;
using BoardHash = unsigned long long;
using Index = std::pair<size_t, size_t>;
struct SharedData {
    Board *max_board;
    int *max_count;
    std::mutex *mutex;
    std::unordered_set<BoardHash> *hashes;
};
Board create_board(int size);
std::vector<std::string> board_to_string(const Board &board);
void place_piece(Board &board, const RotatedPiece &piece, size_t x, size_t y);
void remove_piece(Board &board, size_t x, size_t y);
Index getNext(const Board &board, Index index);
RotatedPiece* getPiece(const Board &board, Index index);
void log_board(const Board &board, const std::string &description);
void export_board(const Board &board);
std::string export_board_to_csv_string(const Board &board);
#endif //ETERNITY2_BOARD_H