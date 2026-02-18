#ifndef XOR_H
#define XOR_H

#include <stdbool.h>
#include <stddef.h>

#include "redismodule.h"
#include "tools/hashes.h"


typedef enum {
    FP4 = 4,
    FP8 = 8,
    FP16 = 16,
    FP32 = 32
} FingerprintSize;


typedef struct {
    void *fingerprints;
    uint32_t segment_size;
    uint32_t seed;
    FingerprintSize fp_size;
    uint32_t reallocations;
} XorFilter;

XorFilter *xor_build(const uint64_t *hashes, size_t count, FingerprintSize fp_size);

bool xor_check(const XorFilter *filter, const void *item, int len);

void xor_free(void *inp);

void *xor_load(RedisModuleIO *rdb, int encver);

void xor_save(RedisModuleIO *rdb, void *value);

size_t xor_mem_usage(const void *value);
#endif
