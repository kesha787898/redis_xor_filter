#include "tools//stack.h"
#include "pair.h"
#include "redismodule.h"

Stack *Stack_Create(const size_t capacity) {
    Stack *stack = RedisModule_Alloc(sizeof(Stack));
    stack->capacity = capacity;
    Pair *data = RedisModule_Calloc(capacity, sizeof(Pair));
    stack->data = data;
    stack->head = 0;
    return stack;
}

void Stack_Push(Stack *stack, const Pair *pair) {
    stack->data[stack->head] = *pair;
    stack->head++;
}

Pair Stack_Pop(Stack *stack) {
    stack->head--;
    return stack->data[stack->head];
}

void Stack_Clean(Stack *stack) {
    stack->head = 0;
};

void Stack_Free(Stack *stack) {
    RedisModule_Free(stack->data);
    RedisModule_Free(stack);
};
