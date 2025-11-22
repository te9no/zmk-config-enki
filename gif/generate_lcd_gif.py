#!/usr/bin/env python3
"""
Utility for rendering simple LCD-style animations as animated GIFs.

The script creates a sequence of frames that scroll each message into
view, holds the text for a configurable duration, and scrolls it out.
All parameters can be overridden on the CLI so you can match the
physical LCD dimensions and colors used on the Enki build.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_FONT_PATH = SCRIPT_DIR / "fonts" / "Eunomia-Regular.ttf"


def parse_color(value: str) -> Tuple[int, int, int]:
    """Convert #RRGGBB strings into RGB tuples."""
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != 6:
        raise argparse.ArgumentTypeError(f"Color should be in #RRGGBB format, got '{value}'")
    r = int(cleaned[0:2], 16)
    g = int(cleaned[2:4], 16)
    b = int(cleaned[4:6], 16)
    return r, g, b


def load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    """Load the requested font (falling back to bundled Eunomia or system defaults)."""
    candidates = []
    if path:
        candidates.append(path)
    if str(DEFAULT_FONT_PATH) not in candidates:
        candidates.append(str(DEFAULT_FONT_PATH))
    for candidate in candidates:
        candidate_path = Path(candidate)
        if not candidate_path.exists():
            continue
        try:
            return ImageFont.truetype(str(candidate_path), size=size)
        except OSError:
            continue
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def ms_to_frames(duration_ms: int, fps: int) -> int:
    frames = round(duration_ms * fps / 1000)
    return max(frames, 1)


def ease_in_out(progress: float) -> float:
    """Slower start and finish for smoother scroll animation."""
    return progress * progress * (3 - 2 * progress)


def blend_color(source: Tuple[int, int, int], target: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    factor = max(0.0, min(1.0, factor))
    return tuple(int(source[i] + (target[i] - source[i]) * factor) for i in range(3))


@dataclass
class MessageSpec:
    text: str
    entry_ms: int
    hold_ms: int
    exit_ms: int

    @classmethod
    def from_dict(cls, payload: dict, defaults: "MessageSpec") -> "MessageSpec":
        return cls(
            text=payload.get("text", defaults.text),
            entry_ms=int(payload.get("entry_ms", defaults.entry_ms)),
            hold_ms=int(payload.get("hold_ms", defaults.hold_ms)),
            exit_ms=int(payload.get("exit_ms", defaults.exit_ms)),
        )


def load_messages(args: argparse.Namespace) -> List[MessageSpec]:
    defaults = MessageSpec(
        text="",
        entry_ms=args.entry_ms,
        hold_ms=args.hold_ms,
        exit_ms=args.exit_ms,
    )

    messages: List[MessageSpec] = []
    if args.config:
        config_path = Path(args.config)
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        config_messages = payload if isinstance(payload, list) else payload.get("messages", [])
        for entry in config_messages:
            messages.append(MessageSpec.from_dict(entry, defaults))
    for text in args.message or []:
        messages.append(MessageSpec(text=text, entry_ms=args.entry_ms, hold_ms=args.hold_ms, exit_ms=args.exit_ms))

    if not messages:
        messages.append(
            MessageSpec(
                text="Enki Ready\nLayer 0",
                entry_ms=args.entry_ms,
                hold_ms=args.hold_ms,
                exit_ms=args.exit_ms,
            )
        )
    return messages


def measure_text(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, text: str, spacing: int) -> Tuple[int, int]:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=spacing)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height


