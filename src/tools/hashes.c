#include <tools/hashes.h>

#include "murmur3.h"

uint64_t mix(uint64_t h) {
    h = (h ^ (h >> 30)) * 0xbf58476d1ce4e5b9ULL; //SplitMix64
    h = (h ^ (h >> 27)) * 0x94d049bb133111ebULL;
    h = h ^ (h >> 31);
    return h;
}


uint64_t Hash_Build(const void *key, const int len) {
    uint64_t hash[2];
    MurmurHash3_x64_128(key, len, 42, hash);
    return hash[0];
}

Hash Hash_Transform(const uint64_t oldHash, const size_t segment_size, const size_t seed, const uint32_t fp_bits) {
    const uint64_t mixed_raw0 = mix(oldHash + seed + 0x9E3779B97F4A7C15ULL);
    const uint64_t mixed_raw1 = mix(oldHash + seed + 0xBF58476D1CE4E5B9ULL);

    const uint32_t h0 = (uint32_t) mixed_raw0 % segment_size;
    const uint32_t h1 = ((uint32_t) (mixed_raw0 >> 32) % segment_size) + segment_size;
    const uint32_t h2 = ((uint32_t) mixed_raw1 % segment_size) + 2 * segment_size;
    const uint32_t fp_mask = (fp_bits >= 32) ? 0xFFFFFFFFu : ((1u << fp_bits) - 1u);
    uint32_t fingerprint = (uint32_t) (mixed_raw1 >> 32) & fp_mask;
    if (fingerprint == 0) fingerprint = 1;
    Hash result;
    result.h0 = h0;
    result.h1 = h1;
    result.h2 = h2;
    result.fingerprint = fingerprint;
    return result;
}

HashNoFP Hash_Transform_No_Fingerprint(const uint64_t oldHash, const size_t segment_size, const size_t seed) {
    const uint64_t mixed_raw0 = mix(oldHash + seed + 0x9E3779B97F4A7C15ULL);
    const uint64_t mixed_raw1 = mix(oldHash + seed + 0xBF58476D1CE4E5B9ULL);

    const uint32_t h0 = (uint32_t) mixed_raw0 % segment_size;
    const uint32_t h1 = ((uint32_t) (mixed_raw0 >> 32) % segment_size) + segment_size;
    const uint32_t h2 = ((uint32_t) mixed_raw1 % segment_size) + 2 * segment_size;
    HashNoFP result;
    result.h0 = h0;
    result.h1 = h1;
    result.h2 = h2;
    return result;
}
