/* SPDX-License-Identifier: MIT */
/* ZMK v0.3 / Zephyr 3.5: preserve stock RGB settings and animations. */
#include <string.h>
#include <zephyr/device.h>
#include <zephyr/drivers/led_strip.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <drivers/behavior.h>
#include <drivers/ext_power.h>
#include <dt-bindings/zmk/keys.h>
#include <zmk/behavior.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/rgb_underglow.h>
#include <zmk/workqueue.h>
#include <zmk/battery.h>
#include <zmk/activity.h>
#include "indicator_config.h"
#include "indicators.h"
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>
#endif

#define PROXY DT_NODELABEL(calibration_strip)
#define REAL_STRIP DT_PHANDLE(PROXY, strip)
#define PIXELS DT_PROP(PROXY, chain_length)
#define TIMEOUT_MS 120000
#define CALIBRATION_LAYER 5

BUILD_ASSERT(PIXELS == DT_PROP(REAL_STRIP, chain_length));

static const struct device *const strip = DEVICE_DT_GET(REAL_STRIP);
#if IS_ENABLED(CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER)
#define POWER DT_INST(0, zmk_ext_power_generic)
static const struct device *const power = DEVICE_DT_GET(POWER);
BUILD_ASSERT(DT_PROP_LEN(POWER, control_gpios) == 1);
static const struct gpio_dt_spec power_gpio = GPIO_DT_SPEC_GET(POWER, control_gpios);
static bool power_overridden;

/* ext_power_enable/disable persist their state. Override only the physical pin
 * temporarily, leaving that logical state and its saved preference untouched. */
static void calibration_power(bool override) {
    if (override || power_overridden) {
        gpio_pin_set_dt(&power_gpio, override ? 1 : ext_power_get(power));
    }
    power_overridden = override;
}
#endif
static struct led_rgb saved[PIXELS];
static struct led_rgb output[PIXELS];
static uint32_t half;
static uint32_t index_selected;
static int64_t deadline;
static bool active;
static uint32_t indicator_layers;
static bool indicators_enabled = true;
static bool indicators_awake = true;
static int64_t battery_deadline;
static uint8_t displayed_charge;
#define STATUS_ENABLED BIT(8)
#define STATUS_AWAKE BIT(9)
#define LAYER_MASK (BIT(1) | BIT(2) | BIT(3) | BIT(4))
K_MUTEX_DEFINE(calibration_lock);

static void calibration_expired(struct k_work *work);
static void battery_expired(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(calibration_expiry_work, calibration_expired);
K_WORK_DELAYABLE_DEFINE(battery_expiry_work, battery_expired);

static bool status_visible(void) {
    bool layers = indicator_layers & (IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
                                      ? LAYER_MASK : (BIT(1) | BIT(2) | BIT(3)));
    return indicators_awake && ((indicators_enabled && layers) ||
                                k_uptime_get() < battery_deadline);
}

static struct led_rgb status_color(uint32_t rgb) {
    return (struct led_rgb){
        .r = ((rgb >> 16) & 255) * INDICATOR_BRIGHTNESS_PERCENT / 100,
        .g = ((rgb >> 8) & 255) * INDICATOR_BRIGHTNESS_PERCENT / 100,
        .b = (rgb & 255) * INDICATOR_BRIGHTNESS_PERCENT / 100,
    };
}

static void paint_status(void) {
    if (!indicators_awake) {
        return;
    }
    if (indicators_enabled) {
        const uint8_t layer_leds[] = {0, MOD_LED, CONTROL_LED, DVORAK_LED};
        for (int layer = 1; layer <= 3; layer++) {
            if (indicator_layers & BIT(layer)) {
                output[layer_leds[layer]] = status_color(INDICATOR_COLOR);
            }
        }
        if (IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL) && (indicator_layers & BIT(4))) {
            output[PASTE_LED] = status_color(INDICATOR_COLOR);
        }
    }
    if (k_uptime_get() < battery_deadline) {
        const uint8_t leds[] = BATTERY_LED_INDEXES;
        uint8_t charge = displayed_charge;
        size_t count = MAX(1, (charge + 19) / 20);
        uint32_t color = charge < 20 ? BATTERY_COLOR_CRITICAL :
                         charge < 40 ? BATTERY_COLOR_LOW : BATTERY_COLOR_NORMAL;
        for (size_t i = 0; i < ARRAY_SIZE(leds); i++) {
            output[leds[i]] = i < count ? status_color(color) : (struct led_rgb){0};
        }
    }
}

