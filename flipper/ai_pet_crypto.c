#include "ai_pet_crypto.h"

#include <string.h>

typedef struct {
    uint32_t state[8];
    uint64_t bits;
    uint8_t block[64];
    size_t used;
} Sha256;

static const uint32_t constants[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

static uint32_t rotate_right(uint32_t value, uint8_t count) {
    return (value >> count) | (value << (32 - count));
}

static void sha256_transform(Sha256* ctx, const uint8_t block[64]) {
    uint32_t words[64];
    for(size_t i = 0; i < 16; i++) {
        words[i] = ((uint32_t)block[i * 4] << 24) | ((uint32_t)block[i * 4 + 1] << 16) |
                   ((uint32_t)block[i * 4 + 2] << 8) | block[i * 4 + 3];
    }
    for(size_t i = 16; i < 64; i++) {
        uint32_t s0 = rotate_right(words[i - 15], 7) ^ rotate_right(words[i - 15], 18) ^
                      (words[i - 15] >> 3);
        uint32_t s1 = rotate_right(words[i - 2], 17) ^ rotate_right(words[i - 2], 19) ^
                      (words[i - 2] >> 10);
        words[i] = words[i - 16] + s0 + words[i - 7] + s1;
    }
    uint32_t a = ctx->state[0], b = ctx->state[1], c = ctx->state[2], d = ctx->state[3];
    uint32_t e = ctx->state[4], f = ctx->state[5], g = ctx->state[6], h = ctx->state[7];
    for(size_t i = 0; i < 64; i++) {
        uint32_t s1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
        uint32_t choice = (e & f) ^ (~e & g);
        uint32_t temp1 = h + s1 + choice + constants[i] + words[i];
        uint32_t s0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
        uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = s0 + majority;
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }
    ctx->state[0] += a;
    ctx->state[1] += b;
    ctx->state[2] += c;
    ctx->state[3] += d;
    ctx->state[4] += e;
    ctx->state[5] += f;
    ctx->state[6] += g;
    ctx->state[7] += h;
}

static void sha256_init(Sha256* ctx) {
    static const uint32_t initial[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    memcpy(ctx->state, initial, sizeof(initial));
    ctx->bits = 0;
    ctx->used = 0;
}

static void sha256_update(Sha256* ctx, const uint8_t* data, size_t size) {
    ctx->bits += (uint64_t)size * 8;
    while(size) {
        size_t available = 64 - ctx->used;
        size_t take = size < available ? size : available;
        memcpy(ctx->block + ctx->used, data, take);
        ctx->used += take;
        data += take;
        size -= take;
        if(ctx->used == 64) {
            sha256_transform(ctx, ctx->block);
            ctx->used = 0;
        }
    }
}

static void sha256_finish(Sha256* ctx, uint8_t output[32]) {
    ctx->block[ctx->used++] = 0x80;
    if(ctx->used > 56) {
        memset(ctx->block + ctx->used, 0, 64 - ctx->used);
        sha256_transform(ctx, ctx->block);
        ctx->used = 0;
    }
    memset(ctx->block + ctx->used, 0, 56 - ctx->used);
    for(size_t i = 0; i < 8; i++) ctx->block[63 - i] = ctx->bits >> (i * 8);
    sha256_transform(ctx, ctx->block);
    for(size_t i = 0; i < 8; i++) {
        output[i * 4] = ctx->state[i] >> 24;
        output[i * 4 + 1] = ctx->state[i] >> 16;
        output[i * 4 + 2] = ctx->state[i] >> 8;
        output[i * 4 + 3] = ctx->state[i];
    }
}

void ai_pet_hmac_sha256(
    const uint8_t* key,
    size_t key_size,
    const uint8_t* data,
    size_t data_size,
    uint8_t output[32]) {
    uint8_t normalized[64] = {0};
    if(key_size > 64) {
        Sha256 hash;
        sha256_init(&hash);
        sha256_update(&hash, key, key_size);
        sha256_finish(&hash, normalized);
    } else {
        memcpy(normalized, key, key_size);
    }
    uint8_t inner_pad[64], outer_pad[64], inner_hash[32];
    for(size_t i = 0; i < 64; i++) {
        inner_pad[i] = normalized[i] ^ 0x36;
        outer_pad[i] = normalized[i] ^ 0x5c;
    }
    Sha256 hash;
    sha256_init(&hash);
    sha256_update(&hash, inner_pad, sizeof(inner_pad));
    sha256_update(&hash, data, data_size);
    sha256_finish(&hash, inner_hash);
    sha256_init(&hash);
    sha256_update(&hash, outer_pad, sizeof(outer_pad));
    sha256_update(&hash, inner_hash, sizeof(inner_hash));
    sha256_finish(&hash, output);
}
