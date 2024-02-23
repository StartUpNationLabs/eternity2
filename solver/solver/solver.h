#include <vector>
#include "board/board.h"
struct SharedData {
    Board &max_board;
    int &max_count;
    std::mutex &mutex;
    std::unordered_set<BoardHash> &hashes;
};


SharedData create_shared_data();

std::vector<RotatedPiece> possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, Index index);

void solve_board(Board &board, const std::vector<Piece> &pieces, SharedData &shared_data);