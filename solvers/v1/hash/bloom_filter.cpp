//
// Bloom Filter Implementation
//

#include "bloom_filter.h"
#include <algorithm>

namespace eternity2 {

BloomFilter::BloomFilter(size_t size_bits, size_t num_hashes)
    : size_bits_(size_bits)
    , num_hashes_(std::min(num_hashes, HASH_SEEDS.size()))
    , item_count_(0)
{
    // Allocate bit array (packed in 64-bit words)
    bits_.resize((size_bits + 63) / 64, 0);
}

void BloomFilter::add(const std::string& key) {
    auto indices = compute_hashes(key);

    for (size_t idx : indices) {
        size_t word_idx = idx / 64;
        size_t bit_idx = idx % 64;
        bits_[word_idx] |= (1ULL << bit_idx);
    }

    item_count_++;
}

bool BloomFilter::might_contain(const std::string& key) const {
    auto indices = compute_hashes(key);

    for (size_t idx : indices) {
        size_t word_idx = idx / 64;
        size_t bit_idx = idx % 64;

        // If any bit is NOT set, key is definitely not present
        if ((bits_[word_idx] & (1ULL << bit_idx)) == 0) {
            return false;
        }
    }

    // All bits are set - key MIGHT be present (or false positive)
    return true;
}

void BloomFilter::clear() {
    std::fill(bits_.begin(), bits_.end(), 0);
    item_count_ = 0;
}

double BloomFilter::estimated_false_positive_rate() const {
    if (item_count_ == 0) return 0.0;

    // False positive rate formula:
    // p = (1 - e^(-k*n/m))^k
    // where:
    //   k = number of hash functions
    //   n = number of items
    //   m = number of bits

    double k = static_cast<double>(num_hashes_);
    double n = static_cast<double>(item_count_);
    double m = static_cast<double>(size_bits_);

    double exponent = -k * n / m;
    double base = 1.0 - std::exp(exponent);
    return std::pow(base, k);
}

std::vector<size_t> BloomFilter::compute_hashes(const std::string& key) const {
    std::vector<size_t> indices;
    indices.reserve(num_hashes_);

    for (size_t i = 0; i < num_hashes_; ++i) {
        uint64_t hash = hash_fnv1a(key, HASH_SEEDS[i]);
        size_t idx = hash % size_bits_;
        indices.push_back(idx);
    }

    return indices;
}

uint64_t BloomFilter::hash_fnv1a(const std::string& key, uint64_t seed) const {
    // FNV-1a 64-bit hash algorithm with custom seed
    // https://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function

    constexpr uint64_t FNV_OFFSET_BASIS = 14695981039346656037ULL;
    constexpr uint64_t FNV_PRIME = 1099511628211ULL;

    uint64_t hash = FNV_OFFSET_BASIS ^ seed;

    for (unsigned char c : key) {
        hash ^= static_cast<uint64_t>(c);
        hash *= FNV_PRIME;
    }

    return hash;
}

} // namespace eternity2
