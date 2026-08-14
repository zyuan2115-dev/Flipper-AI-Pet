#pragma once

#include <stddef.h>
#include <stdint.h>

void ai_pet_hmac_sha256(
    const uint8_t* key,
    size_t key_size,
    const uint8_t* data,
    size_t data_size,
    uint8_t output[32]);
