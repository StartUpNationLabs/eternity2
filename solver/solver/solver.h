#include <vector>
#include "board/board.h"

std::vector<RotatedPiece> possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, Index index);

void solve_board(Board &board, const std::vector<Piece> &pieces, Board &max_board, int &max_count, std::mutex &mutex);