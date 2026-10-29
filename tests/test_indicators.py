import test_led_calibration as calibration


class IndicatorTest(calibration.CalibrationTest):
    harness = r'''
#include <assert.h>
#include "CALIBRATION_SOURCE"
#include "LAYERS_SOURCE"
RUNTIME

static void status_command(unsigned action, unsigned flags) {
    struct zmk_behavior_binding b = {.param1=action,.param2=flags};
    assert(status_convert(&b,(struct zmk_behavior_binding_event){0})==0);
    assert(status_pressed(&b,(struct zmk_behavior_binding_event){0})==0);
}
static bool cyan(int index) {
    return hardware[index].r==0 && hardware[index].g==25 && hardware[index].b==25;
}
#if TEST_CENTRAL
static void hook(int layer, bool on) {
    struct zmk_layer_state_changed event={.layer=layer,.state=on};
    layer_changed(&event);
    layers_changed(&event);
}
static void layer_command(enum layer_mode mode, int layer, bool down) {
    struct layer_config config={.mode=mode};
    behavior_device.config=&config;
    struct zmk_behavior_binding b={.behavior_dev="layer",.param1=layer};
    assert((down ? layer_press(&b,(struct zmk_behavior_binding_event){0}) :
                   layer_release(&b,(struct zmk_behavior_binding_event){0}))==0);
}
#endif
int main(void) {
    assert(proxy_init(&device)==0);
    rgb_on=false;
    status_command(0, STATUS_ENABLED | STATUS_AWAKE | BIT(1) | BIT(2) | BIT(3) | BIT(4));
    assert(cyan(7) && cyan(13) && cyan(19));
    assert(cyan(1)==TEST_CENTRAL);
    assert(hardware[39].g==0); /* Paste thumb must stay dark. */
#if TEST_POWER
    assert(powered);
#endif
    struct led_rgb normal[150];
    for (int i=0;i<150;i++) normal[i]=(struct led_rgb){.r=12,.g=34,.b=56};
    rgb_on=true;
    proxy_update(&device,normal,150);
    assert(cyan(7) && hardware[50].r==12 && hardware[50].g==34);
    status_command(2,0); /* Disable layer LEDs without touching animations. */
    assert(!indicators_enabled && hardware[7].r==12 && hardware[7].g==34);
    rgb_on=false;
    /* Battery display stays available with BOTH layer lights and RGB disabled. */
    const uint8_t levels[]={0,1,19,20,21,39,40,41,60,61,80,81,99,100,255};
    const uint8_t leds[]={31,25,19,13,7};
    for (size_t j=0;j<ARRAY_SIZE(levels);j++) {
        battery_charge=levels[j];
        status_command(1,0);
        unsigned charge=MIN(levels[j],100);
        unsigned count=MAX(1,(charge+19)/20);
        for (unsigned i=0;i<5;i++) {
            struct led_rgb p=hardware[leds[i]];
            assert(p.r==(i<count && charge<40 ? 25 : 0));
            assert(p.g==(i<count && charge>=20 ? 25 : 0));
            assert(p.b==0);
        }
        assert(hardware[1].g==0 && hardware[39].g==0);
    }
    /* Each build reads its local gauge rather than a transmitted percentage. */
    battery_charge=TEST_CENTRAL ? 20 : 80;
    status_command(1,0);
    assert(hardware[13].g==(TEST_CENTRAL ? 0 : 25));
    int64_t expires=battery_deadline;
    now+=5000;
    status_command(0, STATUS_AWAKE | BIT(1));
    assert(battery_deadline==expires && battery_expiry_work.due==expires); /* Layer updates don't extend battery display. */
    battery_charge=100;
    battery_changed(NULL); /* Gauge changes redraw the bar without polling. */
    assert(hardware[7].g==25 && battery_expiry_work.due==expires);
    now=expires;
    run_scheduled(&battery_expiry_work);
    assert(!battery_expiry_work.pending);
    for (unsigned i=0;i<5;i++) assert(hardware[leds[i]].g==0);
#if TEST_POWER
    assert(!powered);
#endif
    status_command(2,0);
    assert(indicators_enabled && cyan(7));
    status_command(0, STATUS_ENABLED | BIT(1)); /* Idle blanks indicators. */
    assert(hardware[7].g==0);
    status_command(0, STATUS_ENABLED | STATUS_AWAKE | BIT(1));
    assert(cyan(7));
#if !TEST_CENTRAL
    unsigned frames=frame_count;
    now+=15000;
    assert(frame_count==frames && !battery_expiry_work.pending && !calibration_expiry_work.pending);
    assert(cyan(7)); /* Static layer lights need no scheduled work. */
#else
    status_command(0, STATUS_ENABLED | STATUS_AWAKE);
    layer_hook=hook;
    layer_command(MOMENTARY,1,true);
    assert(active_layers & BIT(1));
    assert(!indicator_layers && hardware[7].g==0);
    layer_command(TOGGLE,1,true);
    assert(cyan(7));
    layer_command(MOMENTARY,1,false);
    assert(active_layers & BIT(1)); /* Release a hold without cancelling the toggle. */
    assert(cyan(7));
    layer_command(TOGGLE,1,true);
    assert(!(active_layers & BIT(1)) && hardware[7].g==0);
    layer_command(MOMENTARY,1,true);
    layer_command(MOMENTARY,1,true);
    layer_command(MOMENTARY,1,false);
    assert(active_layers & BIT(1)); /* Two independent thumb holds. */
    layer_command(TOGGLE,1,true);
    layer_command(TOGGLE,1,true);
    assert(!indicator_layers && (active_layers & BIT(1)));
    layer_command(MOMENTARY,1,false);
    assert(!(active_layers & BIT(1)));
    layer_command(MOMENTARY,1,true);
    layer_command(TO,4,true); /* Copy macro selects Paste_Layer. */
    layer_command(MOMENTARY,1,false);
    assert(active_layers==BIT(4) && cyan(1) && hardware[39].g==0);
    layer_command(TO,0,true); /* Paste or hold-cancel returns to base. */
    assert(!persistent && !indicator_layers && hardware[1].g==0);
    layer_command(MOMENTARY,1,true);
    layer_command(TO,4,true);
    layer_command(MOMENTARY,1,true);
    layer_command(MOMENTARY,1,false); /* Old held thumb is released after a switch. */
    assert(active_layers & BIT(1));
    layer_command(MOMENTARY,1,false);
    assert(!(active_layers & BIT(1)) && (active_layers & BIT(4)));
    layer_command(TO,0,true);
    layer_command(TOGGLE,2,true);
    layer_command(TOGGLE,3,true);
    assert(cyan(13) && cyan(19));
    zmk_keymap_layer_deactivate(3); /* External deactivation cannot leave stale lights. */
    assert(cyan(13) && hardware[19].g==0);
    layer_command(TO,5,true); /* Existing calibration entry clears persistent layers. */
    assert(!indicator_layers);
    activity_state=ZMK_ACTIVITY_IDLE;
    imprint_indicators_sync(persistent);
    assert(!indicators_awake);
    activity_state=ZMK_ACTIVITY_ACTIVE;
    layer_command(TOGGLE,1,true);
    assert(cyan(7));
#endif
    /* Battery expiry during calibration must leave its selected LED alone. */
    status_command(0, STATUS_ENABLED | STATUS_AWAKE | BIT(1));
    status_command(1,0);
    struct zmk_behavior_binding calibration={.param1=1,.param2=42};
    pressed(&calibration,(struct zmk_behavior_binding_event){0});
    assert(calibration_expiry_work.pending);
    now=battery_deadline;
    run_scheduled(&battery_expiry_work);
    assert(active && hardware[42].g==(TEST_CENTRAL ? 24 : 0));
    calibration.param1=0;
    pressed(&calibration,(struct zmk_behavior_binding_event){0});
    assert(cyan(7) && !calibration_expiry_work.pending && !battery_expiry_work.pending);
    return 0;
}
'''
