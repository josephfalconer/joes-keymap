#!/usr/bin/env python3
"""Calculate/verify Imprint column starts; only write explicitly named layers."""
import argparse
import re
from pathlib import Path


def render(rows):
    assert [len(row) for row in rows] == [12, 12, 12, 12, 12, 10, 6, 6]
    columns = [list(range(12))] * 5 + [[0, 1, 2, 3, 4, 7, 8, 9, 10, 11]]
    widths = [0] * 12
    for row, cols in zip(rows[:6], columns):
        for cell, col in zip(row, cols):
            widths[col] = max(widths[col], len(cell))
    for row in rows[6:]:
        for cell, col in zip(row, [4, 5, None, 6, 7, 8]):
            if col is not None:
                widths[col] = max(widths[col], len(cell))
    starts = [0]
    for col in range(5):
        starts.append(starts[-1] + widths[col] + 2)
    t3 = starts[5] + max(len(row[1]) for row in rows[6:]) + 2
    starts.append(max(starts[5] + widths[5] + 4,
                      t3 + max(len(row[2]) for row in rows[6:]) + 4))
    for col in range(6, 11):
        starts.append(starts[-1] + widths[col] + 2)
    thumb = [starts[4], starts[5], t3, starts[6], starts[7], starts[8]]
    positions = [[starts[col] for col in cols] for cols in columns] + [thumb, thumb]
    lines = []
    for row, offsets in zip(rows, positions):
        line = ''
        for cell, offset in zip(row, offsets):
            assert offset >= len(line)
            line += ' ' * (offset - len(line)) + cell
        lines.append(line)
    return lines, positions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('layers', nargs='+')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'config/imprint.keymap'
    source = path.read_text()
    assert 'zmk,physical-layout = &physical_layout_imprint_function_row_full_bottom_row;' in source
    for layer in args.layers:
        pattern = re.compile(r'(' + re.escape(layer) + r'\s*\{\s*bindings\s*=\s*<\n)(.*?)(\n\s*>;)', re.S)
        match = pattern.search(source)
        assert match, layer
        original = match[2].splitlines()
        rows = [re.findall(r'&[^&]+', line) for line in original]
        rows = [[cell.strip() for cell in row] for row in rows]
        rendered, positions = render(rows)
        if args.write:
            source = source[:match.start(2)] + '\n'.join(rendered) + source[match.end(2):]
        else:
            assert original == rendered, f'{layer}: grid is not canonically aligned'
        print(f'{layer}: counts {[len(row) for row in rows]}')
        for offsets in positions:
            print(' '.join(map(str, offsets)))
    if args.write:
        path.write_text(source)


if __name__ == '__main__':
    main()
