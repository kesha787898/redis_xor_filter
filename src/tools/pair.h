#ifndef XOR_FILTER_MODULE_PAIR_H
#define XOR_FILTER_MODULE_PAIR_H
#include <stdint.h>

typedef struct {
    uint32_t x : 30;
    uint32_t slot : 2;
} Pair;
#endif //XOR_FILTER_MODULE_PAIR_H
