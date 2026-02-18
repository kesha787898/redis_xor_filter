#include "redismodule.h"
#include <stdlib.h>
#include <string.h>

#include "xor.h"
RedisModuleType *XorFilterType;

int cmp_uint64(const void *a, const void *b) {
    const uint64_t va = *(const uint64_t *) a;
    const uint64_t vb = *(const uint64_t *) b;
    return (va > vb) - (va < vb);
}

static size_t get_fingerprints_bytes(const FingerprintSize fp_size, const uint32_t count) {
    if (fp_size == FP4) {
        return (count + 1) / 2;
    }
    return (size_t) count * ((size_t) fp_size / 8);
}

int XorInfo_Command(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    if (argc != 2) return RedisModule_WrongArity(ctx);

    RedisModule_AutoMemory(ctx);

    RedisModuleKey *key = RedisModule_OpenKey(ctx, argv[1], REDISMODULE_READ);
    if (RedisModule_KeyType(key) == REDISMODULE_KEYTYPE_EMPTY) {
        return RedisModule_ReplyWithError(ctx, "ERR key does not exist");
    }

    if (RedisModule_ModuleTypeGetType(key) != XorFilterType) {
        return RedisModule_ReplyWithError(ctx, REDISMODULE_ERRORMSG_WRONGTYPE);
    }

    const XorFilter *filter = RedisModule_ModuleTypeGetValue(key);

    RedisModule_ReplyWithMap(ctx, 4); // seed, fp, segment, queue reallocatiions

    RedisModule_ReplyWithSimpleString(ctx, "seed");
    RedisModule_ReplyWithLongLong(ctx, filter->seed);

    RedisModule_ReplyWithSimpleString(ctx, "fp_size");
    RedisModule_ReplyWithLongLong(ctx, filter->fp_size);

    RedisModule_ReplyWithSimpleString(ctx, "segment_size");
    RedisModule_ReplyWithLongLong(ctx, filter->segment_size);

    RedisModule_ReplyWithSimpleString(ctx, "reallocations");
    RedisModule_ReplyWithLongLong(ctx, filter->reallocations);

    return REDISMODULE_OK;
}

int XorBuild_Command(RedisModuleCtx *ctx, RedisModuleString **argv, const int argc) {
    if (argc != 4) return RedisModule_WrongArity(ctx);
    long long fp_bits;
    if (RedisModule_StringToLongLong(argv[3], &fp_bits) != REDISMODULE_OK ||
        (fp_bits != FP4 && fp_bits != FP8 && fp_bits != FP16 && fp_bits != FP32)) {
        return RedisModule_ReplyWithError(ctx, "Fingerprint size must be 4, 8, 16 or 32");
    }
    RedisModuleKey *source_key = RedisModule_OpenKey(ctx, argv[2], REDISMODULE_READ);
    if (RedisModule_KeyType(source_key) != REDISMODULE_KEYTYPE_SET) {
        RedisModule_CloseKey(source_key);
        return RedisModule_ReplyWithError(ctx, "key is not SET");
    }

    const size_t num_items = RedisModule_ValueLength(source_key);
    if (num_items == 0) {
        RedisModule_CloseKey(source_key);
        return RedisModule_ReplyWithError(ctx, "SET is empty");
    }

    uint64_t *hashes = RedisModule_Alloc(sizeof(uint64_t) * num_items);
    unsigned long long cursor = 0;
    size_t loaded = 0;

    while (loaded < num_items) {
        RedisModuleCallReply *reply = RedisModule_Call(
            ctx, "SSCAN", "slcc", argv[2], (long long) cursor, "COUNT", "10000"
        );
        if (!reply || RedisModule_CallReplyType(reply) != REDISMODULE_REPLY_ARRAY) {
            if (reply) RedisModule_FreeCallReply(reply);
            RedisModule_Free(hashes);
            RedisModule_CloseKey(source_key);
            return RedisModule_ReplyWithError(ctx, "Failed to scan SET members");
        }
        RedisModuleCallReply *cursor_reply = RedisModule_CallReplyArrayElement(reply, 0);
        size_t clen;
        const char *cursor_str = RedisModule_CallReplyStringPtr(cursor_reply, &clen);
        cursor = strtoull(cursor_str, NULL, 10);

        RedisModuleCallReply *items_reply = RedisModule_CallReplyArrayElement(reply, 1);
        const size_t batch_len = RedisModule_CallReplyLength(items_reply);

        for (size_t i = 0; i < batch_len && loaded < num_items; i++) {
            RedisModuleCallReply *item = RedisModule_CallReplyArrayElement(items_reply, i);
            size_t len;
            const char *str_ptr = RedisModule_CallReplyStringPtr(item, &len);

            hashes[loaded++] = Hash_Build(str_ptr, (int) len);
        }

        RedisModule_FreeCallReply(reply);

        if (cursor == 0) break;
    }
    qsort(hashes, loaded, sizeof(uint64_t), cmp_uint64);
    size_t unique_count = 0;
    for (size_t i = 0; i < loaded; i++) {
        if (i == 0 || hashes[i] != hashes[i - 1]) {
            hashes[unique_count++] = hashes[i];
        }
    }
    XorFilter *filter = xor_build(hashes, unique_count, fp_bits);
    RedisModule_Free(hashes);
    if (filter == NULL) {
        RedisModule_CloseKey(source_key);

        return RedisModule_ReplyWithError(
            ctx,
            "Failed to build xor filter"
        );
    }

    RedisModuleKey *dest_key = RedisModule_OpenKey(
        ctx,
        argv[1],
        REDISMODULE_WRITE
    );
    if (dest_key == NULL) {
        xor_free(filter);
        RedisModule_CloseKey(source_key);

        return RedisModule_ReplyWithError(ctx, "Cannot open destination key");
    }
    RedisModule_ModuleTypeSetValue(
        dest_key,
        XorFilterType,
        filter
    );

    RedisModule_CloseKey(source_key);
    RedisModule_CloseKey(dest_key);

    return RedisModule_ReplyWithLongLong(ctx, (long long) num_items);
}