static bool is_selected_half(void) {
    return half == (IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL) ? 1 : 2);
}

/* Driver calls may modify their pixel buffer, so never pass the saved frame. */
static int render(void) {
    if (active) {
        memset(output, 0, sizeof(output));
        if (is_selected_half()) {
            output[index_selected] = (struct led_rgb){.g = 24, .b = 24};
        }
    } else {
        bool on = false;
        zmk_rgb_underglow_get_state(&on);
        memcpy(output, saved, sizeof(output));
        if (!on) {
            memset(output, 0, sizeof(output));
        }
        paint_status();
    }
#if IS_ENABLED(CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER)
    calibration_power(active || status_visible());
#endif
    return led_strip_update_rgb(strip, output, PIXELS);
}

static void restore(void) {
    if (!active) {
        return;
    }
    active = false;
    k_work_cancel_delayable(&calibration_expiry_work);
    render();
}

static int proxy_update(const struct device *dev, struct led_rgb *pixels, size_t count) {
    if (count != PIXELS) {
        return -EINVAL;
    }
    k_mutex_lock(&calibration_lock, K_FOREVER);
    memcpy(saved, pixels, sizeof(saved));
    int err = render();
    k_mutex_unlock(&calibration_lock);
    return err;
}

static const struct led_strip_driver_api strip_api = {.update_rgb = proxy_update};

static int proxy_init(const struct device *dev) {
    if (!device_is_ready(strip)) {
        return -ENODEV;
    }
#if IS_ENABLED(CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER)
    if (!device_is_ready(power) || !gpio_is_ready_dt(&power_gpio)) {
        return -ENODEV;
    }
#endif
    return 0;
}

/* Init priorities must be literal integers (Zephyr uses them in section names). */
BUILD_ASSERT(CONFIG_APPLICATION_INIT_PRIORITY > 89);
DEVICE_DT_DEFINE(PROXY, proxy_init, NULL, NULL, NULL, APPLICATION, 89, &strip_api);

/* These run once at the relevant deadline, never as a redraw loop. */
static void calibration_expired(struct k_work *work) {
    bool expired = false;
    k_mutex_lock(&calibration_lock, K_FOREVER);
    if (active && k_uptime_get() >= deadline) {
        restore();
        expired = true;
    }
    k_mutex_unlock(&calibration_lock);
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    if (expired) {
        zmk_keymap_layer_deactivate(CALIBRATION_LAYER);
    }
#else
    ARG_UNUSED(expired);
#endif
}

static void battery_expired(struct k_work *work) {
    k_mutex_lock(&calibration_lock, K_FOREVER);
    if (k_uptime_get() >= battery_deadline) {
        battery_deadline = 0;
        if (!active && indicators_awake) {
            render();
        }
    }
    k_mutex_unlock(&calibration_lock);
}

/* Snapshot commands never restart the battery timer. A battery request is
 * global, but each half reads its own fuel gauge when rendering the bar. */
static int status_convert(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    if (binding->param1 == 2) {
        binding->param1 = 0;
        binding->param2 = indicator_layers | (indicators_enabled ? 0 : STATUS_ENABLED) |
                          (indicators_awake ? STATUS_AWAKE : 0);
    }
    return 0;
}

