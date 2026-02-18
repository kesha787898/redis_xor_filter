#include "xor.h"

#include <math.h>
#include <string.h>
#include <time.h>

#include "redismodule.h"
#include "tools/bucket.h"
#include "tools/pair.h"
#include "tools/queue.h"
#include "tools/stack.h"

static uint32_t fp_get(const XorFilter *filter, const uint32_t idx) {
    switch (filter->fp_size) {
        case FP4: {
            const uint8_t byte = ((const uint8_t *) filter->fingerprints)[idx >> 1];
            return (idx & 1) ? (byte >> 4) : (byte & 0x0F);
        }
        case FP8: return ((const uint8_t *) filter->fingerprints)[idx];
        case FP16: return ((const uint16_t *) filter->fingerprints)[idx];
        case FP32: return ((const uint32_t *) filter->fingerprints)[idx];
        default: return 0;
    }
}

static void fp_set(const XorFilter *filter, const uint32_t idx, const uint32_t value) {
    switch (filter->fp_size) {
        case FP4: {
            uint8_t *ptr = &((uint8_t *) filter->fingerprints)[idx >> 1];
            const uint8_t val4 = (uint8_t) (value & 0x0F);
            if (idx & 1) {
                *ptr = (*ptr & 0x0F) | (val4 << 4); // high bits
            } else {
                *ptr = (*ptr & 0xF0) | val4; // low bits
            }
            break;
        }
        case FP8: ((uint8_t *) filter->fingerprints)[idx] = (uint8_t) value;
            break;
        case FP16: ((uint16_t *) filter->fingerprints)[idx] = (uint16_t) value;
            break;
        case FP32: ((uint32_t *) filter->fingerprints)[idx] = value;
            break;
    }
}

static size_t fp_bytes(const FingerprintSize fp_size, const size_t elem_count) {
    if (fp_size == FP4) {
        return (elem_count + 1) / 2;
    }
    return elem_count * (size_t) (fp_size / 8);
}

bool map(const uint64_t *hashes, const size_t count, const uint32_t segment_size, const uint32_t seed, Stack *stack,
         Queue *Q, const Buckets *B) {
    Queue_Clean(Q);
    Stack_Clean(stack);
    if (!hashes) return false;
    memset(B->x_sum, 0, B->capacity * sizeof(uint32_t));
    memset(B->counts, 0, B->capacity * sizeof(uint8_t));
    for (size_t i = 0; i < count; i++) {
        const HashNoFP h = Hash_Transform_No_Fingerprint(hashes[i], segment_size, seed);
        Bucket_Push(B, h.h0, (uint32_t) i);
        Bucket_Push(B, h.h1, (uint32_t) i);
        Bucket_Push(B, h.h2, (uint32_t) i);
    }

    for (size_t idx = 0; idx < segment_size * 3; idx++) {
        if (B->counts[idx] == 1) {
            Queue_Add(Q, (uint32_t) idx);
        }
    }

    while (!Queue_Is_Empty(Q)) {
        const uint32_t idx = Queue_Get(Q);
        if (B->counts[idx] == 1) {
            const uint32_t x = Bucket_GetSingleValue(B, idx);
            const uint8_t slot = (uint8_t) (idx / segment_size);
            Stack_Push(stack, &(Pair){.x = x, .slot = slot});
            const HashNoFP h = Hash_Transform_No_Fingerprint(hashes[x], segment_size, seed);

            Bucket_Remove(B, h.h0, x);
            if (B->counts[h.h0] == 1) {
                Queue_Add(Q, h.h0);
            }
            Bucket_Remove(B, h.h1, x);
            if (B->counts[h.h1] == 1) {
                Queue_Add(Q, h.h1);
            }
            Bucket_Remove(B, h.h2, x);
            if (B->counts[h.h2] == 1) {
                Queue_Add(Q, h.h2);
            }
        }
    }
    return stack->head == count;
}

void assign(Stack *stack,
            const XorFilter *filter,
            const uint32_t segment_size,
            const uint32_t seed,
            const uint64_t *hashes) {
    const uint32_t fp_bits = filter->fp_size;
    while (stack->head > 0) {
        const Pair pair = Stack_Pop(stack);
        const Hash h = Hash_Transform(hashes[pair.x], segment_size, seed, fp_bits);
        const uint32_t i = (pair.slot == 0) ? h.h0 : (pair.slot == 1) ? h.h1 : h.h2;
        fp_set(filter, i, 0);
        const uint32_t value = h.fingerprint ^ fp_get(filter, h.h0) ^ fp_get(filter, h.h1) ^ fp_get(filter, h.h2);
        fp_set(filter, i, value);
    }
}