int XorExists_Command(RedisModuleCtx *ctx, RedisModuleString **argv, const int argc) {
    if (argc != 3) return RedisModule_WrongArity(ctx);

    RedisModuleKey *key = RedisModule_OpenKey(ctx, argv[1], REDISMODULE_READ);

    if (key == NULL ||
        RedisModule_ModuleTypeGetType(key) != XorFilterType) {
        if (key)
            RedisModule_CloseKey(key);

        return RedisModule_ReplyWithLongLong(ctx, 0);
    }
    const XorFilter *filter =
            RedisModule_ModuleTypeGetValue(key);

    size_t item_len;
    const char *item_ptr = RedisModule_StringPtrLen(argv[2], &item_len);

    const bool found = xor_check(
        filter,
        item_ptr,
        (int) item_len
    );
    RedisModule_CloseKey(key);
    return RedisModule_ReplyWithLongLong(ctx, found ? 1 : 0);
}

int XorScanDump_Command(
    RedisModuleCtx *ctx,
    RedisModuleString **argv,
    const int argc
) {
    //segment seed fp, realloc, fingerprints
    if (argc != 3)
        return RedisModule_WrongArity(ctx);

    long long cursor;

    if (RedisModule_StringToLongLong(argv[2], &cursor) != REDISMODULE_OK ||
        cursor != 0) {
        return RedisModule_ReplyWithError(ctx, "Invalid cursor");
    }

    RedisModuleKey *key =
            RedisModule_OpenKey(ctx, argv[1], REDISMODULE_READ);

    if (RedisModule_KeyType(key) == REDISMODULE_KEYTYPE_EMPTY) {
        RedisModule_CloseKey(key);
        return RedisModule_ReplyWithError(ctx, "ERR key does not exist");
    }

    if (RedisModule_ModuleTypeGetType(key) != XorFilterType) {
        RedisModule_CloseKey(key);
        return RedisModule_ReplyWithError(
            ctx,
            REDISMODULE_ERRORMSG_WRONGTYPE
        );
    }

    const XorFilter *filter =
            RedisModule_ModuleTypeGetValue(key);


    const uint32_t count = 3 * filter->segment_size;

    const size_t fingerprints_size = get_fingerprints_bytes(filter->fp_size, count);

    const size_t total_size =
            sizeof(filter->segment_size) +
            sizeof(filter->seed) +
            sizeof(filter->fp_size) +
            sizeof(filter->reallocations) +
            fingerprints_size;

    char *buffer = RedisModule_Alloc(total_size);

    size_t offset = 0;

    memcpy(
        buffer + offset,
        &filter->segment_size,
        sizeof(filter->segment_size)
    );
    offset += sizeof(filter->segment_size);

    memcpy(
        buffer + offset,
        &filter->seed,
        sizeof(filter->seed)
    );
    offset += sizeof(filter->seed);

    memcpy(
        buffer + offset,
        &filter->fp_size,
        sizeof(filter->fp_size)
    );
    offset += sizeof(filter->fp_size);

    memcpy(
        buffer + offset,
        &filter->reallocations,
        sizeof(filter->reallocations)
    );
    offset += sizeof(filter->reallocations);

    memcpy(
        buffer + offset,
        filter->fingerprints,
        fingerprints_size
    );

    RedisModule_CloseKey(key);

    RedisModule_ReplyWithArray(ctx, 2);

    RedisModule_ReplyWithLongLong(ctx, 0);

    RedisModule_ReplyWithStringBuffer(
        ctx,
        buffer,
        total_size
    );

    RedisModule_Free(buffer);

    return REDISMODULE_OK;
}

