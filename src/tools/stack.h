#ifndef XOR_FILTER_MODULE_STACK_H
#define XOR_FILTER_MODULE_STACK_H
#include <stddef.h>

#include "pair.h"

typedef struct {
    Pair *data;
    size_t head;
    size_t capacity;
} Stack;

Stack *Stack_Create(size_t capacity);

void Stack_Push(Stack *stack, const Pair *pair);

Pair Stack_Pop(Stack *stack);

void Stack_Clean(Stack *stack);

void Stack_Free(Stack *stack);

#endif //XOR_FILTER_MODULE_STACK_H
