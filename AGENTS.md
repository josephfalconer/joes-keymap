# Repository instructions

## Keymap formatting is a correctness requirement

The formatting rules in this section are mandatory for **every edit to every
`.keymap` file in this repository**. They apply even when the requested change
is functionally tiny, such as changing one key, changing one layer number,
renaming a behavior, adding a macro reference, or replacing `&trans` with a
binding. They also apply when copying a complete layer or keymap from another
keyboard.

Do not treat keymap alignment as optional cleanup. A keymap edit is incomplete
until the affected binding grids are correctly formatted and verified.

### Non-negotiable rules

1. Preserve the target keyboard's physical layout, row shape, and binding
   order. Never copy the visual formatting or line wrapping from a source
   keyboard.
2. Treat every complete ZMK binding as one indivisible cell. Examples include
   `&kp A`, `&kpholdtap LCTRL A`, `&tapcapsword CAPS 0`, and
   `&rgb_ug RGB_TOG`. Spaces inside a binding belong to that binding and are
   not column separators.
3. Use spaces only. Never use tabs inside a binding grid.
4. Columns must be fully left-aligned. The start of every populated cell in a
   logical column must be identical on every applicable row.
5. Use a minimum of exactly two spaces between adjacent columns. Determine a
   column's field width from the longest binding occupying that column, then
   pad every shorter binding so the following column remains left-aligned.
6. Preserve the deliberate visual gap between the left and right halves. This
   gap is additional to ordinary column padding and must be calculated as
   described below.
7. Preserve intentionally absent physical positions with whitespace. Do not
   add placeholder bindings merely to make formatting easier; doing so changes
   binding indexes and the resulting firmware.
8. Do not reorder bindings while formatting. Whitespace is visual, but binding
   sequence is functional.
9. Do not leave trailing whitespace.
10. After changing any binding in a layer, re-check the alignment of the whole
    layer. A longer replacement may change a column width and therefore require
    reflowing multiple rows.

### Never transfer source-keyboard formatting

When copying from another keyboard, first extract the behaviors in their
functional order, then map them to the target keyboard's physical positions.
Only after the physical mapping is correct should the target grid be rendered.

In particular, the Glove80 layout in `glove80-layout.keymap` interleaves main
row and thumb-cluster bindings near the end of each layer. The Imprint layout
does not: it has separate main rows and thumb rows. Copying the Glove80 lines,
or merely re-wrapping its flat sequence, produces a visually plausible but
physically incorrect Imprint keymap.

Source keymap formatting must always be discarded. The target keyboard's
physical layout is authoritative.

## Imprint function-row/full-bottom-row grid

`config/imprint.keymap` currently selects:

```dts
zmk,physical-layout = &physical_layout_imprint_function_row_full_bottom_row;
```

Every layer for this layout has 82 bindings arranged as follows:

- Main rows 1–5: 12 bindings each, six on the left and six on the right.
- Main row 6: 10 bindings, five on the left and five on the right. The two
  inner positions are physically absent.
- Thumb row 1: six bindings, three on the left and three on the right.
- Thumb row 2: six bindings, three on the left and three on the right.

The required per-line binding counts are therefore:

```text
12, 12, 12, 12, 12, 10, 6, 6
```

The row counts and logical-column rules below are the canonical reference for
the **shape and binding order** of this grid. Literal space counts are never
reusable between layers: each layer must retain this shape while recalculating
its own column widths.

### Logical main-board columns

Call the 12 main-board columns `C1` through `C12`, from left to right.

- Rows 1–5 occupy `C1` through `C12`.
- Row 6 occupies `C1` through `C5`, then `C8` through `C12`.
- `C6` and `C7` are absent on row 6. Render that absence with whitespace; do
  not insert two extra bindings.

For a touched layer, calculate the width of each main column from the longest
binding assigned to that column in that layer. A column's normal next start is:

```text
next_start = current_start + longest_binding_length + 2
```

Binding length means the literal character length of the complete binding as
it appears in the source, including its parameters and internal spaces.

### Thumb columns and their relationship to the main board

The thumb block is not independently centred by eye. It has deliberate
relationships to the main-board columns:

- Thumb column `T1` starts at `C5`.
- Thumb column `T2` starts at `C6`.
- `T3` follows `T2`, using the widest `T2` binding plus two spaces.
- There is an additional two-space half gap after `T3`, on top of normal
  two-space column padding.
- Thumb column `T4` and main column `C7` start together.
- Thumb column `T5` and main column `C8` start together.
- Thumb column `T6` and main column `C9` start together.

This is why the right main-board half may need to move farther right than a
simple fixed centre gap would suggest. The correct start of `C7`/`T4` is the
earliest position that satisfies both of these constraints:

```text
C7 must not overlap C6 and must retain a clear half gap.
T4 = T3 start + widest T3 binding + 4 spaces.
C7 start = T4 start.
```

When calculating widths, include thumb bindings in the main columns they align
with where necessary:

- `C5` must be wide enough for `T1`.
- `C6` must be wide enough for `T2`.
- `C7` must be wide enough for `T4`.
- `C8` must be wide enough for `T5`.
- `C9` must be wide enough for `T6`.

