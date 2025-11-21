#!/usr/bin/env python3
"""
Convert a GIF file into a C header that embeds the raw bytes along with basic metadata.

This is handy for bundling the Enki logo animation directly in firmware so LVGL can
display it without needing to read from storage.
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path
from typing import Iterable, List

from PIL import Image, ImageSequence


def read_gif_metadata(path: Path) -> tuple[int, int, int, List[int]]:
    gif = Image.open(path)
    width, height = gif.size
    durations: List[int] = []
    frame_count = 0
    for frame in ImageSequence.Iterator(gif):
        frame_count += 1
        durations.append(int(frame.info.get("duration", 0)))
    return width, height, frame_count, durations


def chunk_hex(data: bytes, columns: int = 12) -> Iterable[str]:
    items = [f"0x{byte:02x}" for byte in data]
    for i in range(0, len(items), columns):
        yield ", ".join(items[i : i + columns])


def write_header(
    output_path: Path,
    symbol: str,
    data: bytes,
    width: int,
    height: int,
    frame_count: int,
    durations: List[int],
) -> None:
    guard = f"{symbol}_H"
    hex_lines = ",\n    ".join(chunk_hex(data))
    duration_lines = ", ".join(str(d or 0) for d in durations)
    header_body = f"""\
#ifndef {guard}
#define {guard}

#include <stddef.h>
#include <stdint.h>

#define {symbol}_WIDTH {width}
#define {symbol}_HEIGHT {height}
#define {symbol}_FRAME_COUNT {frame_count}
#define {symbol}_DATA_SIZE {len(data)}

static const uint8_t {symbol}_DATA[{len(data)}] = {{
    {hex_lines}
}};

static const uint16_t {symbol}_FRAME_DELAYS_MS[{frame_count}] = {{ {duration_lines} }};

#endif /* {guard} */
"""
    output_path.write_text(textwrap.dedent(header_body), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Embed a GIF into a C header.")
    parser.add_argument("--input", required=True, help="Path to the GIF to embed.")
    parser.add_argument("--output", required=True, help="Path to the C header to generate.")
    parser.add_argument(
        "--symbol",
        default="ENKI_LOGO_GIF",
        help="Base symbol name for generated macros and arrays (default: ENKI_LOGO_GIF).",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    symbol = args.symbol.strip().upper()

    gif_bytes = input_path.read_bytes()
    width, height, frame_count, durations = read_gif_metadata(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header(
        output_path=output_path,
        symbol=symbol,
        data=gif_bytes,
        width=width,
        height=height,
        frame_count=frame_count,
        durations=durations,
    )
    print(f"Wrote {output_path} ({len(gif_bytes)} bytes, {frame_count} frames)")


if __name__ == "__main__":
    main()
