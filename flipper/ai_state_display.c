#include "ble_state_profile.h"
#include "ai_pet_crypto.h"

#include <furi.h>
#include <furi_hal.h>
#include <gui/gui.h>
#include <storage/storage.h>
#include <bt/bt_service/bt.h>
#include <notification/notification_messages.h>

#define FRAME_WIDTH 128
#define FRAME_HEIGHT 64
#define FRAME_BUFFER_SIZE 1024
#define FRAME_INTERVAL_MS 500
#define APPROVAL_LIGHT_INTERVAL_MS 50
#define APPROVAL_LIGHT_STEP 12
#define EFFECT_INTERVAL_MS 50
#define DEVICE_KEY_PATH "/ext/apps_data/ai_pet/device.key"
#define DEVICE_KEY_SIZE 32
#define AUTH_CHALLENGE_SIZE 16

typedef struct {
    float frequency;
    uint16_t duration_ms;
} AiNote;

static const AiNote approval_notes[] = {{880.0f, 110}, {1318.5f, 110}, {880.0f, 110}};
static const AiNote success_notes[] = {
    {523.3f, 80}, {659.3f, 80}, {784.0f, 80}, {1046.5f, 140}};
static const AiNote error_notes[] = {{523.3f, 130}, {0.0f, 100}, {523.3f, 130}};

typedef enum {
    AiStateWaiting,
    AiStateIdle,
    AiStateThinking,
    AiStateRunning,
    AiStateApproval,
    AiStateSuccess,
    AiStateError,
} AiState;

typedef enum {
    AiLightOff,
    AiLightSolid,
    AiLightBlink,
    AiLightBreathe,
    AiLightTimeout,
} AiLightMode;

typedef enum {
    AiEventInput,
    AiEventCommand,
} AiEventType;

typedef struct {
    AiEventType type;
    union {
        InputEvent input;
        char command[64];
    };
} AiEvent;

typedef struct {
    FuriMessageQueue* queue;
    FuriMutex* frame_mutex;
    ViewPort* viewport;
    Storage* storage;
    File* frame_file;
    Bt* bt;
    NotificationApp* notification;
    FuriHalBleProfileBase* ble_profile;
    AiState state;
    uint8_t frame_buffer[FRAME_BUFFER_SIZE];
    size_t frame_size;
    uint32_t frame_index;
    uint32_t frame_count;
    uint32_t last_frame_tick;
    bool closing;
    uint32_t approval_light_tick;
    uint8_t approval_light_level;
    bool approval_light_rising;
    bool suppress_default_sound;
    uint8_t effect_red;
    uint8_t effect_green;
    uint8_t effect_blue;
    uint8_t effect_brightness;
    AiLightMode effect_mode;
    uint32_t effect_duration_ms;
    uint32_t effect_started_tick;
    uint32_t effect_tick;
    uint8_t effect_level;
    bool effect_rising;
    bool effect_override;
    uint8_t device_key[DEVICE_KEY_SIZE];
    uint8_t challenge[AUTH_CHALLENGE_SIZE];
    bool key_ready;
    bool authenticated;
    bool approval_pending;
    bool approval_handoff;
    char approval_id[17];
    char approval_summary[33];
} AiStateApp;

static void set_state(AiStateApp* app, AiState state);

static void wake_screen(AiStateApp* app) {
    notification_message(app->notification, &sequence_display_backlight_on);
}

static bool load_device_key(AiStateApp* app) {
    File* file = storage_file_alloc(app->storage);
    bool ok = storage_file_open(file, DEVICE_KEY_PATH, FSAM_READ, FSOM_OPEN_EXISTING) &&
              storage_file_read(file, app->device_key, DEVICE_KEY_SIZE) == DEVICE_KEY_SIZE;
    storage_file_close(file);
    storage_file_free(file);
    return ok;
}

static void bytes_to_hex(const uint8_t* input, size_t size, char* output) {
    static const char hex[] = "0123456789abcdef";
    for(size_t i = 0; i < size; i++) {
        output[i * 2] = hex[input[i] >> 4];
        output[i * 2 + 1] = hex[input[i] & 0x0F];
    }
    output[size * 2] = '\0';
}

