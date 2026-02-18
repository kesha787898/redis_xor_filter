#ifndef XOR_FILTER_MODULE_HASHES_H
#define XOR_FILTER_MODULE_HASHES_H
#include <stddef.h>
#include <stdint.h>


typedef struct {
    uint32_t fingerprint;
    uint32_t h0;
    uint32_t h1;
    uint32_t h2;
} Hash;

typedef struct {
    uint32_t h0;
    uint32_t h1;
    uint32_t h2;
} HashNoFP;


uint64_t Hash_Build(const void *key, int len);

Hash Hash_Transform(uint64_t oldHash, size_t segment_size, size_t seed,  uint32_t fp_bits);

HashNoFP Hash_Transform_No_Fingerprint(uint64_t oldHash, size_t segment_size, size_t seed);

#endif //XOR_FILTER_MODULE_HASHES_H