static int status_pressed(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    if (binding->param1 > 1) {
        return -EINVAL;
    }
    k_mutex_lock(&calibration_lock, K_FOREVER);
    if (binding->param1 == 1) {
        displayed_charge = MIN(zmk_battery_state_of_charge(), 100);
        battery_deadline = k_uptime_get() + BATTERY_DISPLAY_MS;
        indicators_awake = true;
        k_work_reschedule_for_queue(zmk_workqueue_lowprio_work_q(), &battery_expiry_work,
                                    K_MSEC(BATTERY_DISPLAY_MS));
    } else {
        if (indicator_layers == (binding->param2 & LAYER_MASK) &&
            indicators_enabled == !!(binding->param2 & STATUS_ENABLED) &&
            indicators_awake == !!(binding->param2 & STATUS_AWAKE)) {
            k_mutex_unlock(&calibration_lock);
            return 0;
        }
        indicator_layers = binding->param2 & LAYER_MASK;
        indicators_enabled = binding->param2 & STATUS_ENABLED;
        indicators_awake = binding->param2 & STATUS_AWAKE;
    }
    if (!active) {
        render();
    }
    k_mutex_unlock(&calibration_lock);
    return 0;
}

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
void imprint_indicators_sync(uint32_t persistent_layers) {
    /* Zephyr mutexes are recursive: create and deliver the snapshot together. */
    k_mutex_lock(&calibration_lock, K_FOREVER);
    uint32_t current = indicator_layers | (indicators_enabled ? STATUS_ENABLED : 0) |
                       (indicators_awake ? STATUS_AWAKE : 0);
    uint32_t target = (persistent_layers & LAYER_MASK) |
                      (indicators_enabled ? STATUS_ENABLED : 0) |
                      (zmk_activity_get_state() == ZMK_ACTIVITY_ACTIVE ? STATUS_AWAKE : 0);
    if (current == target) {
        k_mutex_unlock(&calibration_lock);
        return;
    }
    if (!indicators_enabled && (current & STATUS_AWAKE) == (target & STATUS_AWAKE)) {
        /* Remember layer changes locally; the next enable command carries the
         * full mask. Disabled layer lights need no radio traffic or redraw. */
        indicator_layers = target & LAYER_MASK;
        k_mutex_unlock(&calibration_lock);
        return;
    }
    struct zmk_behavior_binding binding = {
        .behavior_dev = DEVICE_DT_NAME(DT_NODELABEL(status)),
        .param2 = target,
    };
    struct zmk_behavior_binding_event event = {.timestamp = k_uptime_get()};
    zmk_behavior_invoke_binding(&binding, event, true);
    k_mutex_unlock(&calibration_lock);
}
#endif

/* Resolve relative commands centrally, then send absolute state to BOTH halves.
 * A missed command or a reconnected half cannot accumulate an index offset. */
static int convert(struct zmk_behavior_binding *binding,
                   struct zmk_behavior_binding_event event) {
    uint32_t target = half ? half : 1;
    int selected = index_selected;
    switch (binding->param1) {
    case 0: return 0; /* exit */
    case 1: case 2: return binding->param2 < PIXELS ? 0 : -EINVAL;
    case 3: selected--; break;
    case 4: selected++; break;
    case 5: selected -= 10; break;
    case 6: selected += 10; break;
    case 7: target = 1; break;
    case 8: target = 2; break;
    case 9: selected = 0; break;
    case 10: return 0; /* type index on central only */
    default: return -EINVAL;
    }
    binding->param1 = target;
    binding->param2 = CLAMP(selected, 0, PIXELS - 1);
    return 0;
}

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static uint32_t report_index;
static void type_index(struct k_work *work) {
    static const uint32_t digits[] = {N0, N1, N2, N3, N4, N5, N6, N7, N8, N9};
    uint32_t value = report_index;
    for (int divisor = 100; divisor; divisor /= 10) {
        uint32_t key = digits[(value / divisor) % 10];
        raise_zmk_keycode_state_changed_from_encoded(key, true, k_uptime_get());
        k_msleep(10);
        raise_zmk_keycode_state_changed_from_encoded(key, false, k_uptime_get());
        k_msleep(10);
    }
}
K_WORK_DEFINE(report_work, type_index);
#endif

