#pragma once

#include <furi_ble/profile_interface.h>
#include <stddef.h>
#include <stdint.h>

typedef void (*BleStateProfileRxCallback)(const uint8_t* data, size_t size, void* context);

extern const FuriHalBleProfileTemplate* const ble_profile_ai_state;

void ble_profile_ai_state_set_rx_callback(
    FuriHalBleProfileBase* profile,
    BleStateProfileRxCallback callback,
    void* context);

bool ble_profile_ai_state_notify(
    FuriHalBleProfileBase* profile,
    const uint8_t* data,
    size_t size);
