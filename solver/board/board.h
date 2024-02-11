// function to create an empty board with the given size and fill it with empty pieces
// a board is a 2D array of pieces

// function to create an empty board with the given size and fill it with empty pieces
// a board is a 2D array of pieces


#ifndef ETERNITY2_BOARD_H
#define ETERNITY2_BOARD_H

#include <vector>
#include <mutex>
#include "../piece_search/piece_search.h"
//#include "../piece/piece.h"

using Board = std::vector<std::vector<RotatedPiece>>;

Board create_board(int size);
std::vector<std::string> board_to_string(const Board &board);
void place_piece(Board &board, const RotatedPiece &piece, size_t x, size_t y);
void remove_piece(Board &board, size_t x, size_t y);
std::vector<RotatedPiece> possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, size_t x, size_t y);
void log_board(const Board &board, const std::string &description);
void solve_board(Board &board, const std::vector<PIECE> &pieces, Board &max_board, int &max_count, std::mutex &mutex);
void export_board(const Board &board);
#endif //ETERNITY2_BOARD_H