static int pressed(struct zmk_behavior_binding *binding,
                   struct zmk_behavior_binding_event event) {
    if (binding->param1 == 10) {
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
        report_index = index_selected;
        k_work_submit_to_queue(zmk_workqueue_lowprio_work_q(), &report_work);
#endif
        return 0;
    }
    if (binding->param1 > 2 || binding->param2 >= PIXELS) {
        return -EINVAL;
    }
    k_mutex_lock(&calibration_lock, K_FOREVER);
    if (!binding->param1) {
        restore();
    } else {
        half = binding->param1;
        index_selected = binding->param2;
        active = true;
        deadline = k_uptime_get() + TIMEOUT_MS;
        k_work_reschedule_for_queue(zmk_workqueue_lowprio_work_q(), &calibration_expiry_work,
                                    K_MSEC(TIMEOUT_MS));
        render();
    }
    k_mutex_unlock(&calibration_lock);
    return 0;
}

static int released(struct zmk_behavior_binding *binding,
                    struct zmk_behavior_binding_event event) {
    return 0;
}

#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
static const struct behavior_parameter_value_metadata actions[] = {{
    .display_name = "Calibration command",
    .type = BEHAVIOR_PARAMETER_VALUE_TYPE_RANGE,
    .range = {.min = 0, .max = 10},
}};
static const struct behavior_parameter_value_metadata indexes[] = {{
    .display_name = "LED index",
    .type = BEHAVIOR_PARAMETER_VALUE_TYPE_RANGE,
    .range = {.min = 0, .max = PIXELS - 1},
}};
static const struct behavior_parameter_metadata_set parameter_sets[] = {{
    .param1_values = actions,
    .param1_values_len = ARRAY_SIZE(actions),
    .param2_values = indexes,
    .param2_values_len = ARRAY_SIZE(indexes),
}};
static const struct behavior_parameter_metadata metadata = {
    .sets = parameter_sets,
    .sets_len = ARRAY_SIZE(parameter_sets),
};
#endif

static const struct behavior_driver_api calibration_api = {
    .binding_convert_central_state_dependent_params = convert,
    .binding_pressed = pressed,
    .binding_released = released,
    .locality = BEHAVIOR_LOCALITY_GLOBAL,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .parameter_metadata = &metadata,
#endif
};

BEHAVIOR_DT_DEFINE(DT_NODELABEL(ledcal), NULL, NULL, NULL, NULL, POST_KERNEL,
                   CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &calibration_api);

#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
static const struct behavior_parameter_value_metadata status_actions[] = {{
    .display_name = "Status command",
    .type = BEHAVIOR_PARAMETER_VALUE_TYPE_RANGE,
    .range = {.min = 0, .max = 2},
}};
static const struct behavior_parameter_value_metadata status_flags[] = {{
    .display_name = "Status flags",
    .type = BEHAVIOR_PARAMETER_VALUE_TYPE_RANGE,
    .range = {.min = 0, .max = 1023},
}};
static const struct behavior_parameter_metadata_set status_sets[] = {{
    .param1_values = status_actions,
    .param1_values_len = ARRAY_SIZE(status_actions),
    .param2_values = status_flags,
    .param2_values_len = ARRAY_SIZE(status_flags),
}};
static const struct behavior_parameter_metadata status_metadata = {
    .sets = status_sets,
    .sets_len = ARRAY_SIZE(status_sets),
};
#endif
static const struct behavior_driver_api status_api = {
    .binding_convert_central_state_dependent_params = status_convert,
    .binding_pressed = status_pressed,
    .binding_released = released,
    .locality = BEHAVIOR_LOCALITY_GLOBAL,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .parameter_metadata = &status_metadata,
#endif
};
BEHAVIOR_DT_DEFINE(DT_NODELABEL(status), NULL, NULL, NULL, NULL, POST_KERNEL,
                   CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &status_api);

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
/* Also clean up when existing &to/macros leave the calibration layer. */
static int layer_changed(const zmk_event_t *event) {
    const struct zmk_layer_state_changed *layer = as_zmk_layer_state_changed(event);
    if (layer && layer->layer == CALIBRATION_LAYER && !layer->state) {
        struct zmk_behavior_binding binding = {
            .behavior_dev = DEVICE_DT_NAME(DT_NODELABEL(ledcal)),
        };
        struct zmk_behavior_binding_event binding_event = {.timestamp = k_uptime_get()};
        zmk_behavior_invoke_binding(&binding, binding_event, true);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(calibration, layer_changed);
ZMK_SUBSCRIPTION(calibration, zmk_layer_state_changed);
#endif