static bool hex_to_bytes(const char* input, uint8_t* output, size_t size) {
    if(strlen(input) != size * 2) return false;
    for(size_t i = 0; i < size; i++) {
        unsigned int value;
        if(sscanf(input + i * 2, "%2x", &value) != 1) return false;
        output[i] = value;
    }
    return true;
}

static void notify_text(AiStateApp* app, const char* text) {
    if(app->ble_profile) {
        ble_profile_ai_state_notify(app->ble_profile, (const uint8_t*)text, strlen(text));
    }
}

static void start_auth(AiStateApp* app) {
    app->authenticated = false;
    if(!app->key_ready) {
        notify_text(app, "auth unbound");
        return;
    }
    furi_hal_random_fill_buf(app->challenge, AUTH_CHALLENGE_SIZE);
    char challenge_hex[AUTH_CHALLENGE_SIZE * 2 + 1];
    char message[48];
    bytes_to_hex(app->challenge, AUTH_CHALLENGE_SIZE, challenge_hex);
    snprintf(message, sizeof(message), "challenge %s", challenge_hex);
    notify_text(app, message);
}

static bool verify_auth(AiStateApp* app, const char* response_hex) {
    uint8_t received[16];
    uint8_t expected[32];
    if(!app->key_ready || !hex_to_bytes(response_hex, received, sizeof(received))) {
        app->authenticated = false;
        notify_text(app, "auth failed");
        set_state(app, AiStateWaiting);
        return false;
    }
    ai_pet_hmac_sha256(
        app->device_key,
        DEVICE_KEY_SIZE,
        app->challenge,
        AUTH_CHALLENGE_SIZE,
        expected);
    uint8_t difference = 0;
    for(size_t i = 0; i < sizeof(received); i++) difference |= received[i] ^ expected[i];
    app->authenticated = difference == 0;
    notify_text(app, app->authenticated ? "auth ok" : "auth failed");
    set_state(app, app->authenticated ? AiStateIdle : AiStateWaiting);
    return app->authenticated;
}

static void send_approval_decision(AiStateApp* app, const char* decision) {
    char message[48];
    snprintf(message, sizeof(message), "decision %s %s", app->approval_id, decision);
    notify_text(app, message);
    app->approval_pending = false;
    app->approval_handoff = false;
    memset(app->approval_id, 0, sizeof(app->approval_id));
    memset(app->approval_summary, 0, sizeof(app->approval_summary));
    set_state(app, AiStateIdle);
}

static void handoff_approval(AiStateApp* app, const char* request_id) {
    if(!app->approval_pending || strcmp(app->approval_id, request_id) != 0) return;
    app->approval_pending = false;
    memset(app->approval_id, 0, sizeof(app->approval_id));
    memset(app->approval_summary, 0, sizeof(app->approval_summary));
    set_state(app, AiStateIdle);
    app->approval_handoff = true;
    view_port_update(app->viewport);
}

static const char* state_name(AiState state) {
    switch(state) {
    case AiStateIdle: return "idle";
    case AiStateThinking: return "thinking";
    case AiStateRunning: return "running";
    case AiStateApproval: return "approval";
    case AiStateSuccess: return "success";
    case AiStateError: return "error";
    default: return "waiting";
    }
}

static uint32_t state_frame_count(AiState state) {
    switch(state) {
    case AiStateIdle: return 70;
    case AiStateThinking: return 15;
    case AiStateRunning: return 65;
    case AiStateApproval: return 0;
    case AiStateSuccess: return 38;
    case AiStateError: return 20;
    default: return 0;
    }
}

static bool parse_state(const char* command, AiState* state) {
    while(*command == ' ' || *command == '\t') command++;
    if(strncmp(command, "state", 5) == 0 && (command[5] == ' ' || command[5] == ':')) {
        command += 6;
        while(*command == ' ' || *command == '\t') command++;
    }
    if(strcmp(command, "idle") == 0) *state = AiStateIdle;
    else if(strcmp(command, "thinking") == 0) *state = AiStateThinking;
    else if(strcmp(command, "running") == 0) *state = AiStateRunning;
    else if(strcmp(command, "approval") == 0) *state = AiStateApproval;
    else if(strcmp(command, "success") == 0) *state = AiStateSuccess;
    else if(strcmp(command, "error") == 0) *state = AiStateError;
    else return false;
    return true;
}

