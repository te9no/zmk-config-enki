#include <lvgl.h>
#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/keycode_state_changed.h>
#include "enki_logo_gif.h"
#include "enki_ui.h"

#define ENKI_SPLASH_DEFAULT_DURATION_MS 2000U

static lv_obj_t *counter_label;
static lv_obj_t *counter_container;
static lv_obj_t *splash_obj;
static lv_timer_t *splash_timer;
static lv_obj_t *settings_container;
static lv_obj_t *settings_label;
static bool settings_mode;
static uint32_t key_press_count;

static void update_counter_label(void) {
    if (!counter_label) {
        return;
    }

    char text[32];
    snprintf(text, sizeof(text), "Key Count: %lu", (unsigned long)key_press_count);
    lv_label_set_text(counter_label, text);
}

static int counter_event_handler(const zmk_event_t *eh) {
    const struct zmk_keycode_state_changed *event = as_zmk_keycode_state_changed(eh);
    if (!event || !event->state) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    key_press_count++;
    update_counter_label();
    return ZMK_EV_EVENT_BUBBLE;
}

static void cancel_splash_timer(void) {
    if (!splash_timer) {
        return;
    }

    lv_timer_del(splash_timer);
    splash_timer = NULL;
}

static void show_counter_ui(void) {
    if (!counter_container) {
        return;
    }

    cancel_splash_timer();
    lv_obj_clear_flag(counter_container, LV_OBJ_FLAG_HIDDEN);
    if (settings_container) {
        lv_obj_add_flag(settings_container, LV_OBJ_FLAG_HIDDEN);
    }
    if (splash_obj) {
        lv_obj_del_async(splash_obj);
        splash_obj = NULL;
    }
}

static void show_settings_ui(void) {
    if (!settings_container) {
        return;
    }

    cancel_splash_timer();
    if (counter_container) {
        lv_obj_add_flag(counter_container, LV_OBJ_FLAG_HIDDEN);
    }
    lv_obj_clear_flag(settings_container, LV_OBJ_FLAG_HIDDEN);
    if (splash_obj) {
        lv_obj_del_async(splash_obj);
        splash_obj = NULL;
    }
}

static void splash_timer_cb(lv_timer_t *timer) {
    if (timer == splash_timer) {
        splash_timer = NULL;
    }

    lv_timer_del(timer);
    show_counter_ui();
}

static void start_splash_timer(uint32_t duration_ms) {
    if (!duration_ms) {
        show_counter_ui();
        return;
    }

    cancel_splash_timer();
    splash_timer = lv_timer_create(splash_timer_cb, duration_ms, NULL);
    if (!splash_timer) {
        show_counter_ui();
    }
}

static uint32_t calculate_splash_duration_ms(void) {
#if LV_USE_GIF
    uint32_t duration = 0U;
    const size_t delays_len =
        sizeof(ENKI_LOGO_GIF_FRAME_DELAYS_MS) / sizeof(ENKI_LOGO_GIF_FRAME_DELAYS_MS[0]);
    for (size_t i = 0; i < delays_len; i++) {
        duration += ENKI_LOGO_GIF_FRAME_DELAYS_MS[i];
    }

    if (duration > 0U) {
        return duration;
    }
#endif
    return ENKI_SPLASH_DEFAULT_DURATION_MS;
}

static void screen_cleanup_event_cb(lv_event_t *event) {
    LV_UNUSED(event);
    cancel_splash_timer();
    counter_label = NULL;
    counter_container = NULL;
    splash_obj = NULL;
    settings_container = NULL;
    settings_label = NULL;
}

ZMK_LISTENER(enki_counter_listener, counter_event_handler);
ZMK_SUBSCRIPTION(enki_counter_listener, zmk_keycode_state_changed);

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x000000), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_add_event_cb(screen, screen_cleanup_event_cb, LV_EVENT_DELETE, NULL);

    counter_container = lv_obj_create(screen);
    lv_obj_remove_style_all(counter_container);
    lv_obj_set_size(counter_container, LV_PCT(100), LV_PCT(100));
    lv_obj_add_flag(counter_container, LV_OBJ_FLAG_HIDDEN);

    counter_label = lv_label_create(counter_container);
    lv_label_set_text(counter_label, "Key Count: 0");
    lv_obj_set_style_text_color(counter_label, lv_color_hex(0x00d8ff), 0);
    lv_obj_set_style_text_font(counter_label, &lv_font_montserrat_24, 0);
    lv_obj_center(counter_label);

    settings_container = lv_obj_create(screen);
    lv_obj_remove_style_all(settings_container);
    lv_obj_set_size(settings_container, LV_PCT(100), LV_PCT(100));
    lv_obj_add_flag(settings_container, LV_OBJ_FLAG_HIDDEN);

    settings_label = lv_label_create(settings_container);
    lv_label_set_text(settings_label, "Settings Mode\n(double tap to toggle)");
    lv_obj_set_style_text_color(settings_label, lv_color_hex(0xffd800), 0);
    lv_obj_set_style_text_font(settings_label, &lv_font_montserrat_24, 0);
    lv_obj_center(settings_label);

#if LV_USE_GIF
    splash_obj = lv_gif_create_from_data(screen, ENKI_LOGO_GIF_DATA);
    if (splash_obj) {
        lv_obj_center(splash_obj);
        lv_gif_set_loop_count(splash_obj, 1);
        start_splash_timer(calculate_splash_duration_ms());
    } else {
        show_counter_ui();
    }
#else
    splash_obj = lv_label_create(screen);
    if (splash_obj) {
        lv_label_set_text(splash_obj, "Enki");
        lv_obj_set_style_text_color(splash_obj, lv_color_hex(0x00d8ff), 0);
        lv_obj_set_style_text_font(splash_obj, &lv_font_montserrat_24, 0);
        lv_obj_center(splash_obj);
        start_splash_timer(ENKI_SPLASH_DEFAULT_DURATION_MS);
    } else {
        show_counter_ui();
    }
#endif

    if (settings_mode) {
        show_settings_ui();
    } else {
        lv_obj_add_flag(settings_container, LV_OBJ_FLAG_HIDDEN);
    }

    return screen;
}

void enki_set_settings_mode(bool enable) {
    if (settings_mode == enable) {
        return;
    }

    settings_mode = enable;
    if (settings_mode) {
        show_settings_ui();
    } else {
        show_counter_ui();
    }
}

void enki_toggle_settings_mode(void) { enki_set_settings_mode(!settings_mode); }
