#include <zephyr/device.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define ENKI_BACKLIGHT_PWM_NODE DT_ALIAS(enkibacklightpwm)

#if DT_NODE_HAS_STATUS(ENKI_BACKLIGHT_PWM_NODE, okay)
static const struct pwm_dt_spec enki_backlight_pwm = PWM_DT_SPEC_GET(ENKI_BACKLIGHT_PWM_NODE);

static int enki_backlight_init(const struct device *unused)
{
    ARG_UNUSED(unused);

    if (!device_is_ready(enki_backlight_pwm.dev)) {
        LOG_WRN("Backlight PWM device not ready");
        return -ENODEV;
    }

    const uint32_t period = enki_backlight_pwm.period;
    const uint32_t pulse = period / 2U; /* 50% duty cycle */

    int err = pwm_set_dt(&enki_backlight_pwm, period, pulse);
    if (err) {
        LOG_ERR("Failed to set backlight PWM: %d", err);
        return err;
    }

    return 0;
}

SYS_INIT(enki_backlight_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
#else
#warning "No enki_backlight_pwm alias found; backlight control disabled."
#endif