def render_frame(
    width: int,
    height: int,
    bg: Tuple[int, int, int],
    fg: Tuple[int, int, int],
    font: ImageFont.ImageFont,
    text: str,
    y_offset: int,
    spacing: int,
    accent_bar: bool,
) -> Image.Image:
    frame = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(frame)
    text_width, text_height = measure_text(draw, font, text, spacing)
    x = (width - text_width) // 2
    draw.multiline_text((x, y_offset), text, fill=fg, font=font, align="center", spacing=spacing)

    if accent_bar:
        bar_height = max(2, height // 80)
        draw.rectangle((0, 0, width, bar_height), fill=fg)
        draw.rectangle((0, height - bar_height, width, height), fill=fg)
    return frame


def generate_text_frames(
    width: int,
    height: int,
    bg: Tuple[int, int, int],
    fg: Tuple[int, int, int],
    font: ImageFont.ImageFont,
    spacing: int,
    fps: int,
    padding: int,
    accent_bar: bool,
    messages: Iterable[MessageSpec],
) -> List[Image.Image]:
    frames: List[Image.Image] = []
    for spec in messages:
        scratch = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(scratch)
        _, text_height = measure_text(draw, font, spec.text, spacing)
        center_y = (height - text_height) // 2
        entry_frames = ms_to_frames(spec.entry_ms, fps)
        exit_frames = ms_to_frames(spec.exit_ms, fps)
        hold_frames = ms_to_frames(spec.hold_ms, fps)

        start_y = -text_height - padding
        exit_y = height + padding

        for idx in range(entry_frames):
            progress = ease_in_out(idx / max(entry_frames - 1, 1))
            y = round(start_y + (center_y - start_y) * progress)
            frames.append(render_frame(width, height, bg, fg, font, spec.text, y, spacing, accent_bar))

        for _ in range(hold_frames):
            frames.append(render_frame(width, height, bg, fg, font, spec.text, center_y, spacing, accent_bar))

        for idx in range(exit_frames):
            progress = ease_in_out(idx / max(exit_frames - 1, 1))
            y = round(center_y + (exit_y - center_y) * progress)
            frames.append(render_frame(width, height, bg, fg, font, spec.text, y, spacing, accent_bar))
    return frames


def generate_logo_frames(
    width: int,
    height: int,
    bg: Tuple[int, int, int],
    fg: Tuple[int, int, int],
    secondary: Tuple[int, int, int],
    text_font: ImageFont.ImageFont,
    text: str,
    fps: int,
    args: argparse.Namespace,
) -> List[Image.Image]:
    frames: List[Image.Image] = []
    total_frames = max(1, int(args.logo_duration * fps))
    cx, cy = width // 2, height // 2
    max_radius = min(width, height) // 2 - args.logo_margin
    rings = max(1, args.logo_layers)
    growth_frac = max(0.05, min(args.logo_growth_frac, 0.95))
    for idx in range(total_frames):
        progress = idx / max(total_frames - 1, 1)
        growth_phase = min(progress / growth_frac, 1.0)
        growth_eased = ease_in_out(growth_phase)
        if progress <= growth_frac:
            rotation_phase = 0.0
        else:
            rotation_phase = (progress - growth_frac) / (1.0 - growth_frac)
        rotation_phase = min(max(rotation_phase, 0.0), 1.0)
        rotation_eased = ease_in_out(rotation_phase)
        fade_factor = 0.0
        if rotation_phase > args.logo_fade_start:
            fade_factor = min(
                (rotation_phase - args.logo_fade_start) / max(1e-6, 1.0 - args.logo_fade_start),
                1.0,
            )
        ring_color = blend_color(fg, bg, fade_factor)
        secondary_color = blend_color(secondary, bg, fade_factor)
        frame = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(frame)

        for layer in range(rings):
            radius = max_radius - layer * args.logo_ring_spacing
            if radius <= args.logo_ring_width:
                continue
            radius_effective = max(args.logo_ring_width, radius * growth_eased)
            bbox = (
                cx - radius_effective,
                cy - radius_effective,
                cx + radius_effective,
                cy + radius_effective,
            )
            base_angle = (rotation_eased * 360 * args.logo_rotations) + layer * args.logo_layer_phase
            for seg in range(args.logo_segments):
                offset = seg * (360 / args.logo_segments)
                wave = 0.55 + 0.45 * math.sin(2 * math.pi * progress + layer + seg)
                extent = args.logo_arc_span * wave
                start_angle = base_angle + offset
                draw.arc(bbox, start=start_angle, end=start_angle + extent, width=args.logo_ring_width, fill=ring_color)

        inner_radius = max_radius - rings * args.logo_ring_spacing - args.logo_ring_width
        if inner_radius > 0 and growth_phase > 0.6:
            reveal = min((growth_phase - 0.6) / 0.4, 1.0)
            inner_effective = inner_radius * reveal
            bbox = (
                cx - inner_effective,
                cy - inner_effective,
                cx + inner_effective,
                cy + inner_effective,
            )
            draw.ellipse(bbox, fill=secondary_color)
            split_angle = rotation_eased * 360 * args.logo_center_rotations
            draw.pieslice(bbox, start=split_angle, end=split_angle + 180, fill=ring_color)

        if text and rotation_phase > 0.05:
            text_image = Image.new("L", (width, height), 0)
            text_draw = ImageDraw.Draw(text_image)
            tw, th = measure_text(text_draw, text_font, text, spacing=4)
            text_draw.multiline_text(
                (cx - tw / 2, cy - th / 2),
                text,
                font=text_font,
                fill=255,
                align="center",
                spacing=4,
            )

            block_rows = max(4, args.logo_mosaic_rows)
            block_cols = max(4, args.logo_mosaic_cols)
            mosaic_progress = min(max((rotation_phase - 0.05) / 0.95, 0.0), 1.0)
            block_width = max(1, math.ceil(width / block_cols))
            block_height = max(1, math.ceil(height / block_rows))
            blocks = block_rows * block_cols
            mosaic_frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))

            indices = list(range(blocks))
            rng = random.Random(args.logo_mosaic_seed)
            rng.shuffle(indices)
            fade_window = max(0.02, args.logo_mosaic_fade)

            for order, idx_block in enumerate(indices):
                threshold = order / blocks
                block_phase = (mosaic_progress - threshold) / fade_window
                if block_phase <= 0:
                    continue
                block_alpha = min(block_phase, 1.0)
                row = idx_block // block_cols
                col = idx_block % block_cols
                left = col * block_width
                upper = row * block_height
                if left >= width or upper >= height:
                    continue
                right = min(width, left + block_width)
                lower = min(height, upper + block_height)
                region = text_image.crop((left, upper, right, lower))
                if not region.getbbox():
                    continue

                mask = ImageChops.multiply(
                    region,
                    Image.new("L", region.size, int(255 * block_alpha * rotation_phase)),
                )
                color_tile = Image.new("RGBA", region.size, (*fg, 0))
                color_tile.putalpha(mask)

                pixel_size = max(1, int(block_width * (1 - block_alpha) * 0.75))
                if pixel_size > 1:
                    small = color_tile.resize(
                        (max(1, color_tile.width // pixel_size), max(1, color_tile.height // pixel_size)),
                        resample=Image.NEAREST,
                    )
                    color_tile = small.resize(color_tile.size, resample=Image.NEAREST)
                    color_tile.putalpha(mask)

                mosaic_frame.paste(color_tile, (left, upper), color_tile)

            if mosaic_progress >= 0.98:
                sharp_mask = Image.new("L", (width, height), 0)
                sharp_draw = ImageDraw.Draw(sharp_mask)
                sharp_draw.multiline_text(
                    (cx - tw / 2, cy - th / 2),
                    text,
                    font=text_font,
                    fill=int(255 * (mosaic_progress - 0.98) / 0.02),
                    align="center",
                    spacing=4,
                )
                sharp_tile = Image.new("RGBA", (width, height), (*fg, 0))
                sharp_tile.putalpha(sharp_mask)
                mosaic_frame = Image.alpha_composite(mosaic_frame, sharp_tile)

            frame = Image.alpha_composite(frame.convert("RGBA"), mosaic_frame).convert("RGB")

        frames.append(frame)
    return frames


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate LCD-style animations for the Enki display.")
    parser.add_argument("--mode", choices=["text", "logo"], default="text", help="Animation mode to render.")
    parser.add_argument("--width", type=int, default=240, help="LCD width in pixels (default: 240 from st7789v overlay)")
    parser.add_argument("--height", type=int, default=280, help="LCD height in pixels (default: 280 from st7789v overlay)")
    parser.add_argument(
        "--bg",
        type=parse_color,
        default=parse_color("#000000"),
        help="Background color (#RRGGBB).",
    )
    parser.add_argument(
        "--fg",
        type=parse_color,
        default=parse_color("#00D8FF"),
        help="Foreground/text color (#RRGGBB).",
    )
    parser.add_argument("--font-size", type=int, default=32, help="Font size to use for text rendering.")
    parser.add_argument(
        "--font-path",
        type=str,
        default=str(DEFAULT_FONT_PATH),
        help="Custom .ttf font path (defaults to bundled Eunomia).",
    )
    parser.add_argument("--fps", type=int, default=15, help="Animation frames per second (default: 15).")
    parser.add_argument("--entry-ms", type=int, default=450, help="Milliseconds to scroll text into view.")
    parser.add_argument("--hold-ms", type=int, default=1200, help="Milliseconds to keep text centered.")
    parser.add_argument("--exit-ms", type=int, default=450, help="Milliseconds to scroll text out of view.")
    parser.add_argument("--padding", type=int, default=12, help="Extra pixels above/below text when animating.")
    parser.add_argument("--line-spacing", type=int, default=4, help="Multiline text spacing in pixels.")
    parser.add_argument("--accent-bar", action="store_true", help="Draw thin bars at the top/bottom of the frame.")
    parser.add_argument(
        "--message",
        action="append",
        help="Message to display. Repeat for multiple screens. Use '\\n' for multi-line entries.",
    )
    parser.add_argument("--config", type=str, help="Optional JSON file describing messages (list or {\"messages\": [...]})")
    parser.add_argument(
        "--output",
        type=str,
        default="gif/enki_status.gif",
        help="Path for the generated GIF. Created directories as needed.",
    )
    parser.add_argument("--logo-duration", type=float, default=4.0, help="Seconds for a full logo animation loop.")
    parser.add_argument("--logo-rotations", type=float, default=1.5, help="Number of rotations applied to the rings per loop.")
    parser.add_argument("--logo-center-rotations", type=float, default=0.75, help="Number of rotations for the center split.")
    parser.add_argument("--logo-arc-span", type=float, default=55.0, help="Degrees covered by each arc segment baseline.")
    parser.add_argument("--logo-ring-width", type=int, default=6, help="Stroke width for logo arcs.")
    parser.add_argument("--logo-ring-spacing", type=int, default=14, help="Pixel spacing between each ring.")
    parser.add_argument("--logo-layers", type=int, default=3, help="Number of concentric arc rings.")
    parser.add_argument("--logo-segments", type=int, default=8, help="Number of arc segments per ring.")
    parser.add_argument("--logo-layer-phase", type=float, default=8.0, help="Phase offset (degrees) added per ring.")
    parser.add_argument("--logo-margin", type=int, default=14, help="Padding from frame edge to outer ring.")
    parser.add_argument("--logo-text", type=str, default="enki", help="Optional center text for logo mode.")
    parser.add_argument(
        "--logo-secondary",
        type=parse_color,
        default=parse_color("#c0c0c0"),
        help="Secondary color for center fill in logo mode.",
    )
    parser.add_argument(
        "--logo-growth-frac",
        type=float,
        default=0.35,
        help="Fraction of the loop spent expanding rings before rotation begins.",
    )
    parser.add_argument(
        "--logo-fade-start",
        type=float,
        default=0.65,
        help="Rotation progress at which the logo begins to fade toward the background.",
    )
    parser.add_argument("--logo-text-size", type=int, default=80, help="Font size for the center text in logo mode.")
    parser.add_argument("--logo-mosaic-rows", type=int, default=20, help="Rows used when revealing text mosaic.")
    parser.add_argument("--logo-mosaic-cols", type=int, default=20, help="Columns used when revealing text mosaic.")
    parser.add_argument(
        "--logo-mosaic-fade",
        type=float,
        default=0.08,
        help="Progress window size controlling how long each block takes to fade in.",
    )
    parser.add_argument("--logo-mosaic-seed", type=int, default=1337, help="Seed for shuffling mosaic reveal order.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    font = load_font(args.font_path, args.font_size)
    messages = load_messages(args)

    if args.mode == "logo":
        logo_font = load_font(args.font_path, args.logo_text_size)
        frames = generate_logo_frames(
            width=args.width,
            height=args.height,
            bg=args.bg,
            fg=args.fg,
            secondary=args.logo_secondary,
            text_font=logo_font,
            text=args.logo_text,
            fps=args.fps,
            args=args,
        )
    else:
        frames = generate_text_frames(
            width=args.width,
            height=args.height,
            bg=args.bg,
            fg=args.fg,
            font=font,
            spacing=args.line_spacing,
            fps=args.fps,
            padding=args.padding,
            accent_bar=args.accent_bar,
            messages=messages,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    duration_ms = round(1000 / args.fps)
    frames[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )
    print(f"Generated {len(frames)} frames at {args.fps} fps -> {output_path}")


if __name__ == "__main__":
    main()
