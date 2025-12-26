//
// Bloom Filter for Probabilistic Duplicate Detection
//

#ifndef ETERNITY2_BLOOM_FILTER_H
#define ETERNITY2_BLOOM_FILTER_H

#include <vector>
#include <cstdint>
#include <string>
#include <array>
#include <cmath>

namespace eternity2 {

// Probabilistic data structure for membership testing
// Used to reduce memory overhead vs full hash table
// Trades perfect accuracy for ~90% memory reduction
class BloomFilter {
public:
    // Default: 1MB filter (8M bits) with 3 hash functions
    // Supports ~500K items with ~1% false positive rate
    explicit BloomFilter(size_t size_bits = 8 * 1024 * 1024, size_t num_hashes = 3);

    // Add a key to the filter
    void add(const std::string& key);

    // Check if key might be in the filter
    // Returns true: key MIGHT be present (or false positive)
    // Returns false: key is DEFINITELY NOT present
    bool might_contain(const std::string& key) const;

    // Clear all entries
    void clear();

    // Get number of items added (approximate)
    size_t size() const { return item_count_; }

    // Estimate false positive rate based on current load
    double estimated_false_positive_rate() const;

private:
    std::vector<uint64_t> bits_;     // Bit array (packed in 64-bit words)
    size_t size_bits_;                // Total number of bits
    size_t num_hashes_;               // Number of hash functions
    size_t item_count_;               // Approximate number of items added

    // Pre-defined hash seeds for independent hash functions
    static constexpr std::array<uint64_t, 8> HASH_SEEDS = {
        0x9e3779b97f4a7c16ULL,  // Golden ratio
        0xbf58476d1ce4e5b9ULL,
        0x94d049bb133111ebULL,
        0x7fb5d329728ea185ULL,
        0x6c8e944b2d3a7b4fULL,
        0x5ad4ecb945c69a8dULL,
        0x4e2f5c3d7b8a9e1fULL,
        0x3d1e8b2c6a7f4d5eULL
    };

    // Compute hash function indices for a key
    std::vector<size_t> compute_hashes(const std::string& key) const;

    // FNV-1a hash with custom seed
    uint64_t hash_fnv1a(const std::string& key, uint64_t seed) const;
};

} // namespace eternity2

#endif // ETERNITY2_BLOOM_FILTER_H
