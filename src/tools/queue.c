#include <stdbool.h>
#include <stdint.h>

#include "redismodule.h"

#include <tools/queue.h>

Queue *Queue_Create(const uint32_t capacity) {
    Queue *q = RedisModule_Alloc(sizeof(Queue));
    q->capacity = capacity;
    uint32_t *data = RedisModule_Calloc(capacity, sizeof(uint32_t));
    q->data = data;
    q->first = 0;
    q->last = 0;
    q->reallocations=0;
    return q;
}

void Queue_Add(Queue *q, const uint32_t object) {
    uint32_t new_last = (q->last + 1) % q->capacity;
    if (new_last == q->first) {
        q->reallocations+=1;
        const uint32_t new_cap = q->capacity * 2;
        uint32_t *new_data = RedisModule_Alloc(new_cap * sizeof(uint32_t));

        const uint32_t size = (q->last >= q->first) ? (q->last - q->first) : (q->capacity - q->first + q->last);
        for (uint32_t i = 0; i < size; i++) {
            new_data[i] = q->data[(q->first + i) % q->capacity];
        }

        RedisModule_Free(q->data);
        q->data = new_data;
        q->first = 0;
        q->last = size;
        q->capacity = new_cap;
        new_last = q->last + 1;
    }
    q->data[q->last] = object;
    q->last = new_last;
}

bool Queue_Is_Empty(const Queue *q) {
    return q->first == q->last;
}

uint32_t Queue_Get(Queue *q) {
    const uint32_t result = q->data[q->first];
    q->first = (q->first + 1) % q->capacity;
    return result;
}

void Queue_Clean(Queue *q) {
    q->first = 0;
    q->last = 0;
}

void Queue_Free(Queue *q) {
    RedisModule_Free(q->data);
    RedisModule_Free(q);
}
