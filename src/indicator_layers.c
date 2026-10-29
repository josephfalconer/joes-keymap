/* SPDX-License-Identifier: MIT */
#define DT_DRV_COMPAT joe_indicator_layer
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include "indicators.h"

enum layer_mode { TOGGLE, MOMENTARY, TO };
struct layer_config { enum layer_mode mode; };

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#include <zmk/keymap.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/workqueue.h>

#define LAYERS 6
static uint32_t persistent;
static uint8_t held[LAYERS];
static bool switching;

static int layer_press(struct zmk_behavior_binding *binding,
                       struct zmk_behavior_binding_event event) {
    uint32_t layer = binding->param1;
    if (layer >= LAYERS) {
        return -EINVAL;
    }
    const struct layer_config *config = zmk_behavior_get_binding(binding->behavior_dev)->config;
    int err;
    switching = true;
    switch (config->mode) {
    case TOGGLE:
        persistent ^= BIT(layer);
        err = (persistent & BIT(layer)) || held[layer] ? zmk_keymap_layer_activate(layer) :
                                                       zmk_keymap_layer_deactivate(layer);
        break;
    case MOMENTARY:
        held[layer]++;
        err = zmk_keymap_layer_activate(layer);
        break;
    case TO:
        persistent = layer ? BIT(layer) : 0;
        err = zmk_keymap_layer_to(layer);
        break;
    default:
        err = -EINVAL;
    }
    switching = false;
    imprint_indicators_sync(persistent);
    return err;
}

static int layer_release(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    uint32_t layer = binding->param1;
    if (layer >= LAYERS) {
        return -EINVAL;
    }
    const struct layer_config *config = zmk_behavior_get_binding(binding->behavior_dev)->config;
    if (config->mode == MOMENTARY && held[layer]) {
        held[layer]--;
        if (!held[layer] && !(persistent & BIT(layer))) {
            zmk_keymap_layer_deactivate(layer);
        }
    }
    imprint_indicators_sync(persistent);
    return 0;
}

static int layers_changed(const zmk_event_t *event) {
    const struct zmk_layer_state_changed *layer = as_zmk_layer_state_changed(event);
    if (layer && !switching && !layer->state) {
        persistent &= ~BIT(layer->layer);
    }
    if (!switching) {
        imprint_indicators_sync(persistent);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(indicator_layers, layers_changed);
ZMK_SUBSCRIPTION(indicator_layers, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(indicator_layers, zmk_activity_state_changed);

/* Refresh full snapshots after a right-half reconnect, including OFF states.
 * Battery timers are local and aren't extended by these five-second updates. */
static void sync_state(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(sync_work, sync_state);
static void sync_state(struct k_work *work) {
    imprint_indicators_sync(UINT32_MAX);
    k_work_reschedule_for_queue(zmk_workqueue_lowprio_work_q(), &sync_work, K_SECONDS(5));
}
static int start_sync(void) {
    k_work_reschedule_for_queue(zmk_workqueue_lowprio_work_q(), &sync_work, K_NO_WAIT);
    return 0;
}
SYS_INIT(start_sync, APPLICATION, 91);
#else
/* Layer behaviors execute on the central, unlike the global LED behaviors. */
static int layer_press(struct zmk_behavior_binding *binding,
                       struct zmk_behavior_binding_event event) { return 0; }
static int layer_release(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) { return 0; }
#endif

#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
static const struct behavior_parameter_value_metadata layer_values[] = {{
    .display_name = "Layer",
    .type = BEHAVIOR_PARAMETER_VALUE_TYPE_LAYER_ID,
}};
static const struct behavior_parameter_metadata_set layer_sets[] = {{
    .param1_values = layer_values,
    .param1_values_len = ARRAY_SIZE(layer_values),
}};
static const struct behavior_parameter_metadata layer_metadata = {
    .sets = layer_sets, .sets_len = ARRAY_SIZE(layer_sets),
};
#endif
static const struct behavior_driver_api layer_api = {
    .binding_pressed = layer_press,
    .binding_released = layer_release,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .parameter_metadata = &layer_metadata,
#endif
};
#define LAYER_INST(n)                                                                               \
    static const struct layer_config config_##n = {.mode = DT_ENUM_IDX(DT_DRV_INST(n), mode)};       \
    BEHAVIOR_DT_INST_DEFINE(n, NULL, NULL, NULL, &config_##n, POST_KERNEL,                             \
                            CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &layer_api);
DT_INST_FOREACH_STATUS_OKAY(LAYER_INST)
