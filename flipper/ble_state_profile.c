#include "ble_state_profile.h"

#include <furi.h>
#include <furi_hal_version.h>
#include <furi_ble/event_dispatcher.h>
#include <furi_ble/gatt.h>
#include <ble/core/ble_defs.h>
#include <ble/core/ble_std.h>
#include <ble/core/auto/ble_types.h>

#define ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE 0x0C01U

typedef struct __attribute__((packed)) {
    uint8_t type;
    uint8_t data[1];
} AiHciUartPacket;

typedef struct __attribute__((packed)) {
    uint8_t event;
    uint8_t length;
    uint8_t data[1];
} AiHciEventPacket;

typedef struct __attribute__((packed)) {
    uint16_t event_code;
    uint8_t data[1];
} AiBleCoreEvent;

#define AI_STATE_RX_MAX_LEN 64
#define AI_STATE_TX_MAX_LEN 64

typedef struct {
    uint16_t service_handle;
    BleGattCharacteristicInstance rx_characteristic;
    BleGattCharacteristicInstance tx_characteristic;
    uint8_t tx_data[AI_STATE_TX_MAX_LEN];
    GapSvcEventHandler* event_handler;
    BleStateProfileRxCallback callback;
    void* callback_context;
} BleStateService;

typedef struct {
    FuriHalBleProfileBase base;
    BleStateService* service;
} BleProfileAiState;

static const Service_UUID_t ai_state_service_uuid = {
    .Service_UUID_128 =
        {0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
         0x93, 0xf3, 0xa3, 0xb5, 0x01, 0x00, 0x40, 0x6e}};

static const BleGattCharacteristicParams ai_state_rx_params = {
    .name = "AI State RX",
    .data_prop_type = FlipperGattCharacteristicDataFixed,
    .data.fixed.length = AI_STATE_RX_MAX_LEN,
    .uuid.Char_UUID_128 =
        {0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
         0x93, 0xf3, 0xa3, 0xb5, 0x02, 0x00, 0x40, 0x6e},
    .uuid_type = UUID_TYPE_128,
    .char_properties = CHAR_PROP_WRITE_WITHOUT_RESP | CHAR_PROP_WRITE,
    .security_permissions = ATTR_PERMISSION_ENCRY_WRITE,
    .gatt_evt_mask = GATT_NOTIFY_ATTRIBUTE_WRITE,
    .is_variable = CHAR_VALUE_LEN_VARIABLE,
};

static const BleGattCharacteristicParams ai_state_tx_params = {
    .name = "AI Pet TX",
    .data_prop_type = FlipperGattCharacteristicDataFixed,
    .data.fixed.length = AI_STATE_TX_MAX_LEN,
    .uuid.Char_UUID_128 =
        {0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
         0x93, 0xf3, 0xa3, 0xb5, 0x03, 0x00, 0x40, 0x6e},
    .uuid_type = UUID_TYPE_128,
    .char_properties = CHAR_PROP_NOTIFY | CHAR_PROP_READ,
    .security_permissions = ATTR_PERMISSION_ENCRY_READ,
    .gatt_evt_mask = 0,
    .is_variable = CHAR_VALUE_LEN_VARIABLE,
};

static BleEventAckStatus ble_state_service_event_handler(void* event, void* context) {
    BleStateService* service = context;
    AiHciEventPacket* event_packet = (AiHciEventPacket*)(((AiHciUartPacket*)event)->data);
    AiBleCoreEvent* blecore_event = (AiBleCoreEvent*)event_packet->data;

    if(event_packet->event != HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE ||
       blecore_event->event_code != ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE) {
        return BleEventNotAck;
    }

    aci_gatt_attribute_modified_event_rp0* modified =
        (aci_gatt_attribute_modified_event_rp0*)blecore_event->data;
    if(modified->Attr_Handle != service->rx_characteristic.handle + 1) {
        return BleEventNotAck;
    }

    if(service->callback && modified->Attr_Data_Length) {
        service->callback(
            modified->Attr_Data, modified->Attr_Data_Length, service->callback_context);
    }
    return BleEventAckFlowEnable;
}

