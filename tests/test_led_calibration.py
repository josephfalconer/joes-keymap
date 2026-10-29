"""Run the actual calibration C code against a small simulated strip/Zephyr API.

This checks rendering and restoration, not firmware compilation or BLE transport.
Run with: python3 -m unittest discover -s tests -v
"""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

STUB = r'''
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
#define CONFIG_ZMK_RGB_UNDERGLOW_EXT_POWER TEST_POWER
#define CONFIG_ZMK_SPLIT_ROLE_CENTRAL TEST_CENTRAL
#define CONFIG_ZMK_BEHAVIOR_METADATA TEST_METADATA
#define CONFIG_APPLICATION_INIT_PRIORITY 90
#define CONFIG_KERNEL_INIT_PRIORITY_DEFAULT 40
#define IS_ENABLED(x) (x)
#define BUILD_ASSERT(x) _Static_assert(x, #x)
#define DT_NODELABEL(x) x
#define DT_PHANDLE(x,y) 0
#define DT_PROP(x,y) 150
#define DT_INST(x,y) 0
#define DT_PROP_LEN(x,y) 1
#define DEVICE_DT_GET(x) (&device)
#define STRINGIFY(x) #x
#define DEVICE_DT_NAME(x) STRINGIFY(x)
#define DEVICE_DT_DEFINE(...)
#define BEHAVIOR_DT_DEFINE(...)
#define DT_INST_FOREACH_STATUS_OKAY(x)
#define SYS_INIT(...)
#define K_MUTEX_DEFINE(x) int x
#define K_FOREVER 0
#define K_MSEC(x) (x)
#define K_SECONDS(x) ((x)*1000)
#define K_NO_WAIT 0
#define BIT(x) (1U << (x))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define CLAMP(x,a,b) ((x)<(a)?(a):((x)>(b)?(b):(x)))
#define ARG_UNUSED(x) (void)(x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define ZMK_EV_EVENT_BUBBLE 0
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
#define N0 0
#define N1 1
#define N2 2
#define N3 3
#define N4 4
#define N5 5
#define N6 6
#define N7 7
#define N8 8
#define N9 9
struct device { const void *config; };
static struct device device;
static struct device behavior_device;
static const struct device *zmk_behavior_get_binding(const char *name) { return &behavior_device; }
struct led_rgb { uint8_t r,g,b; };
static struct led_rgb hardware[150];
static bool rgb_on, powered, normal_power, ready = true;
static int64_t now;
static char typed[10];
static int typed_length;
static unsigned frame_count;
static unsigned power_write_count, status_messages;
static uint8_t battery_charge;
static uint8_t zmk_battery_state_of_charge(void) { return battery_charge; }
enum { ZMK_ACTIVITY_ACTIVE, ZMK_ACTIVITY_IDLE };
static int activity_state = ZMK_ACTIVITY_ACTIVE;
static int zmk_activity_get_state(void) { return activity_state; }
static bool device_is_ready(const struct device *d) { return ready; }
static int led_strip_update_rgb(const struct device *d, struct led_rgb *p, size_t n) {
    frame_count++;
    memcpy(hardware, p, n*sizeof(*p));
    memset(p, 0xA5, n*sizeof(*p)); /* Allowed by the real LED API. */
    return 0;
}
struct led_strip_driver_api {
    int (*update_rgb)(const struct device*, struct led_rgb*, size_t);
};
static int zmk_rgb_underglow_get_state(bool *on) { *on = rgb_on; return 0; }
struct gpio_dt_spec { int unused; };
#define GPIO_DT_SPEC_GET(x,y) {0}
static bool gpio_is_ready_dt(const struct gpio_dt_spec *s) { return ready; }
static int gpio_pin_set_dt(const struct gpio_dt_spec *s, int value) {
    power_write_count++;
    powered = value;
    return 0;
}
static int ext_power_get(const struct device *d) { return normal_power; }
static int64_t k_uptime_get(void) { return now; }
static void k_msleep(int ms) { now += ms; }
static void k_mutex_lock(int *m, int timeout) {}
static void k_mutex_unlock(int *m) {}
struct k_work { void (*handler)(struct k_work*); };
struct k_work_delayable { struct k_work work; bool pending; int64_t due; };
#define K_WORK_DEFINE(n,f) struct k_work n = {.handler=f}
#define K_WORK_DELAYABLE_DEFINE(n,f) struct k_work_delayable n = {.work={.handler=f}}
static void *zmk_workqueue_lowprio_work_q(void) { return NULL; }
static int k_work_reschedule_for_queue(void *q, struct k_work_delayable *w, int ms) {
    w->pending=true;
    w->due=now+ms;
    return 0;
}
static int k_work_cancel_delayable(struct k_work_delayable *w) { w->pending=false; return 0; }
static void run_scheduled(struct k_work_delayable *w) {
    if (!w->pending || now<w->due) __builtin_trap();
    w->pending=false;
    w->work.handler(&w->work);
}
static int k_work_submit_to_queue(void *q, struct k_work *w) { w->handler(w); return 0; }
static int raise_zmk_keycode_state_changed_from_encoded(uint32_t key, bool pressed, int64_t t) {
    if (pressed) typed[typed_length++] = '0' + key;
    return 0;
}
struct zmk_behavior_binding { const char *behavior_dev; uint32_t param1,param2; };
struct zmk_behavior_binding_event { int64_t timestamp; };
struct zmk_layer_state_changed { int layer; bool state; };
typedef struct zmk_layer_state_changed zmk_event_t;
static const struct zmk_layer_state_changed *as_zmk_layer_state_changed(const zmk_event_t *e) { return e; }
static int deactivated = -1, invoked_exit;
static uint32_t active_layers;
static void (*layer_hook)(int, bool);
static int zmk_keymap_layer_deactivate(int layer) {
    deactivated = layer;
    bool was = active_layers & BIT(layer);
    active_layers &= ~BIT(layer);
    if (was && layer_hook) layer_hook(layer, false);
    return 0;
}
static int zmk_keymap_layer_activate(int layer) {
    bool was = active_layers & BIT(layer);
    active_layers |= BIT(layer);
    if (!was && layer_hook) layer_hook(layer, true);
    return 0;
}
static int zmk_keymap_layer_to(int layer) {
    for (int i=5; i>=0; i--) zmk_keymap_layer_deactivate(i);
    return zmk_keymap_layer_activate(layer);
}
static int zmk_behavior_invoke_binding(const struct zmk_behavior_binding *b,
                                      struct zmk_behavior_binding_event e, bool pressed);
enum { BEHAVIOR_LOCALITY_GLOBAL };
enum { BEHAVIOR_PARAMETER_VALUE_TYPE_RANGE, BEHAVIOR_PARAMETER_VALUE_TYPE_LAYER_ID };
struct behavior_parameter_value_metadata {
    char *display_name;
    int type;
    struct { int32_t min, max; } range;
};
struct behavior_parameter_metadata_set {
    const struct behavior_parameter_value_metadata *param1_values, *param2_values;
    size_t param1_values_len, param2_values_len;
};
struct behavior_parameter_metadata {
    const struct behavior_parameter_metadata_set *sets;
    size_t sets_len;
};
struct behavior_driver_api {
    int (*binding_convert_central_state_dependent_params)(struct zmk_behavior_binding*,struct zmk_behavior_binding_event);
    int (*binding_pressed)(struct zmk_behavior_binding*,struct zmk_behavior_binding_event);
    int (*binding_released)(struct zmk_behavior_binding*,struct zmk_behavior_binding_event);
    int locality;
    const struct behavior_parameter_metadata *parameter_metadata;
};
'''