If a newly added binding is longer, expand the affected column and shift every
later column consistently. Never squeeze a long binding into the next column,
reduce the required two-space padding, or align only the edited row.

### Current `default_layer` alignment

The current `default_layer` is a useful concrete example. At the time these
instructions were written, its main-board column starts are:

```text
C1   C2   C3   C4   C5    C6    C7    C8    C9    C10   C11   C12
0    28   54   82   104   126   168   190   212   240   268   294
```

Its thumb starts are:

```text
T1   T2   T3   T4   T5   T6
104  126  147  168  190  212
```

These numeric starts are a regression check for the current bindings, not
magic constants. If a binding changes the maximum width of a column, recalculate
the starts using the rules above. Do not force a longer binding into these old
positions.

The current alignment intentionally gives these relationships:

- `&tog 3`, `&kp K`, `&kp LC(UP)`, and `&tapcapsword CAPS 0` share `C7`/`T4`.
- `&kp RG(RS(N4))`, `&kp LC(C)`, and `&kp RET` share `C8`/`T5`.
- `&kp LG(LA(J))`, `&kp ESC`, and `&layerholdtap 1 SPACE` share `C9`/`T6`.
- Row 6 has no binding in `C6` or `C7`; its first right-side binding begins at
  `C8`.

These relationships must remain visually evident after any edit unless the
physical layout itself is deliberately changed.

## Required workflow for every keymap edit

Follow this workflow even for a one-binding change.

1. Read the file's `chosen { zmk,physical-layout = ...; };` declaration.
2. Identify the exact target layer and its physical row shape.
3. If copying from another keyboard, map source positions to target physical
   positions before touching formatting.
4. List each target row's bindings in functional order.
5. Confirm the binding counts for every row.
6. Assign bindings to logical columns, including absent physical positions.
7. Calculate the widest literal binding in every populated column.
8. Calculate all column starts using widest binding plus two spaces.
9. Apply the target layout's half-gap and thumb-alignment constraints.
10. Render every row from the calculated starts using spaces only.
11. Re-check the complete touched layer, not just the changed binding.
12. Run the verification checks below.

Do not align by repeatedly adding spaces until the layer merely looks close.
Calculate starts from the grid and verify them mechanically.

## Required verification

### Binding counts

For the current Imprint layout, each layer must have these row counts:

```text
12 12 12 12 12 10 6 6
```

For example, this command prints the number of behavior references on each
line of `default_layer`:

```sh
awk '
    /default_layer[[:space:]]*\{/ { in_layer = 1 }
    in_layer && /bindings[[:space:]]*=[[:space:]]*</ { in_bindings = 1; next }
    in_bindings && />;/ { exit }
    in_bindings { print }
' config/imprint.keymap \
| perl -ne '$count = () = /&/g; print "$count\n"'
```

If a binding contains additional behavior references inside the same cell in
the future, do not blindly trust the `&` count; inspect and count complete cells
instead.

### Column starts

Use this command to print the zero-based start position of every binding on
each `default_layer` row:

```sh
awk '
    /default_layer[[:space:]]*\{/ { in_layer = 1 }
    in_layer && /bindings[[:space:]]*=[[:space:]]*</ { in_bindings = 1; next }
    in_bindings && />;/ { exit }
    in_bindings { print }
' config/imprint.keymap \
| perl -ne '
    $offset = 0;
    while (($index = index($_, "&")) >= 0) {
        print $offset + $index, " ";
        $offset += $index + 1;
        $_ = substr($_, $index + 1);
    }
    print "\n";
'
```

For the current `default_layer`, rows 1–5 must report identical main-column
starts. Row 6 must report `C1`–`C5` followed by `C8`–`C12`. The two thumb rows
must report identical `T1`–`T6` starts.

Run an equivalent check for any other layer that is edited. Do not rely only on
visual inspection in an editor, because proportional fonts, tab rendering, and
horizontal scrolling can conceal misalignment.

### Final checks

Every keymap edit must finish with all of the following:

```sh
git diff --check
git diff -- config/imprint.keymap
```

Also inspect `git status --short` and ensure no unrelated keymap or generated
file was changed. If a local ZMK build is available, run the relevant firmware
build after structural or behavioral changes. Formatting checks do not replace
compilation when bindings, behaviors, includes, layer indexes, or configuration
have changed.

## Other layouts and keymap files

Do not assume every `.keymap` uses the 82-key Imprint layout. For another
physical layout:

1. Read its selected physical layout or matrix transform.
2. Find the nearest repository-provided layer that correctly demonstrates that
   target shape.
3. Derive its row counts, absent positions, half gap, and thumb placement.
4. Apply the same strict widest-binding-plus-two-spaces column algorithm.
5. Document any non-obvious layout-specific alignment before making repeated
   edits to it.

If the physical mapping or intended column relationship is uncertain, stop and
ask before editing. Do not guess at thumb placement, flatten and re-wrap a
foreign layout, or compensate for uncertainty with whitespace.
