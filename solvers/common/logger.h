//
// Simple logging utility for Eternity II solvers
//

#ifndef ETERNITY2_LOGGER_H
#define ETERNITY2_LOGGER_H

#include <iostream>
#include <sstream>
#include <string>
#include <mutex>

namespace eternity2_logger {

enum class LogLevel {
    INFO,
    WARN,
    ERROR
};

// Simple string formatting helper (basic implementation)
template<typename... Args>
std::string format_string(const std::string& fmt, Args... args) {
    std::ostringstream oss;
    size_t pos = 0;
    size_t arg_count = 0;
    
    auto format_arg = [&](auto&& arg) {
        size_t placeholder = fmt.find("{}", pos);
        if (placeholder != std::string::npos) {
            oss << fmt.substr(pos, placeholder - pos);
            oss << arg;
            pos = placeholder + 2;
            arg_count++;
        }
    };
    
    (format_arg(args), ...);
    oss << fmt.substr(pos);
    return oss.str();
}

// Logging functions
inline void log(LogLevel level, const std::string& message) {
#ifndef DISABLE_LOGGING
    static std::mutex log_mutex;
    std::lock_guard<std::mutex> lock(log_mutex);
    
    switch (level) {
        case LogLevel::INFO:
            std::cout << "[INFO] " << message << std::endl;
            break;
        case LogLevel::WARN:
            std::cerr << "[WARN] " << message << std::endl;
            break;
        case LogLevel::ERROR:
            std::cerr << "[ERROR] " << message << std::endl;
            break;
    }
#endif
}

template<typename... Args>
void info(const std::string& fmt, Args... args) {
    log(LogLevel::INFO, format_string(fmt, args...));
}

template<typename... Args>
void warn(const std::string& fmt, Args... args) {
    log(LogLevel::WARN, format_string(fmt, args...));
}

template<typename... Args>
void error(const std::string& fmt, Args... args) {
    log(LogLevel::ERROR, format_string(fmt, args...));
}

// Overloads for simple string messages (no formatting)
inline void info(const std::string& message) {
    log(LogLevel::INFO, message);
}

inline void warn(const std::string& message) {
    log(LogLevel::WARN, message);
}

inline void error(const std::string& message) {
    log(LogLevel::ERROR, message);
}

} // namespace eternity2_logger

// Convenience macros for compatibility
#define ETERNITY2_INFO(...) eternity2_logger::info(__VA_ARGS__)
#define ETERNITY2_WARN(...) eternity2_logger::warn(__VA_ARGS__)
#define ETERNITY2_ERROR(...) eternity2_logger::error(__VA_ARGS__)

#endif // ETERNITY2_LOGGER_H

