#!/usr/bin/env python3
"""Animate the IT Titans symbol with dependency-free ASCII rendering."""

import argparse
import math
import os
from pathlib import Path
import random
import shutil
import signal
import sys
import time


ASSETS = Path(__file__).resolve().parent / "assets"
SOURCE_WIDTH, SOURCE_HEIGHT = 84, 82
RAMP = " .:-=+*#%@"


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def width_value(value):
    number = int(value)
    if not 12 <= number <= 200:
        raise argparse.ArgumentTypeError("must be between 12 and 200")
    return number


def sample_mask(mask, width):
    """Area-average alpha, accounting for cells being about twice as tall as wide."""
    height = max(1, round(width * SOURCE_HEIGHT / SOURCE_WIDTH / 2))
    rows = []
    for y in range(height):
        top, bottom = y * SOURCE_HEIGHT / height, (y + 1) * SOURCE_HEIGHT / height
        row = []
        for x in range(width):
            left, right = x * SOURCE_WIDTH / width, (x + 1) * SOURCE_WIDTH / width
            total = 0.0
            for sy in range(math.floor(top), math.ceil(bottom)):
                for sx in range(math.floor(left), math.ceil(right)):
                    weight = (min(right, sx + 1) - max(left, sx)) * (min(bottom, sy + 1) - max(top, sy))
                    total += mask[sy * SOURCE_WIDTH + sx] / 255 * weight
            alpha = min(1.0, total / ((right - left) * (bottom - top)))
            row.append(alpha if alpha >= 0.10 else 0.0)
        rows.append(row)
    return rows


def rotate_mask(rows, angle):
    """Project a flat symbol rotating around its central vertical (Y) axis.

    Integrate projected cell coverage to avoid holes and flickering. Keep a
    one-character edge visible when the plane faces sideways.
    """
    width = len(rows[0])
    cosine = math.cos(angle)
    scale = max(1 / width, abs(cosine))
    offset = (width - width * scale) / 2
    projected = []
    for row in rows:
        source = row if cosine >= 0 else row[::-1]
        target = [0.0] * width
        for x, alpha in enumerate(source):
            left, right = offset + x * scale, offset + (x + 1) * scale
            for dest in range(max(0, math.floor(left)), min(width, math.ceil(right))):
                target[dest] += alpha * (min(right, dest + 1) - max(left, dest))
        projected.append([min(1.0, value) if value >= 0.10 else 0.0 for value in target])
    return projected


# A small block font keeps the full name readable at the default 48 columns.
TEXT = "IT-TITANS"
FONT = {
    "I": ("###", " # ", " # ", " # ", "###"),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  "),
    "-": ("   ", "   ", "###", "   ", "   "),
    "A": (" ### ", "#   #", "#####", "#   #", "#   #"),
    "N": ("#   #", "##  #", "# # #", "#  ##", "#   #"),
    "S": (" ####", "#    ", " ### ", "    #", "#### "),
}


