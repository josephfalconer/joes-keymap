# Battery and layer indicators

Flash the new firmware onto **both halves**. The ZMK and Cyboard versions are
unchanged. Calibration remains available on layer 5.

## Controls

- **Battery display:** the top-left key on the right half (formerly the Dvorak
  toggle). Shows each half's own battery for ten seconds.
- **Dvorak toggle:** the top-left key on the left half, on Mod_Layer. Activate
  Mod_Layer to toggle Dvorak on or off.
- **Layer-light toggle:** the Up Arrow position on Keyboard_Control_Layer
  (innermost bottom-row key on the right half). Layer lights start enabled after
  reboot. This toggle affects layer indicators only; battery display remains
  available.

These lights work with decorative RGB switched off. With animations enabled,
status lights override only their assigned LEDs. Other LEDs keep animating.
After a status light clears, its key returns to the animation or turns off.
Indicators blank while the keyboard is idle and return when it wakes.
Static indicators do not run a repeating redraw task. Changes redraw the lights
immediately; battery display and calibration use one-shot expiry timers.
Battery levels are sampled when the button is pressed. Stock RGB animations
retain their existing update loop.

## Layer lights

All layer indicators are cyan. Multiple toggled layers can each show a light.

| Layer | Left LED | Right LED |
| --- | --- | --- |
| Mod_Layer (1) | 007 — Right Arrow | 007 — Up Arrow |
| Keyboard_Control_Layer (2) | 013 — Left Arrow | 013 — Down Arrow |
| Dvorak (3) | 019 — Equals | 019 — Minus |
| Paste_Layer (4) | 001 — physical V position | None |

Holding `layerholdtap` temporarily activates Mod_Layer without adding a layer
light. Toggling it on adds the light. Releasing a held thumb key preserves an
already-toggled layer. Both thumb holds can be used together.

The source keymap uses `ltog`, `lmo`, and `lto` in place of stock `tog`, `mo`, and
`to` to track that distinction. Copy/paste/cancel macros also use `lto`, so V
lights on entering Paste_Layer and clears on paste or cancel. Thumb LED 039 is
not used as a Paste_Layer indicator.

## Battery bars

The bars fill from **outside towards the centre**, independently on each half.
They temporarily override layer lights and animations on all five bar keys,
including darkening the unfilled positions.

| Outside → inside | LED index on either half | Left key | Right key |
| --- | --- | --- | --- |
| 20% | 031 | End | Page Down |
| 40% | 025 | Left bracket | Right bracket |
| 60% | 019 | Equals | Minus |
| 80% | 013 | Left Arrow | Down Arrow |
| 100% | 007 | Right Arrow | Up Arrow |

One light means 0–20%, two means 21–40%, three means 41–60%, four means 61–80%,
and five means 81–100%. The entire filled bar is red below 20%, yellow from
20–39%, and green from 40% upwards. Pressing the battery button again restarts
the ten-second display. V's Paste_Layer indication remains independent.

Colours, brightness (initially 10%), duration, and measured LED indexes are in
[`src/indicator_config.h`](src/indicator_config.h). Changing these requires a
rebuild and reflash.

## Studio and split updates

If you've saved bindings in Studio, they may override the firmware defaults.
Record any live changes you want to keep before restoring the firmware's
default keymap. The new controls and status-aware layer behaviors need to be
in the active keymap; old Studio bindings using stock layer behaviors won't
track persistent activation.

Layer switching, the indicator toggle, and activity changes send status updates
to both halves. There are no periodic Bluetooth status messages or stale-light
timeouts. After a half restarts or disconnects, its layer lights may be out of
sync until the next status update. Each half reads its own battery locally;
layer updates do not restart battery displays.

## Checks

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/keymap_grid.py default_layer Mod_Layer Keyboard_Control_Layer LED_Calibration
git diff --check
```

Host simulations cover both halves, external power and Studio metadata options,
hold versus toggle behavior, paste/cancel, overlapping holds, animations, RGB-off
operation, battery thresholds, expiry, and lights without periodic updates. Firmware
compilation still uses the existing GitHub Actions build; physical split and
lighting behavior need checking after flashing.