static BleStateService* ble_state_service_start(void) {
    BleStateService* service = malloc(sizeof(BleStateService));
    memset(service, 0, sizeof(BleStateService));

    service->event_handler =
        ble_event_dispatcher_register_svc_handler(ble_state_service_event_handler, service);
    if(!ble_gatt_service_add(
           UUID_TYPE_128, &ai_state_service_uuid, PRIMARY_SERVICE, 6, &service->service_handle)) {
        ble_event_dispatcher_unregister_svc_handler(service->event_handler);
        free(service);
        return NULL;
    }

    ble_gatt_characteristic_init(
        service->service_handle, &ai_state_rx_params, &service->rx_characteristic);
    ble_gatt_characteristic_init(
        service->service_handle, &ai_state_tx_params, &service->tx_characteristic);
    return service;
}

static void ble_state_service_stop(BleStateService* service) {
    if(!service) return;
    ble_event_dispatcher_unregister_svc_handler(service->event_handler);
    ble_gatt_characteristic_delete(service->service_handle, &service->rx_characteristic);
    ble_gatt_characteristic_delete(service->service_handle, &service->tx_characteristic);
    ble_gatt_service_delete(service->service_handle);
    free(service);
}

static FuriHalBleProfileBase* ble_profile_ai_state_start(FuriHalBleProfileParams params) {
    UNUSED(params);
    BleProfileAiState* profile = malloc(sizeof(BleProfileAiState));
    profile->base.config = ble_profile_ai_state;
    profile->service = ble_state_service_start();
    if(!profile->service) {
        free(profile);
        return NULL;
    }
    return &profile->base;
}

static void ble_profile_ai_state_stop(FuriHalBleProfileBase* profile_base) {
    furi_check(profile_base && profile_base->config == ble_profile_ai_state);
    BleProfileAiState* profile = (BleProfileAiState*)profile_base;
    ble_state_service_stop(profile->service);
    free(profile);
}

static void ble_profile_ai_state_get_gap_config(
    GapConfig* config,
    FuriHalBleProfileParams params) {
    UNUSED(params);
    static const GapConfig template = {
        .adv_service = {
            .UUID_Type = UUID_TYPE_16,
            .Service_UUID_16 = 0xA15A,
        },
        .appearance_char = 0x0000,
        .bonding_mode = true,
        .pairing_method = GapPairingPinCodeShow,
        .conn_param = {
            .conn_int_min = 0x06,
            .conn_int_max = 0x24,
            .slave_latency = 0,
            .supervisor_timeout = 0,
        },
    };

    memcpy(config, &template, sizeof(GapConfig));
    memcpy(config->mac_address, furi_hal_version_get_ble_mac(), sizeof(config->mac_address));
    strlcpy(config->adv_name, "AIPet", sizeof(config->adv_name));
}

static const FuriHalBleProfileTemplate ai_state_profile_template = {
    .start = ble_profile_ai_state_start,
    .stop = ble_profile_ai_state_stop,
    .get_gap_config = ble_profile_ai_state_get_gap_config,
};

const FuriHalBleProfileTemplate* const ble_profile_ai_state = &ai_state_profile_template;

void ble_profile_ai_state_set_rx_callback(
    FuriHalBleProfileBase* profile_base,
    BleStateProfileRxCallback callback,
    void* context) {
    furi_check(profile_base && profile_base->config == ble_profile_ai_state);
    BleProfileAiState* profile = (BleProfileAiState*)profile_base;
    profile->service->callback = callback;
    profile->service->callback_context = context;
}

bool ble_profile_ai_state_notify(
    FuriHalBleProfileBase* profile_base,
    const uint8_t* data,
    size_t size) {
    furi_check(profile_base && profile_base->config == ble_profile_ai_state);
    BleProfileAiState* profile = (BleProfileAiState*)profile_base;
    BleStateService* service = profile->service;
    if(!data || !size || size >= AI_STATE_TX_MAX_LEN) return false;
    memset(service->tx_data, 0, sizeof(service->tx_data));
    memcpy(service->tx_data, data, size);
    return ble_gatt_characteristic_update(
        service->service_handle, &service->tx_characteristic, service->tx_data);
}
