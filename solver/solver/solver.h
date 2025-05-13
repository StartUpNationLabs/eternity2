#include "board/board.h"

#include <atomic>
#include <functional>
#include <vector>

struct SharedData {
    Board &max_board;
    uint64_t max_count;
    std::mutex &mutex;
    std::unordered_set<BoardHash> &hashes;
    uint64_t board_count{0};
    uint64_t hash_hit_count{0};
    bool stop{false};
    // callback that is called when you enter the recursive function, takes in a Board
    std::function<void(const Board &)> on_board_update = [](const Board &board) {};
    unsigned int hash_length_threshold = 7;
    unsigned long redis_hash_count = 0;
    uint64_t pieces_placed{0};
    uint64_t milliseconds_since_start{1};
};

auto possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, Index index)
-> std::vector<RotatedPiece>;

void solve_board(Board &board, const std::vector<Piece> &pieces, SharedData &shared_data);

// take a global and an array of local data and merge them
void merge_shared_data(SharedData &global_data, std::vector<SharedData> &local_data);