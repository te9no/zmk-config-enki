#include <zephyr/device.h>
#include <zephyr/input/input.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/util.h>

#include "enki_ui.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#if DT_HAS_COMPAT_STATUS_OKAY(hynitron_cst816s)

#define ENKI_TOUCH_DEVICE DEVICE_DT_GET(DT_NODELABEL(touch_sensor))
#define ENKI_TAP_MAX_DURATION_MS 250
#define ENKI_TAP_MAX_MOVEMENT 20
#define ENKI_DOUBLE_TAP_WINDOW_MS 400

struct enki_touch_state {
    bool active;
    bool have_start_x;
    bool have_start_y;
    int32_t start_x;
    int32_t start_y;
    int32_t last_x;
    int32_t last_y;
    int32_t max_dx;
    int32_t max_dy;
    int64_t start_time;
};

static struct enki_touch_state touch_state;
static int64_t last_tap_time;
static bool tap_pending;

static void enki_touch_handle_release(void) {
    if (!touch_state.have_start_x || !touch_state.have_start_y) {
        tap_pending = false;
        return;
    }

    const int64_t now = k_uptime_get();
    const int64_t duration = now - touch_state.start_time;
    const bool is_tap = duration <= ENKI_TAP_MAX_DURATION_MS &&
                        touch_state.max_dx <= ENKI_TAP_MAX_MOVEMENT &&
                        touch_state.max_dy <= ENKI_TAP_MAX_MOVEMENT;

    if (!is_tap) {
        tap_pending = false;
        return;
    }

    if (tap_pending && (now - last_tap_time) <= ENKI_DOUBLE_TAP_WINDOW_MS) {
        tap_pending = false;
        enki_toggle_settings_mode();
    } else {
        tap_pending = true;
        last_tap_time = now;
    }
}

static void enki_touch_process_abs(const struct input_event *evt) {
    if (!touch_state.active) {
        return;
    }

    if (evt->code == INPUT_ABS_X) {
        touch_state.last_x = evt->value;
        if (!touch_state.have_start_x) {
            touch_state.have_start_x = true;
            touch_state.start_x = evt->value;
        }
        touch_state.max_dx = MAX(touch_state.max_dx, ABS(touch_state.last_x - touch_state.start_x));
    } else if (evt->code == INPUT_ABS_Y) {
        touch_state.last_y = evt->value;
        if (!touch_state.have_start_y) {
            touch_state.have_start_y = true;
            touch_state.start_y = evt->value;
        }
        touch_state.max_dy = MAX(touch_state.max_dy, ABS(touch_state.last_y - touch_state.start_y));
    }
}

static void enki_touch_event_cb(struct input_event *evt) {
    if (evt->dev != ENKI_TOUCH_DEVICE) {
        return;
    }

    switch (evt->type) {
    case INPUT_EV_KEY:
        if (evt->code != INPUT_BTN_TOUCH) {
            break;
        }

        if (evt->value) {
            touch_state.active = true;
            touch_state.have_start_x = false;
            touch_state.have_start_y = false;
            touch_state.max_dx = 0;
            touch_state.max_dy = 0;
            touch_state.start_time = k_uptime_get();
        } else {
            if (touch_state.active) {
                enki_touch_handle_release();
            }
            touch_state.active = false;
            touch_state.have_start_x = false;
            touch_state.have_start_y = false;
            touch_state.max_dx = 0;
            touch_state.max_dy = 0;
        }
        break;
    case INPUT_EV_ABS:
        enki_touch_process_abs(evt);
        break;
    default:
        break;
    }
}

INPUT_CALLBACK_DEFINE(ENKI_TOUCH_DEVICE, enki_touch_event_cb);

#endif /* DT_HAS_COMPAT_STATUS_OKAY(hynitron_cst816s) */