HARNESS = r'''
#include <assert.h>
#include "CALIBRATION_SOURCE"
RUNTIME
static void command(unsigned action, unsigned index) {
    struct zmk_behavior_binding b = {.param1=action,.param2=index};
    assert(convert(&b,(struct zmk_behavior_binding_event){0}) == 0);
    assert(pressed(&b,(struct zmk_behavior_binding_event){0}) == 0);
}
static void check_single(bool selected, int index) {
    for (int i=0;i<150;i++) {
        assert(hardware[i].r == 0);
        assert(hardware[i].g == (selected && i==index ? 24 : 0));
        assert(hardware[i].b == (selected && i==index ? 24 : 0));
    }
}
int main(void) {
    assert(proxy_init(&device)==0);
    ready=false;
    assert(proxy_init(&device)==-ENODEV);
    ready=true;
    struct led_rgb normal[150];
    for (int i=0;i<150;i++) normal[i]=(struct led_rgb){.r=12,.g=34,.b=56};
    rgb_on=true;
    assert(proxy_update(&device, normal, 149)==-EINVAL);
    assert(proxy_update(&device, normal, 150)==0);
    assert(hardware[0].r==12);
    assert(normal[0].r==12); /* Physical driver cannot corrupt stock RGB buffer. */
    unsigned power_writes=power_write_count;
    proxy_update(&device, normal,150);
    assert(power_write_count==power_writes); /* Normal animations don't rewrite LED power. */
    command(1,0);
#if TEST_POWER
    assert(power_write_count==power_writes+1); /* One power override per selection, not two. */
#endif
    assert(active && index_selected==0);
    check_single(TEST_CENTRAL,0);
    command(6,0); /* +10 */
    command(4,0); /* +1 */
    assert(index_selected==11);
    command(8,0); /* select right; index is retained */
    check_single(!TEST_CENTRAL,11);
    command(10,0);
#if TEST_CENTRAL
    assert(typed_length==3 && memcmp(typed,"011",3)==0);
#else
    assert(typed_length==0);
#endif
    assert(proxy_update(&device, normal,150)==0);
    check_single(!TEST_CENTRAL,11); /* Animations cannot overwrite calibration. */
    command(0,0);
    assert(!active && hardware[0].r==12 && hardware[0].g==34);
    unsigned frames=frame_count;
    command(0,0);
    assert(frame_count==frames); /* Duplicate exit from the layer listener does no LED work. */
    rgb_on=false;
    command(2,149);
#if TEST_POWER
    assert(powered);
#endif
    command(4,0);
    assert(index_selected==149); /* Clamp at physical strip bound. */
    command(9,0);
    command(3,0);
    assert(index_selected==0);
    command(6,0);
    command(5,0);
    assert(index_selected==0);
    command(7,0);
    check_single(TEST_CENTRAL,0);
    now=deadline;
    run_scheduled(&calibration_expiry_work);
    assert(!calibration_expiry_work.pending);
    assert(!active);
#if TEST_CENTRAL
    assert(deactivated==5);
    struct zmk_layer_state_changed event={.layer=5,.state=false};
    layer_changed(&event);
    assert(invoked_exit==1);
    event.state=true;
    layer_changed(&event);
    event.layer=2;
    event.state=false;
    layer_changed(&event);
    assert(invoked_exit==1);
#endif
    check_single(false,0);
#if TEST_POWER
    assert(!powered);
#endif
    command(1,42);
    assert(calibration_expiry_work.pending && calibration_expiry_work.due==deadline);
    command(0,0);
    assert(!calibration_expiry_work.pending);
    check_single(false,0); /* RGB originally off stays off, no saved-setting changes. */
#if TEST_POWER
    normal_power=true;
    command(1,42);
    assert(calibration_expiry_work.pending && calibration_expiry_work.due==deadline);
    command(0,0);
    assert(!calibration_expiry_work.pending);
    assert(powered); /* Preserve ext-power preference even when RGB was off. */
#endif
    struct zmk_behavior_binding bad={.param1=1,.param2=150};
    assert(convert(&bad,(struct zmk_behavior_binding_event){0})==-EINVAL);
    assert(pressed(&bad,(struct zmk_behavior_binding_event){0})==-EINVAL);
    return 0;
}
'''


