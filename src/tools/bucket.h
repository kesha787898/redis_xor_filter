#ifndef XOR_FILTER_MODULE_BUCKET_H
#define XOR_FILTER_MODULE_BUCKET_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint32_t *x_sum;
    uint8_t *counts;
    size_t capacity;
} Buckets;

Buckets *Buckets_Create(size_t capacity);

void Buckets_Free(Buckets *b);

static void Bucket_Push(const Buckets *b, const uint32_t idx, const uint32_t key_index) {
    b->x_sum[idx] ^= key_index;
    if (b->counts[idx] < 255) {
        //P(x>256)~0, since x~Poisson(1/1.23)
        b->counts[idx]++;
    }
}

static void Bucket_Remove(const Buckets *b, const uint32_t idx, const uint32_t key_index) {
    b->x_sum[idx] ^= key_index;
    if (b->counts[idx] > 0) {
        b->counts[idx]--;
    }
}

static uint32_t Bucket_GetSingleValue(const Buckets *b, const uint32_t idx) {
    return b->x_sum[idx];
}

static uint8_t Bucket_GetCount(const Buckets *b, const uint32_t idx) {
    return b->counts[idx];
}

#endif // XOR_FILTER_MODULE_BUCKET_H
