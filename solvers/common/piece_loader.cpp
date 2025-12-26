//
// Created by appad on 10/02/2024.
//

#include "piece_loader.h"
#include "utils.h"

// Include board.h from v1 (Board type is defined there but used by both versions)
// Note: With solvers/ in include path, we can use "v1/board/board.h" directly
#include "v1/board/board.h"

using eternity2_common::Piece;
using eternity2_common::PiecePart;
using eternity2_common::make_piece;

#include <fstream>
#include <stdexcept>

std::pair<Board, std::vector<Piece>> load_from_csv(const std::string &filename)
{
    // function to load pieces from a csv file
    // the csv file should contain the bit strings of the pieces
    // the bit strings are converted to Piece and returned as a vector

    std::ifstream in(filename);
    if (!in.is_open())
    {
        throw std::runtime_error("File not found: " + filename);
    }
    std::string line;
    if (!std::getline(in, line))
    {
        throw std::runtime_error("CSV file is empty: " + filename);
    }

    // read the first line of the csv file to get the size of the board
    int size;
    try {
        size = eternity2_utils::safe_stoi(line);
    } catch (const eternity2_utils::ConversionError& e) {
        throw std::runtime_error("Invalid board size in CSV file: " + std::string(e.what()));
    }
    
    if (size <= 0) {
        throw std::runtime_error("Board size must be positive, got: " + std::to_string(size));
    }
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
        size_t pos = 0;
        size_t next_pos = line.find(',');
        if (next_pos == std::string::npos) {
            throw std::runtime_error("Invalid CSV format: missing comma in line " + std::to_string(i + 1));
        }
        a = line.substr(0, next_pos);
        pos = next_pos + 1;
        
        next_pos = line.find(',', pos);
        if (next_pos == std::string::npos) {
            throw std::runtime_error("Invalid CSV format: missing comma in line " + std::to_string(i + 1));
        }
        b = line.substr(pos, next_pos - pos);
        pos = next_pos + 1;
        
        next_pos = line.find(',', pos);
        if (next_pos == std::string::npos) {
            throw std::runtime_error("Invalid CSV format: missing comma in line " + std::to_string(i + 1));
        }
        c = line.substr(pos, next_pos - pos);
        pos = next_pos + 1;
        
        next_pos = line.find(',', pos);
        if (next_pos == std::string::npos) {
            throw std::runtime_error("Invalid CSV format: missing comma in line " + std::to_string(i + 1));
        }
        d = line.substr(pos, next_pos - pos);
        pos = next_pos + 1;
        
        next_pos = line.find(',', pos);
        if (next_pos == std::string::npos) {
            throw std::runtime_error("Invalid CSV format: missing comma in line " + std::to_string(i + 1));
        }
        std::string isHint_str = line.substr(pos, next_pos - pos);
        pos = next_pos + 1;
        
        next_pos = line.find(',', pos);
        if (next_pos == std::string::npos) {
            throw std::runtime_error("Invalid CSV format: missing comma in line " + std::to_string(i + 1));
        }
        std::string x_str = line.substr(pos, next_pos - pos);
        pos = next_pos + 1;
        
        std::string y_str = line.substr(pos);
        
        // Convert string values with error handling
        try {
            isHint = eternity2_utils::safe_stoi(isHint_str);
            x = eternity2_utils::safe_stoi(x_str);
            y = eternity2_utils::safe_stoi(y_str);
        } catch (const eternity2_utils::ConversionError& e) {
            throw std::runtime_error("Invalid numeric value in CSV line " + std::to_string(i + 1) + ": " + std::string(e.what()));
        }

        // read bit strings from csv and convert them to Piece
        PiecePart as, bs, cs, ds;
        try {
            as = eternity2_utils::safe_strtol_binary<PiecePart>(a);
            bs = eternity2_utils::safe_strtol_binary<PiecePart>(b);
            cs = eternity2_utils::safe_strtol_binary<PiecePart>(c);
            ds = eternity2_utils::safe_strtol_binary<PiecePart>(d);
        } catch (const eternity2_utils::ConversionError& e) {
            throw std::runtime_error("Invalid binary string in CSV line " + std::to_string(i + 1) + ": " + std::string(e.what()));
        }

        Piece piece = eternity2_common::make_piece(as, bs, cs, ds);
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
        PiecePart as, bs, cs, ds;
        try {
            as = eternity2_utils::safe_strtol_binary<PiecePart>(a);
            bs = eternity2_utils::safe_strtol_binary<PiecePart>(b);
            cs = eternity2_utils::safe_strtol_binary<PiecePart>(c);
            ds = eternity2_utils::safe_strtol_binary<PiecePart>(d);
        } catch (const eternity2_utils::ConversionError& e) {
            throw std::runtime_error("Invalid binary string in CSV: " + std::string(e.what()));
        }

        Piece piece = eternity2_common::make_piece(as, bs, cs, ds);
        pieces.push_back(piece);
        csv_string.erase(0, pos + delimiter.length());
    }
    return pieces;
}