static bool parse_light_mode(const char* value, AiLightMode* mode) {
    if(strcmp(value, "off") == 0) *mode = AiLightOff;
    else if(strcmp(value, "solid") == 0) *mode = AiLightSolid;
    else if(strcmp(value, "blink") == 0) *mode = AiLightBlink;
    else if(strcmp(value, "breathe") == 0) *mode = AiLightBreathe;
    else if(strcmp(value, "timeout") == 0) *mode = AiLightTimeout;
    else return false;
    return true;
}

static void set_rgb(AiStateApp* app, uint8_t level) {
    uint16_t scale = (uint16_t)app->effect_brightness * level;
    furi_hal_light_set(LightRed, ((uint16_t)app->effect_red * scale) / 25500U);
    furi_hal_light_set(LightGreen, ((uint16_t)app->effect_green * scale) / 25500U);
    furi_hal_light_set(LightBlue, ((uint16_t)app->effect_blue * scale) / 25500U);
}

static bool load_frame(AiStateApp* app) {
    if(app->state == AiStateWaiting || app->state == AiStateApproval) {
        furi_mutex_acquire(app->frame_mutex, FuriWaitForever);
        app->frame_size = 0;
        furi_mutex_release(app->frame_mutex);
        return false;
    }
    char path[96];
    snprintf(
        path,
        sizeof(path),
        "/assets/%s/frame_%03lu.bm",
        state_name(app->state),
        app->frame_index);
    uint8_t buffer[FRAME_BUFFER_SIZE];
    if(!storage_file_open(app->frame_file, path, FSAM_READ, FSOM_OPEN_EXISTING)) {
        storage_file_close(app->frame_file);
        furi_mutex_acquire(app->frame_mutex, FuriWaitForever);
        app->frame_size = 0;
        furi_mutex_release(app->frame_mutex);
        return false;
    }
    size_t size = storage_file_read(app->frame_file, buffer, FRAME_BUFFER_SIZE);
    storage_file_close(app->frame_file);
    if(size == 0 || size > FRAME_BUFFER_SIZE) return false;
    furi_mutex_acquire(app->frame_mutex, FuriWaitForever);
    memcpy(app->frame_buffer, buffer, size);
    app->frame_size = size;
    furi_mutex_release(app->frame_mutex);
    return true;
}

static void draw_callback(Canvas* canvas, void* context) {
    AiStateApp* app = context;
    furi_mutex_acquire(app->frame_mutex, FuriWaitForever);
    canvas_clear(canvas);
    if(app->closing) {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 64, 27, AlignCenter, AlignCenter, "Closing...");
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, 64, 45, AlignCenter, AlignCenter, "Restoring Bluetooth");
    } else if(app->state == AiStateWaiting) {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 64, 18, AlignCenter, AlignCenter, "AI Pet");
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, 64, 37, AlignCenter, AlignCenter, "Waiting for Bluetooth");
        canvas_draw_str_aligned(
            canvas,
            64,
            53,
            AlignCenter,
            AlignCenter,
            app->key_ready ? "Waiting for secure link" : "Bind with USB first");
    } else if(app->approval_handoff) {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 64, 23, AlignCenter, AlignCenter, "Please confirm");
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, 64, 43, AlignCenter, AlignCenter, "on computer");
    } else if(app->approval_pending) {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 64, 11, AlignCenter, AlignCenter, "Approval");
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, 64, 28, AlignCenter, AlignCenter, app->approval_summary);
        canvas_draw_str_aligned(canvas, 64, 45, AlignCenter, AlignCenter, "OK: Allow");
        canvas_draw_str_aligned(canvas, 64, 58, AlignCenter, AlignCenter, "Back: Deny");
    } else if(app->frame_size) {
        canvas_draw_bitmap(canvas, 0, 0, FRAME_WIDTH, FRAME_HEIGHT, app->frame_buffer);
    } else {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 64, 32, AlignCenter, AlignCenter, state_name(app->state));
    }
    furi_mutex_release(app->frame_mutex);
}

