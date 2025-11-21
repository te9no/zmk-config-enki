#include <lvgl.h>
#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/keycode_state_changed.h>
#include "enki_logo_gif.h"

static lv_obj_t *counter_label;
static lv_obj_t *counter_container;
static lv_obj_t *logo_gif_obj;
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

static void show_counter_ui(void) {
    if (!counter_container) {
        return;
    }

    lv_obj_clear_flag(counter_container, LV_OBJ_FLAG_HIDDEN);
    if (logo_gif_obj) {
        lv_obj_del_async(logo_gif_obj);
        logo_gif_obj = NULL;
    }
}

static void logo_animation_finished_cb(lv_event_t *event) {
    LV_UNUSED(event);
    show_counter_ui();
}

ZMK_LISTENER(enki_counter_listener, counter_event_handler);
ZMK_SUBSCRIPTION(enki_counter_listener, zmk_keycode_state_changed);

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x000000), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);

    counter_container = lv_obj_create(screen);
    lv_obj_remove_style_all(counter_container);
    lv_obj_set_size(counter_container, LV_PCT(100), LV_PCT(100));
    lv_obj_add_flag(counter_container, LV_OBJ_FLAG_HIDDEN);

    counter_label = lv_label_create(counter_container);
    lv_label_set_text(counter_label, "Key Count: 0");
    lv_obj_set_style_text_color(counter_label, lv_color_hex(0x00d8ff), 0);
    lv_obj_set_style_text_font(counter_label, &lv_font_montserrat_24, 0);
    lv_obj_center(counter_label);

#if LV_USE_GIF
    logo_gif_obj = lv_gif_create_from_data(screen, ENKI_LOGO_GIF_DATA);
    if (logo_gif_obj) {
        lv_obj_center(logo_gif_obj);
        lv_gif_set_loop_count(logo_gif_obj, 1);
        lv_obj_add_event_cb(logo_gif_obj, logo_animation_finished_cb, LV_EVENT_READY, NULL);
    } else {
        show_counter_ui();
    }
#else
    show_counter_ui();
#endif

    return screen;
}