def text_mask(width, height):
    """Center the block wordmark in the same canvas as the logo."""
    font = FONT
    if width < 47:
        # Narrower T glyphs preserve letter spacing in an 80 × 24 terminal.
        font = {**FONT, "T": ("###", " # ", " # ", " # ", " # ")}
    bitmap = [" ".join(font[letter][y] for letter in TEXT) for y in range(5)]
    scale = max(1, min(width // len(bitmap[0]), height // 5))
    text_width = min(width, len(bitmap[0]) * scale)
    text_height = min(height, 5 * scale)
    left, top = (width - text_width) // 2, (height - text_height) // 2
    result = [[0.0] * width for _ in range(height)]
    for y in range(text_height):
        for x in range(text_width):
            sx = min(len(bitmap[0]) - 1, x * len(bitmap[0]) // text_width)
            sy = min(4, y * 5 // text_height)
            if bitmap[sy][sx] == "#":
                result[top + y][left + x] = 1.0
    return result


def morph_mask(rows, amount):
    """Move logo particles into IT-TITANS; reverse amount to reassemble it."""
    height, width = len(rows), len(rows[0])
    target = text_mask(width, height)
    if amount <= 0:
        return [row[:] for row in rows]
    if amount >= 1:
        return target
    source_points = sorted((x, y, alpha) for y, row in enumerate(rows)
                           for x, alpha in enumerate(row) if alpha)
    target_points = sorted((x, y, alpha) for y, row in enumerate(target)
                           for x, alpha in enumerate(row) if alpha)
    # Very small terminals may have no visible cells in one of the shapes.
    if not source_points or not target_points:
        return [[a * (1 - amount) + b * amount for a, b in zip(src, dst)]
                for src, dst in zip(rows, target)]
    amount = amount * amount * (3 - 2 * amount)
    bend = math.sin(math.pi * amount)
    result = [[0.0] * width for _ in rows]
    rng = random.Random(42)
    count = max(len(source_points), len(target_points))
    for index in range(count):
        x, y, alpha = source_points[index * len(source_points) // count]
        tx, ty, target_alpha = target_points[index * len(target_points) // count]
        px = x + (tx - x) * amount + rng.uniform(-width * 0.12, width * 0.12) * bend
        py = y + (ty - y) * amount + rng.uniform(-height * 0.18, height * 0.18) * bend
        px, py = max(0.0, min(width - 1, px)), max(0.0, min(height - 1, py))
        brightness = alpha + (target_alpha - alpha) * amount
        # Multiple logo particles can converge on one text cell (and split
        # again on the return journey). Max blending avoids bright clumps.
        left, top = math.floor(px), math.floor(py)
        for dy in (top, top + 1):
            for dx in (left, left + 1):
                if 0 <= dx < width and 0 <= dy < height:
                    coverage = (1 - abs(px - dx)) * (1 - abs(py - dy))
                    result[dy][dx] = max(result[dy][dx], brightness * coverage)
    return [[value if value >= 0.035 else 0.0 for value in row] for row in result]


def assemble_mask(rows, phase):
    """Logo → text → logo, with readable holds at both endpoints."""
    phase %= 1.0
    if phase < 0.1 or phase >= 0.9:
        amount = 0.0
    elif phase < 0.4:
        amount = (phase - 0.1) / 0.3
    elif phase <= 0.6:
        amount = 1.0
    else:
        amount = (0.9 - phase) / 0.3
    return morph_mask(rows, amount)


def pulse_light(progress):
    """Retained for future use; no active animation calls this effect."""
    return 1.0 - 0.4 * math.sin(math.pi * progress) ** 2


def flow_light(x, width, progress):
    """Sweep a band across the text, with full brightness at the endpoints."""
    position = x / max(1, width - 1)
    wave = ((math.cos((position - progress) * math.tau) + 1) / 2) ** 4
    strength = math.sin(math.pi * progress) ** 2
    return 1.0 - 0.5 * (1 - wave) * strength


def render(rows, elapsed=0, effect="cycle", color=False, static=False, period=6):
    if effect == "cycle" and not static:
        phase = (elapsed / period) % 1.0
        if phase < 0.75:
            effect, elapsed = "assemble", phase / 0.75 * period
        else:
            effect, elapsed = "spin", (phase - 0.75) / 0.25 * period
    angle = elapsed / period * math.tau
    text_flow_progress = None
    if effect == "spin" and not static:
        rows = rotate_mask(rows, angle)
    elif effect == "assemble" and not static:
        assembly_phase = (elapsed / period) % 1.0
        rows = assemble_mask(rows, assembly_phase)
        if 0.4 <= assembly_phase <= 0.6:
            text_flow_progress = (assembly_phase - 0.4) / 0.2
    elif effect == "flow" and not static:
        rows = text_mask(len(rows[0]), len(rows))
        text_flow_progress = (elapsed / period) % 1.0
    lines = []
    for y, row in enumerate(rows):
        line = []
        for x, alpha in enumerate(row):
            if not alpha:
                line.append(" ")
                continue
            if static:
                light = 1.0
            elif text_flow_progress is not None:
                light = flow_light(x, len(row), text_flow_progress)
            elif effect == "spin":
                light = 0.55 + 0.45 * abs(math.cos(angle))
            else:
                light = 1.0
            char = RAMP[max(1, round(alpha * light * (len(RAMP) - 1)))]
            if color:
                brightness = 0.45 + 0.55 * light
                red = round(20 + 100 * light)
                green, blue = round(210 * brightness), round(250 * brightness)
                line.append(f"\033[38;2;{red};{green};{blue}m{char}")
            else:
                line.append(char)
        # Animated frames must overwrite the entire previous silhouette.
        text = "".join(line)
        lines.append((text.rstrip() if static else text) + ("\033[0m" if color else ""))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=width_value, default=48, help="symbol width in characters, 12–200 (default: 48)")
    parser.add_argument("--effect", choices=("cycle", "flow", "spin", "assemble"), default="cycle", help="animation to play (default: cycle, logo to text and back, then spin)")
    parser.add_argument("--period", type=positive_float, default=12, help="seconds per full loop, spin or assembly cycle (default: 12)")
    parser.add_argument("--fps", type=positive_float, default=24, help="frames per second, at most 120 (default: 24)")
    parser.add_argument("--duration", type=positive_float, help="stop after this many seconds")
    parser.add_argument("--static", action="store_true", help="print one plain ASCII frame")
    parser.add_argument("--no-color", action="store_true", help="animate using plain ASCII brightness")
    args = parser.parse_args(argv)
    if args.fps > 120:
        parser.error("--fps must be at most 120")
    try:
        mask = (ASSETS / "symbol-mask.bin").read_bytes()
    except OSError as error:
        parser.exit(1, f"Cannot read symbol asset: {error}\n")
    if len(mask) != SOURCE_WIDTH * SOURCE_HEIGHT:
        parser.exit(1, "Symbol mask is invalid; expected 84 × 82 bytes.\n")

    interactive = sys.stdout.isatty() and os.environ.get("TERM") != "dumb"
    if args.static or not interactive:
        print(render(sample_mask(mask, args.width), static=True))
        return 0

    color = not args.no_color and "NO_COLOR" not in os.environ
    previous_width = None
    previous_size = None
    started = time.monotonic()

    def stop(signum, frame):
        raise KeyboardInterrupt

    previous_handler = signal.signal(signal.SIGTERM, stop)
    try:
        sys.stdout.write("\033[?1049h\033[?25l\033[2J")
        while True:
            frame_started = time.monotonic()
            elapsed = frame_started - started
            if args.duration is not None and elapsed >= args.duration:
                break
            columns, lines = shutil.get_terminal_size()
            width = max(1, min(args.width, columns - 2, int(max(1, lines - 2) * 2 * SOURCE_WIDTH / SOURCE_HEIGHT)))
            if width != previous_width:
                rows = sample_mask(mask, width)
                previous_width = width
            if (columns, lines) != previous_size:
                sys.stdout.write("\033[2J")
                previous_size = (columns, lines)
            left = " " * max(0, (columns - width) // 2)
            top = max(1, (lines - len(rows)) // 2 + 1)
            frame = render(rows, elapsed, args.effect, color, period=args.period)
            sys.stdout.write(f"\033[{top};1H" + ("\r\n".join(left + line for line in frame.split("\n"))))
            sys.stdout.flush()
            time.sleep(max(0, 1 / args.fps - (time.monotonic() - frame_started)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?25h\033[?1049l")
        sys.stdout.flush()
        signal.signal(signal.SIGTERM, previous_handler)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # A closed pipe (e.g. `titans.py --static | head`) is normal CLI use.
        raise SystemExit(0)
