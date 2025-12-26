//
// Common utility functions for safe string conversions and error handling
//

#ifndef ETERNITY2_UTILS_H
#define ETERNITY2_UTILS_H

#include <string>
#include <stdexcept>
#include <cstdlib>
#include <cerrno>
#include <limits>
#include <cctype>

namespace eternity2_utils {

/**
 * @brief Exception thrown when string conversion fails
 */
class ConversionError : public std::runtime_error {
public:
    explicit ConversionError(const std::string& message) : std::runtime_error(message) {}
};

/**
 * @brief Safely convert string to integer
 * @param str String to convert
 * @param base Numeric base (default: 10)
 * @return Converted integer value
 * @throws ConversionError if conversion fails
 */
inline int safe_stoi(const std::string& str, int base = 10) {
    if (str.empty()) {
        throw ConversionError("Cannot convert empty string to integer");
    }
    
    try {
        size_t pos = 0;
        int result = std::stoi(str, &pos, base);
        
        // Check if entire string was consumed
        if (pos != str.length()) {
            // Check for trailing whitespace
            for (size_t i = pos; i < str.length(); ++i) {
                if (!std::isspace(static_cast<unsigned char>(str[i]))) {
                    throw ConversionError("Invalid characters in integer string: " + str);
                }
            }
        }
        
        return result;
    } catch (const std::invalid_argument& e) {
        throw ConversionError("Invalid integer format: " + str);
    } catch (const std::out_of_range& e) {
        throw ConversionError("Integer value out of range: " + str);
    }
}

/**
 * @brief Safely convert string to unsigned long
 * @param str String to convert
 * @param base Numeric base (default: 10)
 * @return Converted unsigned long value
 * @throws ConversionError if conversion fails
 */
inline unsigned long safe_stoul(const std::string& str, int base = 10) {
    if (str.empty()) {
        throw ConversionError("Cannot convert empty string to unsigned long");
    }
    
    try {
        size_t pos = 0;
        unsigned long result = std::stoul(str, &pos, base);
        
        // Check if entire string was consumed
        if (pos != str.length()) {
            // Check for trailing whitespace
            for (size_t i = pos; i < str.length(); ++i) {
                if (!std::isspace(static_cast<unsigned char>(str[i]))) {
                    throw ConversionError("Invalid characters in unsigned long string: " + str);
                }
            }
        }
        
        return result;
    } catch (const std::invalid_argument& e) {
        throw ConversionError("Invalid unsigned long format: " + str);
    } catch (const std::out_of_range& e) {
        throw ConversionError("Unsigned long value out of range: " + str);
    }
}

/**
 * @brief Safely convert string to long using strtol
 * @param str String to convert
 * @param base Numeric base (default: 10)
 * @return Converted long value
 * @throws ConversionError if conversion fails
 */
inline long safe_strtol(const std::string& str, int base = 10) {
    if (str.empty()) {
        throw ConversionError("Cannot convert empty string to long");
    }
    
    char* endptr = nullptr;
    errno = 0;
    long result = std::strtol(str.c_str(), &endptr, base);
    
    // Check for conversion errors
    if (endptr == str.c_str()) {
        throw ConversionError("No conversion performed for string: " + str);
    }
    
    if (errno == ERANGE || result == std::numeric_limits<long>::max() || result == std::numeric_limits<long>::min()) {
        if (errno == ERANGE) {
            throw ConversionError("Long value out of range: " + str);
        }
    }
    
    // Check if entire string was consumed (allowing trailing whitespace)
    while (*endptr != '\0') {
        if (!std::isspace(static_cast<unsigned char>(*endptr))) {
            throw ConversionError("Invalid characters in long string: " + str);
        }
        ++endptr;
    }
    
    return result;
}

/**
 * @brief Safely convert string to PiecePart using strtol with base 2
 * @param str Binary string to convert
 * @return Converted PiecePart value
 * @throws ConversionError if conversion fails
 */
template<typename PiecePart>
inline PiecePart safe_strtol_binary(const std::string& str) {
    if (str.empty()) {
        throw ConversionError("Cannot convert empty string to PiecePart");
    }
    
    char* endptr = nullptr;
    errno = 0;
    long result = std::strtol(str.c_str(), &endptr, 2);
    
    // Check for conversion errors
    if (endptr == str.c_str()) {
        throw ConversionError("No conversion performed for binary string: " + str);
    }
    
    if (errno == ERANGE) {
        throw ConversionError("Binary value out of range: " + str);
    }
    
    // Check if entire string was consumed (allowing trailing whitespace)
    while (*endptr != '\0') {
        if (!std::isspace(static_cast<unsigned char>(*endptr))) {
            throw ConversionError("Invalid characters in binary string: " + str);
        }
        ++endptr;
    }
    
    // Check if result fits in PiecePart type
    if (result < static_cast<long>(std::numeric_limits<PiecePart>::min()) ||
        result > static_cast<long>(std::numeric_limits<PiecePart>::max())) {
        throw ConversionError("Binary value out of range for PiecePart: " + str);
    }
    
    return static_cast<PiecePart>(result);
}

} // namespace eternity2_utils

#endif // ETERNITY2_UTILS_H