XorFilter *XorFilter_Create() {
    XorFilter *filter = RedisModule_Calloc(1, sizeof(XorFilter));
    return filter;
};

XorFilter *xor_build(const uint64_t *hashes, const size_t count, const FingerprintSize fp_size) {
    const uint32_t segment_size = ceil(1.23 * (double) count / 3.0);
    const uint32_t total_buckets = segment_size * 3;
    XorFilter *filter = XorFilter_Create();
    Stack *stack = Stack_Create(count);
    Buckets *B = Buckets_Create(total_buckets);

    Queue *Q = Queue_Create((uint32_t) (total_buckets * 0.4));
    void *fingerprints = NULL;
    if (!filter || !stack || !B || !Q) {
        goto cleanup;
    }
    uint64_t seed = 0;
    while (true) {
        if (map(hashes, count, segment_size, seed, stack, Q, B)) {
            break;
        }
        seed++;
        if (seed > 100) {
            goto cleanup;
        }
    }
    Buckets_Free(B);
    B = NULL;
    const uint32_t reallocations = Q->reallocations;
    Queue_Free(Q);
    Q = NULL;
    const size_t bytes_needed = fp_bytes(fp_size, total_buckets);
    fingerprints = RedisModule_Calloc(
        bytes_needed,
        1
    );
    if (!fingerprints) {
        goto cleanup;
    }
    filter->fp_size = fp_size;
    filter->segment_size = segment_size;
    filter->seed = seed;
    filter->fingerprints = fingerprints;
    filter->reallocations = reallocations;
    assign(stack, filter, segment_size, seed, hashes);

    Stack_Free(stack);

    return filter;

cleanup:
    if (filter) RedisModule_Free(filter);
    if (stack) Stack_Free(stack);
    if (B) Buckets_Free(B);
    if (Q) Queue_Free(Q);
    return NULL;
}


bool xor_check(const XorFilter *filter, const void *item, const int len) {
    const Hash h = Hash_Transform(Hash_Build(item, len), filter->segment_size, filter->seed, filter->fp_size);

    const uint32_t actual = fp_get(filter, h.h0) ^ fp_get(filter, h.h1) ^ fp_get(filter, h.h2);
    return actual == h.fingerprint;
}

void xor_free(void *inp) {
    XorFilter *filter = inp;
    RedisModule_Free(filter->fingerprints);
    RedisModule_Free(filter);
}

void *xor_load(RedisModuleIO *rdb, const int encver) {
    if (encver > 0) return NULL;
    XorFilter *filter = RedisModule_Alloc(sizeof(XorFilter));
    filter->seed = RedisModule_LoadUnsigned(rdb);
    filter->segment_size = RedisModule_LoadUnsigned(rdb);
    filter->fp_size = RedisModule_LoadUnsigned(rdb);
    filter->reallocations = RedisModule_LoadUnsigned(rdb);
    size_t loaded_len;
    const char *raw_data = RedisModule_LoadStringBuffer(rdb, &loaded_len);
    filter->fingerprints = RedisModule_Alloc(loaded_len);
    memcpy(filter->fingerprints, raw_data, loaded_len);
    return filter;
}

void xor_save(RedisModuleIO *rdb, void *value) {
    const XorFilter *filter = (XorFilter *) value;
    RedisModule_SaveUnsigned(rdb, filter->seed);
    RedisModule_SaveUnsigned(rdb, filter->segment_size);
    RedisModule_SaveUnsigned(rdb, filter->fp_size);
    RedisModule_SaveUnsigned(rdb, filter->reallocations);

    const size_t data_size = fp_bytes(filter->fp_size, (size_t) filter->segment_size * 3);
    RedisModule_SaveStringBuffer(rdb, (const char *) filter->fingerprints, data_size);
}

size_t xor_mem_usage(const void *value) {
    const XorFilter *filter = value;
    if (!filter) return 0;

    const size_t fingerprints_size = fp_bytes(filter->fp_size, (size_t) filter->segment_size * 3);
    return sizeof(XorFilter) + fingerprints_size;
}