RUNTIME = r'''
static int zmk_behavior_invoke_binding(const struct zmk_behavior_binding *b,
                                      struct zmk_behavior_binding_event e, bool down) {
    struct zmk_behavior_binding copy = *b;
    if (!down) return 0;
    if (!strcmp(b->behavior_dev,"status")) {
        status_messages++;
        return status_pressed(&copy,e);
    }
    if (b->param1==0) invoked_exit++;
    return pressed(&copy,e);
}
'''


class CalibrationTest(unittest.TestCase):
    harness = HARNESS
    def test_both_halves_with_and_without_power_control(self):
        headers = [
            'zephyr/device.h', 'zephyr/drivers/led_strip.h', 'zephyr/drivers/gpio.h', 'zephyr/kernel.h',
            'drivers/behavior.h', 'drivers/ext_power.h', 'dt-bindings/zmk/keys.h',
            'zmk/behavior.h', 'zmk/events/keycode_state_changed.h',
            'zmk/rgb_underglow.h', 'zmk/workqueue.h',
            'zmk/event_manager.h', 'zmk/events/layer_state_changed.h', 'zmk/keymap.h',
            'zmk/battery.h', 'zmk/activity.h', 'zmk/events/activity_state_changed.h',
            'zephyr/init.h', 'zmk/events/battery_state_changed.h',
        ]
        with tempfile.TemporaryDirectory() as temp:
            folder = pathlib.Path(temp)
            (folder / 'stub.h').write_text(STUB)
            for header in headers:
                path = folder / header
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('#include "stub.h"\n')
            harness = folder / 'test.c'
            harness.write_text(self.harness.replace('CALIBRATION_SOURCE', str(ROOT / 'src/led_calibration.c'))
                               .replace('LAYERS_SOURCE', str(ROOT / 'src/indicator_layers.c'))
                               .replace('RUNTIME', RUNTIME))
            for central in (0, 1):
                for power in (0, 1):
                    for metadata in (0, 1):
                        with self.subTest(central=central, power=power, metadata=metadata):
                            binary = folder / 'test'
                            subprocess.run([
                                'clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                                '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-unused-const-variable',
                                f'-DTEST_CENTRAL={central}', f'-DTEST_POWER={power}',
                                f'-DTEST_METADATA={metadata}',
                                '-I', str(folder), str(harness), '-o', str(binary),
                            ], check=True)
                            subprocess.run([str(binary)], check=True)
