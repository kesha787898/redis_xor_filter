#ifndef XOR_FILTER_MODULE_QUEUE_H
#define XOR_FILTER_MODULE_QUEUE_H
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint32_t *data;
    uint32_t capacity;
    uint32_t last;
    uint32_t first;
    uint32_t reallocations;
} Queue;

Queue *Queue_Create(uint32_t capacity);


void Queue_Add(Queue *q, uint32_t object);

bool Queue_Is_Empty(const Queue *q);

uint32_t Queue_Get(Queue *q);

void Queue_Clean(Queue *q);

void Queue_Free(Queue *q);

#endif //XOR_FILTER_MODULE_QUEUE_H
