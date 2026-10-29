# LED calibration

This adds layer 5 to the existing keymap, on the pinned ZMK v0.3.0 stack.
Flash the new firmware to **both halves**. The measured indexes now drive the
[battery and layer indicators](INDICATORS.md); calibration remains available
for checking additional keys.

## Enter and leave

1. Activate Keyboard_Control_Layer using its existing toggle: the innermost
   top-row key on the left half.
2. Press the **outermost top-row key on the right half** (Volume Up on the base
   layer). This enters calibration with left LED index 0 selected.
3. To leave, press either half's **outermost top-row key**. This returns to the
   base layer and restores ordinary lighting.

Only the top/function row changes on the calibration layer. All other keys
fall through to the normal base keymap, so letters, numbers, arrows, and thumb
keys remain usable. Entering calibration clears other active layers. Existing
macros that switch away from calibration also restore normal lighting.

Studio-saved bindings can override source defaults after flashing. If the entry
key still performs its previous action, assign `calibration_enter` to that
position in Studio, or use Studio's restore-defaults facility after recording
any live edits you want to keep.

## Controls

Positions below count **left to right as seen in the keymap**, separately on
each half's top/function row. They refer to physical keys, not F-key legends.

| Position | Left half | Right half |
| --- | --- | --- |
| 1 (leftmost) | Exit to base | Previous 10 LEDs |
| 2 | Reset index to 0 | Previous LED |
| 3 | Select left half | Next LED |
| 4 | Select right half | Next 10 LEDs |
| 5 | Type current index | Type current index |
| 6 (rightmost) | No action | Exit to base |

Only the selected half lights one LED, in dim cyan; the other half is dark.
Switching halves retains the index. The index is clamped to **0–149**; it does
not wrap. Some indexes may not correspond to installed LEDs.

Open a plain text editor and release any modifiers before using **Type current
index**. It types three digits, for example `037`, at the current cursor. It
does not press Enter. This is a normal keystroke output, so choose the text
field before pressing it.

Calibration works even with decorative RGB off. It temporarily suppresses
animations without modifying their settings or saving calibration state to
flash. Leaving restores the previous lighting. After **two minutes without a
selection command**, calibration lighting stops; the central half also removes
the calibration layer. If the right half disconnects during calibration, its
own timeout still clears its light. Re-enter calibration to start again.

## Record these indexes

For each half, locate its five bottom-row LEDs. Record them **outside to
inside**, regardless of the order in which they occur in the LED strip.

| Target | Left LED index | Right LED index |
| --- | --- | --- |
| 20% — outermost, END / Page Down | 031 | 031 |
| 40% — next inward | 025 | 025 |
| 60% — middle | 019 | 019 |
| 80% — next inward | 013 | 013 |
| 100% — innermost, Right Arrow / Up Arrow | 007 | 007 |
| Physical V key (base layer) | 001 | Not needed |
| Paste/cancel thumb key (unused by indicators) | 039 | Not needed |

Select the left half first, then reset to 0 and advance through the strip. When
a target lights, use the index-report key to record its number beside its name.
Repeat for the right half. Use ten-step jumps once you can see the wiring order.
`config/info.json` describes key positions, not this electrical LED order.

## Implementation and checks

The module supplies a virtual strip between stock underglow and the physical
WS2812 driver. Outside calibration it forwards normal frames. During calibration
it retains the latest animation frame and substitutes a single-LED frame.
Commands are converted to an absolute half/index on the central and forwarded
using ZMK's existing global-behavior transport. No custom BLE protocol or ZMK
source fork is needed.

Local checks:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/keymap_grid.py Keyboard_Control_Layer LED_Calibration
git diff --check
```

The C simulation exercises the actual driver source for both halves, with and
without external power control. It covers normal frame forwarding, driver-buffer
mutation, selection, bounds, index reporting, restoration, and timeout cleanup.
It does **not** replace building both firmware targets or testing on hardware.
The existing GitHub Actions workflow builds both halves with this module.