static void input_callback(InputEvent* input, void* context) {
    AiStateApp* app = context;
    AiEvent event = {.type = AiEventInput, .input = *input};
    furi_message_queue_put(app->queue, &event, 0);
}

static void ble_rx_callback(const uint8_t* data, size_t size, void* context) {
    AiStateApp* app = context;
    AiEvent event = {.type = AiEventCommand};
    size = MIN(size, sizeof(event.command) - 1);
    memcpy(event.command, data, size);
    event.command[size] = '\0';
    while(size && (event.command[size - 1] == '\r' || event.command[size - 1] == '\n' ||
                   event.command[size - 1] == ' ' || event.command[size - 1] == '\t')) {
        event.command[--size] = '\0';
    }
    furi_message_queue_put(app->queue, &event, 0);
}

static void start_sound(AiStateApp* app, const AiNote* notes, size_t count) {
    if(!notes || !count || count > 4) return;
    NotificationMessage sound_messages[4] = {0};
    NotificationMessage delay_messages[4] = {0};
    NotificationSequence sequence = {NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                                     NULL, NULL, NULL, NULL, NULL, NULL};
    size_t sequence_index = 0;
    for(size_t i = 0; i < count; i++) {
        if(notes[i].frequency > 0.0f) {
            sound_messages[i].type = NotificationMessageTypeSoundOn;
            sound_messages[i].data.sound.frequency = notes[i].frequency;
            sound_messages[i].data.sound.volume = 1.0f;
            sequence[sequence_index++] = &sound_messages[i];
        } else {
            sequence[sequence_index++] = &message_sound_off;
        }
        delay_messages[i].type = NotificationMessageTypeDelay;
        delay_messages[i].data.delay.length = notes[i].duration_ms;
        sequence[sequence_index++] = &delay_messages[i];
        sequence[sequence_index++] = &message_sound_off;
    }
    sequence[sequence_index] = NULL;
    notification_message_block(app->notification, &sequence);
}

static void update_outputs(AiStateApp* app) {
    furi_hal_light_set(LightRed, 0);
    furi_hal_light_set(LightGreen, 0);
    furi_hal_light_set(LightBlue, 0);

    if(app->state == AiStateThinking) {
        furi_hal_light_set(LightBlue, 255);
    } else if(app->state == AiStateRunning) {
        furi_hal_light_set(LightRed, 255);
        furi_hal_light_set(LightGreen, 180);
    } else if(app->state == AiStateApproval) {
        app->approval_light_level = 24;
        app->approval_light_rising = true;
        app->approval_light_tick = furi_get_tick();
        furi_hal_light_set(LightRed, app->approval_light_level);
        furi_hal_light_set(LightBlue, app->approval_light_level);
        if(!app->suppress_default_sound)
            start_sound(app, approval_notes, COUNT_OF(approval_notes));
    } else if(app->state == AiStateSuccess) {
        furi_hal_light_set(LightGreen, 255);
        if(!app->suppress_default_sound)
            start_sound(app, success_notes, COUNT_OF(success_notes));
    } else if(app->state == AiStateError) {
        furi_hal_light_set(LightRed, 255);
        if(!app->suppress_default_sound)
            start_sound(app, error_notes, COUNT_OF(error_notes));
    }
}

static void start_named_sound(AiStateApp* app, const char* sound) {
    if(strcmp(sound, "single") == 0) start_sound(app, approval_notes, 1);
    else if(strcmp(sound, "double") == 0) start_sound(app, approval_notes, 2);
    else if(strcmp(sound, "triple") == 0) start_sound(app, approval_notes, 3);
    else if(strcmp(sound, "success") == 0) start_sound(app, success_notes, COUNT_OF(success_notes));
    else if(strcmp(sound, "error") == 0) start_sound(app, error_notes, COUNT_OF(error_notes));
}

