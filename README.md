# Titans ASCII animation

A terminal animation of the graphic symbol from the IT Titans logo. The symbol morphs into an ASCII “IT-TITANS” wordmark; the original tagline is excluded. Runs on Python 3.9+ with no third-party packages.

The default is one continuous loop: **logo → morph into IT-TITANS → flow across text → reassemble logo → full spin → repeat**. Run `python3 titans.py`; no effect selection is needed. `--period` controls the complete loop (default 12 seconds).

```sh
python3 titans.py
python3 titans.py --period 18
python3 titans.py --effect flow
python3 titans.py --effect spin
python3 titans.py --effect spin --period 3
python3 titans.py --effect assemble
python3 titans.py --effect assemble --period 8
python3 titans.py --width 64 --duration 10
python3 titans.py --no-color
python3 titans.py --static
```

Press **Ctrl+C** to stop. Animation uses the terminal's alternate screen and restores the cursor on exit. The symbol automatically fits the terminal. `--fps` adjusts frame rate (default 24, maximum 120). `flow` animates character brightness; color terminals also show a cyan highlight. `NO_COLOR` disables color.

`--width` sets the requested width in characters (default 48, accepted range 12–200); animated output shrinks to fit the terminal and adapts when it is resized. `--duration` stops the animation after the specified number of seconds; without it, animation continues until interrupted. `--period`, `--fps`, and `--duration` must be finite numbers greater than zero. Run `python3 titans.py --help` for all options.

Individual effects remain available through `--effect` for previewing. `--effect cycle` explicitly selects the combined loop.

Flow sweeps across the fully formed text, in both color and monochrome. `--effect flow` previews the text flow alone. The logo and morph transitions have no flow or pulse. Pulse is disabled; its implementation is retained in `pulse_light()` for future use.

`spin` rotates the flat symbol 360° around its central vertical axis, like a turning sign: front, narrow edge, mirrored back, then front again. Shading changes with the angle. `--period` sets seconds per full revolution (default 12; smaller means faster). It also works with `--no-color`.

`assemble` moves particles from the logo into block letters spelling **IT-TITANS**, holds the text, then follows the same paths back to the logo. There is no scattered circle. The cycle repeats along stable particle paths. Use at least `--width 48` and a terminal with enough space for clearly readable text; smaller terminals compress the letters. `--period` controls the full cycle in seconds (default 12). Color and monochrome output are supported.

`--static`, redirected or piped output, and terminals with `TERM=dumb` produce one plain ASCII logo frame, with no terminal control codes. This uses the requested width without fitting it to the terminal, regardless of the selected effect:

```sh
python3 titans.py --static > logo.txt
```

`assets/logo-ascii.txt` contains a ready-made 48-column rendering.

## Source assets

The original [IT Titans logo](https://it-titans-gmbh.com/wp-content/uploads/2026/03/IT-Titans_Logo-scaled-300x82.png) is saved as `assets/it-titans-logo.png`. `assets/titans-symbol.png` crops the leftmost 84 × 82 pixels, isolating the graphic. The rendering uses its alpha channel, retaining the dots and connecting strands while ignoring transparent background color.

`assets/symbol-mask.bin` stores 84 × 82 unsigned 8-bit alpha values in row order. It is precomputed so running the CLI requires only Python. To rebuild the assets with ImageMagick:

```sh
magick assets/it-titans-logo.png -crop 84x82+0+0 +repage assets/titans-symbol.png
magick assets/titans-symbol.png -alpha extract -depth 8 gray:assets/symbol-mask.bin
python3 titans.py --static > assets/logo-ascii.txt
```

## Tests

Run the test suite with Python's built-in test runner; no additional packages are needed:

```sh
python3 -m unittest -v
```
