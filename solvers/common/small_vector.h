//
// SmallVector - Inline storage optimization for small vectors
// Avoids heap allocations for common small cases
//

#ifndef ETERNITY2_COMMON_SMALL_VECTOR_H
#define ETERNITY2_COMMON_SMALL_VECTOR_H

#include <array>
#include <vector>
#include <cstddef>
#include <type_traits>
#include <initializer_list>
#include <algorithm>

namespace eternity2_common {

/**
 * @brief SmallVector with inline storage for N elements
 *
 * Uses inline storage for up to N elements, falls back to heap
 * allocation for larger sizes. Optimized for the common case of
 * small collections (e.g., removed pieces in trail entries).
 *
 * @tparam T Element type
 * @tparam N Inline storage capacity (default: 8)
 */
template<typename T, size_t N = 8>
class SmallVector {
public:
    using value_type = T;
    using size_type = size_t;
    using iterator = T*;
    using const_iterator = const T*;

    SmallVector() noexcept : size_(0), using_heap_(false) {}

    SmallVector(const SmallVector& other) : size_(0), using_heap_(false) {
        reserve(other.size_);
        for (const auto& elem : other) {
            push_back(elem);
        }
    }

    SmallVector(SmallVector&& other) noexcept : size_(0), using_heap_(false) {
        if (other.using_heap_) {
            // Steal heap storage
            heap_ = std::move(other.heap_);
            using_heap_ = true;
            size_ = other.size_;
            other.size_ = 0;
            other.using_heap_ = false;
        } else {
            // Move inline elements
            for (size_t i = 0; i < other.size_; ++i) {
                new (&inline_storage_[i]) T(std::move(other.inline_storage_[i]));
                other.inline_storage_[i].~T();
            }
            size_ = other.size_;
            other.size_ = 0;
        }
    }

    SmallVector& operator=(const SmallVector& other) {
        if (this != &other) {
            clear();
            reserve(other.size_);
            for (const auto& elem : other) {
                push_back(elem);
            }
        }
        return *this;
    }

    SmallVector& operator=(SmallVector&& other) noexcept {
        if (this != &other) {
            clear();
            if (other.using_heap_) {
                heap_ = std::move(other.heap_);
                using_heap_ = true;
                size_ = other.size_;
                other.size_ = 0;
                other.using_heap_ = false;
            } else {
                for (size_t i = 0; i < other.size_; ++i) {
                    new (&inline_storage_[i]) T(std::move(other.inline_storage_[i]));
                    other.inline_storage_[i].~T();
                }
                size_ = other.size_;
                other.size_ = 0;
            }
        }
        return *this;
    }

    ~SmallVector() {
        clear();
    }

    void push_back(const T& value) {
        if (!using_heap_ && size_ < N) {
            // Use inline storage
            new (&inline_storage_[size_]) T(value);
            ++size_;
        } else {
            // Switch to or use heap storage
            if (!using_heap_) {
                migrate_to_heap();
            }
            heap_.push_back(value);
            ++size_;
        }
    }

    void push_back(T&& value) {
        if (!using_heap_ && size_ < N) {
            new (&inline_storage_[size_]) T(std::move(value));
            ++size_;
        } else {
            if (!using_heap_) {
                migrate_to_heap();
            }
            heap_.push_back(std::move(value));
            ++size_;
        }
    }

    template<typename... Args>
    void emplace_back(Args&&... args) {
        if (!using_heap_ && size_ < N) {
            new (&inline_storage_[size_]) T(std::forward<Args>(args)...);
            ++size_;
        } else {
            if (!using_heap_) {
                migrate_to_heap();
            }
            heap_.emplace_back(std::forward<Args>(args)...);
            ++size_;
        }
    }

    void reserve(size_t new_cap) {
        if (new_cap > N && !using_heap_) {
            migrate_to_heap();
            heap_.reserve(new_cap);
        } else if (using_heap_) {
            heap_.reserve(new_cap);
        }
    }

    void clear() {
        if (using_heap_) {
            heap_.clear();
        } else {
            for (size_t i = 0; i < size_; ++i) {
                inline_storage_[i].~T();
            }
        }
        size_ = 0;
    }

    [[nodiscard]] bool empty() const noexcept { return size_ == 0; }
    [[nodiscard]] size_t size() const noexcept { return size_; }

    T& operator[](size_t idx) {
        return using_heap_ ? heap_[idx] : inline_storage_[idx];
    }

    const T& operator[](size_t idx) const {
        return using_heap_ ? heap_[idx] : inline_storage_[idx];
    }

    iterator begin() noexcept {
        return using_heap_ ? heap_.data() : inline_storage_.data();
    }

    iterator end() noexcept {
        return begin() + size_;
    }

    const_iterator begin() const noexcept {
        return using_heap_ ? heap_.data() : inline_storage_.data();
    }

    const_iterator end() const noexcept {
        return using_heap_ ? (heap_.data() + size_) : (inline_storage_.data() + size_);
    }

    const_iterator cbegin() const noexcept { return begin(); }
    const_iterator cend() const noexcept { return end(); }

    // Insert from iterators (for compatibility with std::vector::insert)
    template<typename InputIt>
    void insert(iterator pos, InputIt first, InputIt last) {
        // For simplicity, just append at end (trail restoration doesn't care about order)
        while (first != last) {
            push_back(*first);
            ++first;
        }
    }

private:
    void migrate_to_heap() {
        heap_.reserve(size_ + N);  // Pre-allocate for growth
        for (size_t i = 0; i < size_; ++i) {
            heap_.push_back(std::move(inline_storage_[i]));
            inline_storage_[i].~T();
        }
        using_heap_ = true;
    }

    // Inline storage (uninitialized)
    alignas(T) std::array<T, N> inline_storage_;

    // Heap storage (used when inline capacity exceeded)
    std::vector<T> heap_;

    size_t size_;
    bool using_heap_;
};

} // namespace eternity2_common

#endif // ETERNITY2_COMMON_SMALL_VECTOR_H
