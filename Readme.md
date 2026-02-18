# XOR Filter Redis Module

A Redis module implementing  **XOR Filter** probabilistic data structure in C.

## What is an XOR Filter?

An XOR Filter is a probabilistic data structure for testing whether an element belongs to a set.

It provides two possible results:

* **Definitely not present** — the element is guaranteed not to be in the set.
* **Possibly present** — the element may be in the set.

## Building

### Build with CMake

```bash
mkdir -p build
cd build
cmake ..
make
```

The resulting module will be:

```text
build/xor_filter.so
```

## Running Redis with the module

Start Redis and load the module:

```bash
redis-server --loadmodule ./build/xor_filter.so
```

## Redis Commands

### `XOR.BUILD`

Build an XOR Filter from a Redis set.

Example:

```text
SADD myset key1 key2 key3 key4 ...
XOR.BUILD myfilter myset
```

### `XOR.EXISTS`

Check whether an element is potentially contained in the filter.

```text
XOR.EXISTS myfilter key1
```

Possible result:

```text
1
```

means that the element **may be present**.

```text
0
```

means that the element is **definitely not present**.

> Note: `1` does not guarantee that the element exists because XOR Filters are probabilistic data structures and can produce false positives.

## Fingerprint Size

The fingerprint size determines the amount of information stored for each filter position.

Smaller fingerprints reduce memory consumption but increase the probability of false positives.

The implementation supports multiple fingerprint sizes, allowing the memory/accuracy trade-off to be evaluated experimentally.


## False Positive Probability

For an XOR Filter with an approximately uniform `f`-bit fingerprint, the theoretical false-positive probability is approximately:

```text
FPP ≈ 2⁻ᶠ
```

| Fingerprint |   Approx. FPP |
| ----------: | ------------: |
|       4 bit |         6.25% |
|       8 bit |       0.3906% |
|      16 bit |     0.001526% |
|      32 bit | ~2.33 × 10⁻¹⁰ |


## Benchmarks

The `src/reports/` directory contains script `build_filter.py`  used to evaluate the implementation and generate experimental results.
After that it is possible to run scripts in `src/reports/plots_generators`