static bool apply_effect_command(AiStateApp* app, const char* command) {
    char state_value[12], color[7], mode_value[10], sound[10];
    unsigned int brightness, duration;
    if(sscanf(
           command,
           "fx %11s %6s %u %9s %u %9s",
           state_value,
           color,
           &brightness,
           mode_value,
           &duration,
           sound) != 6 ||
       strlen(color) != 6 || brightness > 100 || duration > 60) {
        return false;
    }
    AiState state;
    AiLightMode mode;
    unsigned int rgb;
    if(!parse_state(state_value, &state) || !parse_light_mode(mode_value, &mode) ||
       sscanf(color, "%x", &rgb) != 1) {
        return false;
    }
    app->suppress_default_sound = true;
    set_state(app, state);
    app->suppress_default_sound = false;
    app->effect_red = (rgb >> 16) & 0xFF;
    app->effect_green = (rgb >> 8) & 0xFF;
    app->effect_blue = rgb & 0xFF;
    app->effect_brightness = brightness;
    app->effect_mode = mode;
    app->effect_duration_ms = duration * 1000U;
    app->effect_started_tick = furi_get_tick();
    app->effect_tick = app->effect_started_tick;
    app->effect_level = 24;
    app->effect_rising = true;
    app->effect_override = true;
    set_rgb(app, mode == AiLightOff ? 0 : (mode == AiLightBreathe ? 24 : 255));
    start_named_sound(app, sound);
    return true;
}

static void update_approval_light(AiStateApp* app) {
    if(app->effect_override || app->state != AiStateApproval ||
       furi_get_tick() - app->approval_light_tick < APPROVAL_LIGHT_INTERVAL_MS) {
        return;
    }
    app->approval_light_tick = furi_get_tick();
    if(app->approval_light_rising) {
        if(app->approval_light_level >= 255 - APPROVAL_LIGHT_STEP) {
            app->approval_light_level = 255;
            app->approval_light_rising = false;
        } else {
            app->approval_light_level += APPROVAL_LIGHT_STEP;
        }
    } else if(app->approval_light_level <= 24 + APPROVAL_LIGHT_STEP) {
        app->approval_light_level = 24;
        app->approval_light_rising = true;
    } else {
        app->approval_light_level -= APPROVAL_LIGHT_STEP;
    }
    furi_hal_light_set(LightRed, app->approval_light_level);
    furi_hal_light_set(LightBlue, app->approval_light_level);
}

static void update_custom_light(AiStateApp* app) {
    if(!app->effect_override || app->effect_mode == AiLightOff ||
       app->effect_mode == AiLightSolid) return;
    uint32_t now = furi_get_tick();
    if(app->effect_mode == AiLightTimeout) {
        if(app->effect_duration_ms && now - app->effect_started_tick >= app->effect_duration_ms) {
            set_rgb(app, 0);
            app->effect_mode = AiLightOff;
        }
        return;
    }
    uint32_t interval = app->effect_mode == AiLightBlink ? 500U : EFFECT_INTERVAL_MS;
    if(now - app->effect_tick < interval) return;
    app->effect_tick = now;
    if(app->effect_mode == AiLightBlink) {
        app->effect_level = app->effect_level ? 0 : 255;
    } else if(app->effect_rising) {
        if(app->effect_level >= 243) {
            app->effect_level = 255;
            app->effect_rising = false;
        } else app->effect_level += 12;
    } else if(app->effect_level <= 36) {
        app->effect_level = 24;
        app->effect_rising = true;
    } else app->effect_level -= 12;
    set_rgb(app, app->effect_level);
}

static void set_state(AiStateApp* app, AiState state) {
    furi_mutex_acquire(app->frame_mutex, FuriWaitForever);
    app->state = state;
    app->approval_handoff = false;
    app->frame_count = state_frame_count(state);
    app->frame_index = 0;
    app->last_frame_tick = furi_get_tick();
    app->effect_override = false;
    furi_mutex_release(app->frame_mutex);
    load_frame(app);
    update_outputs(app);
    wake_screen(app);
    view_port_update(app->viewport);
}

static void update_animation(AiStateApp* app) {
    if(!app->frame_count || furi_get_tick() - app->last_frame_tick < FRAME_INTERVAL_MS) return;
    app->last_frame_tick = furi_get_tick();
    app->frame_index = (app->frame_index + 1) % app->frame_count;
    load_frame(app);
    view_port_update(app->viewport);
}

