#include "bucket.h"
#include "redismodule.h"

Buckets *Buckets_Create(const size_t capacity) {
    Buckets *b = RedisModule_Alloc(sizeof(Buckets));
    b->capacity = capacity;
    b->x_sum = RedisModule_Calloc(capacity, sizeof(uint32_t));
    b->counts = RedisModule_Calloc(capacity, sizeof(uint8_t));
    return b;
}

void Buckets_Free(Buckets *b) {
    if (!b) return;
    RedisModule_Free(b->x_sum);
    RedisModule_Free(b->counts);
    RedisModule_Free(b);
}
