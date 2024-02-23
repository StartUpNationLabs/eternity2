#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "board/board.h"
#include "format/format.h"
#include "solver/solver.h"


TEST_CASE("Possible pieces") {
    SECTION("Test possible pieces in 2x2 board") {
        Board board = create_board(2);
        Piece piece = make_piece(1, 2, WALL, WALL);
        log_board(board, "2x2 board with piece");
        std::vector<RotatedPiece> possible = possible_pieces(board, create_pieces_with_availability({piece}), 1, 1);
        REQUIRE(possible.size() == 1);
        REQUIRE(possible[0].piece == piece);
        REQUIRE(possible[0].rotation == 3);
        place_piece(board, possible[0], 1, 1);
        log_board(board, "2x2 board with piece placed");

    }

}


TEST_CASE("Solve Board") {
    SECTION("Solve 2x2 board") {
        Board board = create_board(2);
        std::vector<Piece> pieces = {
                make_piece(1, 1, WALL, WALL),
                make_piece(1, WALL, WALL, 1),
                make_piece(WALL, WALL, 1, 1),
                make_piece(1, 1, WALL, WALL)
        };
        //solve_board(Board &board, const std::vector<Piece> &pieces, Board &max_board, int &max_count, std::mutex &mutex)
        int max_count = 0;
        Board max_board = create_board(2);
        std::mutex mutex;
        solve_board(board, pieces, max_board, max_count, mutex);
        log_board(board, "2x2 board solved");
        for (auto const &row: board) {
            for (auto const &piece: row) {
                REQUIRE(piece.piece != 0);
            }
        }
    }

    SECTION("Solve 3x3 board") {
        Board board = create_board(3);
        std::vector<Piece> pieces = {
                make_piece(1, 1, WALL, WALL),
                make_piece(1, WALL, WALL, 1),
                make_piece(WALL, WALL, 1, 1),
                make_piece(1, 1, WALL, WALL),


                make_piece(1, 1, WALL, 1),
                make_piece(1, WALL, 1, 1),
                make_piece(1, 1, 1, WALL),
                make_piece(WALL, 1, 1, 1),

                make_piece(1, 1, 1, 1),


        };
        int max_count = 0;
        Board max_board = create_board(3);
        std::mutex mutex;
        solve_board(board, pieces, max_board, max_count, mutex);
        log_board(board, "3x3 board solved");
        for (auto const &row: board) {
            for (auto const &piece: row) {
                REQUIRE(piece.piece != 0);
            }
        }
    }

    SECTION("3x3 Complex") {
        /*
 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
 |                 1111111111111111                  ||                 1111111111111111                  ||                 1111111111111111                  |
 |  1111111111111111               0000000000000002  ||  0000000000000002               0000000000000005  ||  0000000000000005               1111111111111111  |
 |                 0000000000000001                  ||                 0000000000000001                  ||                 0000000000000001                  |
 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
 |                 0000000000000001                  ||                 0000000000000001                  ||                 0000000000000001                  |
 |  1111111111111111               0000000000000002  ||  0000000000000002               0000000000000003  ||  0000000000000003               1111111111111111  |
 |                 0000000000000003                  ||                 0000000000000001                  ||                 0000000000000001                  |
 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
 ---------------------------------------------------------------------------------------------------------------------------------------------------------------
 |                 0000000000000003                  ||                 0000000000000001                  ||                 0000000000000001                  |
 |  1111111111111111               0000000000000004  ||  0000000000000004               0000000000000001  ||  0000000000000001               1111111111111111  |
 |                 1111111111111111                  ||                 1111111111111111                  ||                 1111111111111111                  |
 ---------------------------------------------------------------------------------------------------------------------------------------------------------------

         */
        Board board = create_board(3);
        std::vector<Piece> pieces = {
                rotate_piece_right(make_piece(WALL, 2, 1, WALL), 1),
                rotate_piece_right(make_piece(WALL, 5, 1, 2), 2),
                rotate_piece_right(make_piece(WALL, WALL, 1, 5), 3),

                rotate_piece_right(make_piece(1, 2, 3, WALL), 1),
                rotate_piece_right(make_piece(1, 3, 1, 2), 0),
                rotate_piece_right(make_piece(1, WALL, 1, 3), 1),

                rotate_piece_right(make_piece(3, 4, WALL, WALL), 2),
                rotate_piece_right(make_piece(1, 1, WALL, 4), 1),
                rotate_piece_right(make_piece(1, WALL, WALL, 1), 1),


        };
        auto start = std::chrono::high_resolution_clock::now();
        int max_count = 0;
        Board max_board = create_board(3);
        std::mutex mutex;
        solve_board(board, pieces, max_board, max_count, mutex);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;
        log_board(board, format("3x3 board solved in {} seconds", elapsed.count()));
        for (auto const &row: board) {
            for (auto const &piece: row) {
                REQUIRE(piece.piece != 0);
            }
        }
    }

}

TEST_CASE("Solve & Export Board") {
    SECTION("Solve 2x2 board") {
        Board board = create_board(2);
        std::vector<Piece> pieces = {
                make_piece(1, 1, WALL, WALL),
                make_piece(1, WALL, WALL, 1),
                make_piece(WALL, WALL, 1, 1),
                make_piece(1, 1, WALL, WALL)
        };

        int max_count = 0;
        Board max_board = create_board(2);
        std::mutex mutex;
        solve_board(board, pieces, max_board, max_count, mutex);
        log_board(board, "2x2 board solved");
        for (auto const &row: board) {
            for (auto const &piece: row) {
                REQUIRE(piece.piece != 0);
            }
        }

        export_board(max_board);
    }
}