int32_t ai_state_display_app(void* args) {
    UNUSED(args);
    AiStateApp* app = malloc(sizeof(AiStateApp));
    memset(app, 0, sizeof(AiStateApp));
    app->queue = furi_message_queue_alloc(32, sizeof(AiEvent));
    app->frame_mutex = furi_mutex_alloc(FuriMutexTypeNormal);
    app->storage = furi_record_open(RECORD_STORAGE);
    app->frame_file = storage_file_alloc(app->storage);
    app->bt = furi_record_open(RECORD_BT);
    app->notification = furi_record_open(RECORD_NOTIFICATION);
    app->key_ready = load_device_key(app);

    Gui* gui = furi_record_open(RECORD_GUI);
    app->viewport = view_port_alloc();
    view_port_draw_callback_set(app->viewport, draw_callback, app);
    view_port_input_callback_set(app->viewport, input_callback, app);
    gui_add_view_port(gui, app->viewport, GuiLayerFullscreen);
    set_state(app, AiStateWaiting);

    app->ble_profile = bt_profile_start(app->bt, ble_profile_ai_state, NULL);
    if(app->ble_profile) {
        ble_profile_ai_state_set_rx_callback(app->ble_profile, ble_rx_callback, app);
        furi_hal_bt_start_advertising();
    }

    bool running = true;
    while(running) {
        AiEvent event;
        if(furi_message_queue_get(app->queue, &event, 25) == FuriStatusOk) {
            if(event.type == AiEventInput) {
                if(event.input.type == InputTypePress && app->approval_pending &&
                   event.input.key == InputKeyOk) {
                    send_approval_decision(app, "allow");
                } else if(event.input.type == InputTypePress && app->approval_pending &&
                          event.input.key == InputKeyBack) {
                    send_approval_decision(app, "deny");
                } else if(event.input.key == InputKeyBack && event.input.type == InputTypePress) {
                    running = false;
                }
            } else if(event.type == AiEventCommand) {
                AiState state;
                if(strcmp(event.command, "hello") == 0) {
                    start_auth(app);
                    wake_screen(app);
                } else if(strncmp(event.command, "auth ", 5) == 0) {
                    verify_auth(app, event.command + 5);
                    wake_screen(app);
                } else if(!app->authenticated) {
                    notify_text(app, "error unauthenticated");
                } else if(strncmp(event.command, "approval_req ", 13) == 0) {
                    char id[17] = {0};
                    char summary[33] = {0};
                    if(sscanf(event.command + 13, "%16s %32[^\n]", id, summary) >= 1) {
                        strlcpy(app->approval_id, id, sizeof(app->approval_id));
                        strlcpy(
                            app->approval_summary,
                            summary[0] ? summary : "AI permission request",
                            sizeof(app->approval_summary));
                        app->approval_pending = true;
                        app->approval_handoff = false;
                        set_state(app, AiStateApproval);
                        notify_text(app, "approval shown");
                    }
                } else if(strncmp(event.command, "approval_handoff ", 17) == 0) {
                    handoff_approval(app, event.command + 17);
                } else if(strncmp(event.command, "fx ", 3) == 0) {
                    apply_effect_command(app, event.command);
                } else if(parse_state(event.command, &state)) {
                    set_state(app, state);
                }
            }
        }
        update_animation(app);
        update_approval_light(app);
        update_custom_light(app);
    }

    app->closing = true;
    notification_message_block(app->notification, &sequence_reset_sound);
    furi_hal_light_set(LightRed, 0);
    furi_hal_light_set(LightGreen, 0);
    furi_hal_light_set(LightBlue, 0);
    view_port_update(app->viewport);
    furi_delay_ms(50);
    if(app->ble_profile) {
        ble_profile_ai_state_set_rx_callback(app->ble_profile, NULL, NULL);
        furi_hal_bt_stop_advertising();
        bt_disconnect(app->bt);
        furi_delay_ms(500);
        bt_profile_restore_default(app->bt);
        app->ble_profile = NULL;
    }

    gui_remove_view_port(gui, app->viewport);
    view_port_free(app->viewport);
    furi_record_close(RECORD_GUI);
    storage_file_free(app->frame_file);
    furi_record_close(RECORD_STORAGE);
    furi_record_close(RECORD_BT);
    furi_record_close(RECORD_NOTIFICATION);
    furi_message_queue_free(app->queue);
    furi_mutex_free(app->frame_mutex);
    free(app);
    return 0;
}
