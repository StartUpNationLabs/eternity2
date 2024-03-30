//
// Created by appad on 10/02/2024.
//

#include "piece_loader.h"

#include "board/board.h"

#include <fstream>

std::pair<Board, std::vector<Piece>> load_from_csv(const std::string &filename)
{
    // function to load pieces from a csv file
    // the csv file should contain the bit strings of the pieces
    // the bit strings are converted to Piece and returned as a vector

    std::ifstream in(filename);
    if (!in.is_open())
    {
        throw std::runtime_error("File not found");
    }
    std::string line;
    std::getline(in, line);

    // read the first line of the csv file to get the size of the board
    int size                  = std::stoi(line);
    Board board               = create_board(size);
    std::vector<Piece> pieces = {};
    for (int i = 0; i < size * size; i++)
    {
        std::getline(in, line);
        if (line.empty())
        {
            continue;
        }
        std::string a;
        std::string b;
        std::string c;
        std::string d;
        int isHint = 0;
        int x      = 0;
        int y      = 0;
        // split the line by comma a,b,c,d,isHint,x,y
        a      = line.substr(0, line.find(','));
        line   = line.substr(line.find(',') + 1);
        b      = line.substr(0, line.find(','));
        line   = line.substr(line.find(',') + 1);
        c      = line.substr(0, line.find(','));
        line   = line.substr(line.find(',') + 1);
        d      = line.substr(0, line.find(','));
        line   = line.substr(line.find(',') + 1);
        isHint = std::stoi(line.substr(0, line.find(',')));
        line   = line.substr(line.find(',') + 1);
        x      = std::stoi(line.substr(0, line.find(',')));
        line   = line.substr(line.find(',') + 1);
        y      = std::stoi(line);

        // read bit strings from csv and convert them to Piece
        auto as = (PiecePart) strtol(a.c_str(), nullptr, 2);
        auto bs = (PiecePart) strtol(b.c_str(), nullptr, 2);
        auto cs = (PiecePart) strtol(c.c_str(), nullptr, 2);
        auto ds = (PiecePart) strtol(d.c_str(), nullptr, 2);

        Piece piece = make_piece(as, bs, cs, ds);
        if (isHint)
        {
            place_piece(board, {piece, 0, -i}, {x, y});
        }
        else
        {
            pieces.push_back(piece);
        }
    }
    log_board(board, "Loaded board");
    return {board, pieces};
}

std::vector<Piece> load_from_csv_string(std::string &csv_string)
{
    // function to load pieces from a csv string
    // the csv string should contain the bit strings of the pieces
    // the bit strings are converted to Piece and returned as a vector

    // iterate over the lines of the csv string
    std::vector<Piece> pieces;
    std::string delimiter = "\n";
    size_t pos            = 0;
    std::string token;

    while ((pos = csv_string.find(delimiter)) != std::string::npos)
    {
        token = csv_string.substr(0, pos);
        std::string a;
        std::string b;
        std::string c;
        std::string d;
        std::string isHint;
        std::string x;
        std::string y;
        // split the line by comma
        a      = token.substr(0, token.find(','));
        token  = token.substr(token.find(',') + 1);
        b      = token.substr(0, token.find(','));
        token  = token.substr(token.find(',') + 1);
        c      = token.substr(0, token.find(','));
        token  = token.substr(token.find(',') + 1);
        d      = token.substr(0, token.find(','));
        token  = token.substr(token.find(',') + 1);
        isHint = token.substr(0, token.find(','));
        token  = token.substr(token.find(',') + 1);
        x      = token.substr(0, token.find(','));
        token  = token.substr(token.find(',') + 1);
        y      = token;

        // read bit strings from csv and convert them to Piece
        auto as = (PiecePart) strtol(a.c_str(), nullptr, 2);
        auto bs = (PiecePart) strtol(b.c_str(), nullptr, 2);
        auto cs = (PiecePart) strtol(c.c_str(), nullptr, 2);
        auto ds = (PiecePart) strtol(d.c_str(), nullptr, 2);

        Piece piece = make_piece(as, bs, cs, ds);
        pieces.push_back(piece);
        csv_string.erase(0, pos + delimiter.length());
    }
    return pieces;
}