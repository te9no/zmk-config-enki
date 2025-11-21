#include <lvgl.h>
#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/keycode_state_changed.h>

static lv_obj_t *counter_label;
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

ZMK_LISTENER(enki_counter_listener, counter_event_handler);
ZMK_SUBSCRIPTION(enki_counter_listener, zmk_keycode_state_changed);

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x000000), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);

    counter_label = lv_label_create(screen);
    lv_label_set_text(counter_label, "Key Count: 0");
    lv_obj_set_style_text_color(counter_label, lv_color_hex(0x00d8ff), 0);
    lv_obj_set_style_text_font(counter_label, &lv_font_montserrat_24, 0);
    lv_obj_center(counter_label);

    return screen;
}