int XorLoadChunk_Command(
    RedisModuleCtx *ctx,
    RedisModuleString **argv,
    const int argc
) {
    if (argc != 4)
        return RedisModule_WrongArity(ctx);

    long long cursor;

    if (RedisModule_StringToLongLong(argv[2], &cursor) != REDISMODULE_OK ||
        cursor != 0) {
        return RedisModule_ReplyWithError(ctx, "Invalid cursor");
    }

    size_t data_len;
    const char *data =
            RedisModule_StringPtrLen(argv[3], &data_len);

    const size_t metadata_size =
            sizeof(uint32_t) +
            sizeof(uint32_t) +
            sizeof(FingerprintSize) +
            sizeof(uint32_t);

    if (data_len < metadata_size) {
        return RedisModule_ReplyWithError(
            ctx,
            "Invalid XOR filter data"
        );
    }

    size_t offset = 0;
    uint32_t segment_size;
    uint32_t seed;
    FingerprintSize fp_size;
    uint32_t reallocations;
    memcpy(&segment_size, data + offset, sizeof(segment_size));
    offset += sizeof(segment_size);

    memcpy(&seed, data + offset, sizeof(seed));
    offset += sizeof(seed);

    memcpy(&fp_size, data + offset, sizeof(fp_size));
    offset += sizeof(fp_size);
    memcpy(&reallocations, data + offset, sizeof(reallocations));
    offset += sizeof(reallocations);

    if (fp_size != FP4 && fp_size != FP8 && fp_size != FP16 && fp_size != FP32) {
        return RedisModule_ReplyWithError(ctx, "Invalid fingerprint size");
    }

    const uint32_t count = 3 * segment_size;
    const size_t fp_bytes_needed = get_fingerprints_bytes(fp_size, count);

    const size_t expected_size = metadata_size + fp_bytes_needed;

    if (data_len != expected_size) {
        return RedisModule_ReplyWithError(ctx, "Invalid XOR filter size");
    }

    XorFilter *filter = RedisModule_Alloc(sizeof(XorFilter));
    filter->segment_size = segment_size;
    filter->seed = seed;
    filter->fp_size = fp_size;
    filter->reallocations = reallocations;
    filter->fingerprints = RedisModule_Alloc(fp_bytes_needed);
    memcpy(filter->fingerprints, data + offset, fp_bytes_needed);

    RedisModuleKey *key = RedisModule_OpenKey(ctx, argv[1], REDISMODULE_WRITE);
    RedisModule_ModuleTypeSetValue(key, XorFilterType, filter);
    RedisModule_CloseKey(key);

    return RedisModule_ReplyWithSimpleString(ctx, "OK");
}

int RedisModule_OnLoad(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    if (RedisModule_Init(ctx, "xorfilter", 1, REDISMODULE_APIVER_1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;

    RedisModuleTypeMethods methods = {
        .version = 1,
        .rdb_load = xor_load,
        .rdb_save = xor_save,
        .free = xor_free,
        .mem_usage = xor_mem_usage,

    };

    XorFilterType = RedisModule_CreateDataType(
        ctx,
        "xorfilt00",
        1,
        &methods
    );

    if (XorFilterType == NULL)
        return REDISMODULE_ERR;
    if (RedisModule_CreateCommand(ctx, "xor.build", XorBuild_Command, "write", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;
    if (RedisModule_CreateCommand(ctx, "xor.info", XorInfo_Command, "readonly", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;

    if (RedisModule_CreateCommand(ctx, "xor.exists", XorExists_Command, "readonly", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;

    if (RedisModule_CreateCommand(ctx, "xor.scandump", XorScanDump_Command, "readonly", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;
    if (RedisModule_CreateCommand(ctx, "xor.loadchunk", XorLoadChunk_Command, "write", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;


    return REDISMODULE_OK;
}
