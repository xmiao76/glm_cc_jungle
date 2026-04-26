"""Piece rendering for Jungle (Dou Shou Qi).

Each piece is a circular token with:
- A colored fill (blue/red) with gradient highlight and border
- A recognizable animal drawing in the upper portion
- The animal short name in bold text below the drawing
- A small rank number in the corner

Pieces are pre-rendered to offscreen surfaces at init for performance.
"""

import pygame
import math
from jungle_game.engine.pieces import Piece, PieceType, Player


# Colors for pieces
COLOR_BLUE_FILL = (55, 120, 220)
COLOR_BLUE_BORDER = (25, 60, 150)
COLOR_BLUE_DARK = (18, 45, 110)
COLOR_RED_FILL = (220, 55, 45)
COLOR_RED_BORDER = (150, 25, 20)
COLOR_RED_DARK = (110, 18, 15)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_SELECTED = (255, 235, 59)

# Extra drawing colors
COLOR_PINK = (255, 170, 170)
COLOR_DARK_PINK = (200, 120, 120)
COLOR_BEIGE = (245, 230, 200)
COLOR_GRAY = (160, 160, 160)
COLOR_DARK_GRAY = (80, 80, 80)
COLOR_ORANGE = (240, 160, 50)
COLOR_DARK_ORANGE = (180, 100, 20)
COLOR_LIGHT_BLUE = (150, 200, 255)

# Display names for each piece — short and recognizable
PIECE_DISPLAY_NAMES = {
    PieceType.RAT: "Rat",
    PieceType.CAT: "Cat",
    PieceType.DOG: "Dog",
    PieceType.WOLF: "Wlf",
    PieceType.LEOPARD: "Lpd",
    PieceType.TIGER: "Tgr",
    PieceType.LION: "Lio",
    PieceType.ELEPHANT: "Elt",
}


# ---------- Animal drawing functions ----------
# Each draws a simplified, distinctive animal icon centered at (cx, cy)
# into a circle of radius `r` (the piece token radius).
# The icon is drawn in the UPPER half of the piece to leave room for the name below.


def _draw_rat(surf, cx, cy, r):
    """Rat: round body, big round ears, long curling tail, prominent eye."""
    s = r * 2  # scale factor based on radius
    # Tail (drawn first, behind body)
    pygame.draw.arc(surf, COLOR_WHITE,
                    (cx - int(s * 0.45), cy - int(s * 0.05), int(s * 0.3), int(s * 0.35)),
                    -0.5, 2.8, 3)
    # Body
    pygame.draw.ellipse(surf, COLOR_WHITE,
                        (cx - int(s * 0.22), cy - int(s * 0.10), int(s * 0.35), int(s * 0.25)))
    # Head
    pygame.draw.circle(surf, COLOR_WHITE, (cx + int(s * 0.08), cy - int(s * 0.14)), int(s * 0.17))
    # Ears (big and round)
    pygame.draw.circle(surf, COLOR_WHITE, (cx - int(s * 0.02), cy - int(s * 0.28)), int(s * 0.09))
    pygame.draw.circle(surf, COLOR_PINK, (cx - int(s * 0.02), cy - int(s * 0.28)), int(s * 0.05))
    pygame.draw.circle(surf, COLOR_WHITE, (cx + int(s * 0.18), cy - int(s * 0.28)), int(s * 0.09))
    pygame.draw.circle(surf, COLOR_PINK, (cx + int(s * 0.18), cy - int(s * 0.28)), int(s * 0.05))
    # Eye
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.14), cy - int(s * 0.16)), max(2, int(s * 0.04)))
    pygame.draw.circle(surf, COLOR_WHITE, (cx + int(s * 0.15), cy - int(s * 0.17)), max(1, int(s * 0.015)))
    # Nose
    pygame.draw.circle(surf, COLOR_DARK_PINK, (cx + int(s * 0.22), cy - int(s * 0.10)), max(1, int(s * 0.025)))


def _draw_cat(surf, cx, cy, r):
    """Cat: triangular ears, whiskers, curved tail."""
    s = r * 2
    # Tail
    pygame.draw.arc(surf, COLOR_WHITE,
                    (cx + int(s * 0.05), cy + int(s * 0.0), int(s * 0.25), int(s * 0.3)),
                    -0.3, 2.5, 3)
    # Body
    pygame.draw.ellipse(surf, COLOR_WHITE,
                        (cx - int(s * 0.18), cy - int(s * 0.02), int(s * 0.32), int(s * 0.22)))
    # Head
    pygame.draw.circle(surf, COLOR_WHITE, (cx, cy - int(s * 0.14)), int(s * 0.17))
    # Pointed ears (triangles) — the signature cat feature
    pygame.draw.polygon(surf, COLOR_WHITE, [
        (cx - int(s * 0.14), cy - int(s * 0.20)),
        (cx - int(s * 0.10), cy - int(s * 0.40)),
        (cx - int(s * 0.02), cy - int(s * 0.20)),
    ])
    pygame.draw.polygon(surf, COLOR_PINK, [
        (cx - int(s * 0.12), cy - int(s * 0.22)),
        (cx - int(s * 0.10), cy - int(s * 0.35)),
        (cx - int(s * 0.04), cy - int(s * 0.22)),
    ])
    pygame.draw.polygon(surf, COLOR_WHITE, [
        (cx + int(s * 0.02), cy - int(s * 0.20)),
        (cx + int(s * 0.10), cy - int(s * 0.40)),
        (cx + int(s * 0.14), cy - int(s * 0.20)),
    ])
    pygame.draw.polygon(surf, COLOR_PINK, [
        (cx + int(s * 0.04), cy - int(s * 0.22)),
        (cx + int(s * 0.10), cy - int(s * 0.35)),
        (cx + int(s * 0.12), cy - int(s * 0.22)),
    ])
    # Eyes
    pygame.draw.circle(surf, (80, 180, 80), (cx - int(s * 0.06), cy - int(s * 0.15)), max(2, int(s * 0.035)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx - int(s * 0.06), cy - int(s * 0.15)), max(1, int(s * 0.018)))
    pygame.draw.circle(surf, (80, 180, 80), (cx + int(s * 0.06), cy - int(s * 0.15)), max(2, int(s * 0.035)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.06), cy - int(s * 0.15)), max(1, int(s * 0.018)))
    # Nose
    pygame.draw.polygon(surf, COLOR_PINK, [
        (cx, cy - int(s * 0.07)),
        (cx - int(s * 0.025), cy - int(s * 0.05)),
        (cx + int(s * 0.025), cy - int(s * 0.05)),
    ])
    # Whiskers
    for dy in [-1, 0, 1]:
        pygame.draw.line(surf, COLOR_DARK_GRAY,
                         (cx - int(s * 0.07), cy - int(s * 0.06) + dy * int(s * 0.015)),
                         (cx - int(s * 0.25), cy - int(s * 0.08) + dy * int(s * 0.025)), 1)
        pygame.draw.line(surf, COLOR_DARK_GRAY,
                         (cx + int(s * 0.07), cy - int(s * 0.06) + dy * int(s * 0.015)),
                         (cx + int(s * 0.25), cy - int(s * 0.08) + dy * int(s * 0.025)), 1)


def _draw_dog(surf, cx, cy, r):
    """Dog: floppy ears, happy face with tongue, wagging tail."""
    s = r * 2
    # Tail (upward)
    pygame.draw.arc(surf, COLOR_WHITE,
                    (cx + int(s * 0.10), cy - int(s * 0.15), int(s * 0.2), int(s * 0.25)),
                    -0.5, 2.5, 3)
    # Body
    pygame.draw.ellipse(surf, COLOR_WHITE,
                        (cx - int(s * 0.20), cy + int(s * 0.0), int(s * 0.35), int(s * 0.22)))
    # Head
    pygame.draw.circle(surf, COLOR_WHITE, (cx, cy - int(s * 0.12)), int(s * 0.18))
    # Floppy ears (signature dog feature)
    pygame.draw.ellipse(surf, COLOR_BEIGE,
                        (cx - int(s * 0.24), cy - int(s * 0.18), int(s * 0.14), int(s * 0.22)))
    pygame.draw.ellipse(surf, COLOR_BEIGE,
                        (cx + int(s * 0.10), cy - int(s * 0.18), int(s * 0.14), int(s * 0.22)))
    # Eyes (happy, round)
    pygame.draw.circle(surf, COLOR_BLACK, (cx - int(s * 0.06), cy - int(s * 0.15)), max(2, int(s * 0.03)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.06), cy - int(s * 0.15)), max(2, int(s * 0.03)))
    # Nose
    pygame.draw.ellipse(surf, COLOR_DARK_GRAY,
                        (cx - int(s * 0.03), cy - int(s * 0.07), int(s * 0.06), int(s * 0.04)))
    # Tongue (sticking out — cute dog feature)
    pygame.draw.ellipse(surf, COLOR_PINK,
                        (cx - int(s * 0.02), cy - int(s * 0.03), int(s * 0.04), int(s * 0.07)))


def _draw_wolf(surf, cx, cy, r):
    """Wolf: sharp pointed ears, angular snout, intense eyes, bushy tail."""
    s = r * 2
    # Bushy tail (up)
    pygame.draw.polygon(surf, COLOR_WHITE, [
        (cx - int(s * 0.20), cy + int(s * 0.08)),
        (cx - int(s * 0.30), cy - int(s * 0.15)),
        (cx - int(s * 0.22), cy - int(s * 0.25)),
        (cx - int(s * 0.12), cy - int(s * 0.10)),
    ])
    # Body (lean)
    pygame.draw.ellipse(surf, COLOR_WHITE,
                        (cx - int(s * 0.22), cy + int(s * 0.02), int(s * 0.38), int(s * 0.22)))
    # Head
    pygame.draw.circle(surf, COLOR_WHITE, (cx, cy - int(s * 0.12)), int(s * 0.16))
    # Pointed ears (wolf feature)
    pygame.draw.polygon(surf, COLOR_GRAY, [
        (cx - int(s * 0.10), cy - int(s * 0.22)),
        (cx - int(s * 0.14), cy - int(s * 0.44)),
        (cx - int(s * 0.01), cy - int(s * 0.24)),
    ])
    pygame.draw.polygon(surf, COLOR_GRAY, [
        (cx + int(s * 0.01), cy - int(s * 0.24)),
        (cx + int(s * 0.14), cy - int(s * 0.44)),
        (cx + int(s * 0.10), cy - int(s * 0.22)),
    ])
    # Snout (pointed)
    pygame.draw.polygon(surf, COLOR_BEIGE, [
        (cx - int(s * 0.04), cy - int(s * 0.06)),
        (cx + int(s * 0.20), cy - int(s * 0.06)),
        (cx + int(s * 0.20), cy + int(s * 0.02)),
        (cx - int(s * 0.04), cy + int(s * 0.02)),
    ])
    # Eyes (intense, narrow)
    pygame.draw.ellipse(surf, (220, 200, 50),
                        (cx - int(s * 0.08), cy - int(s * 0.18), int(s * 0.06), int(s * 0.04)))
    pygame.draw.ellipse(surf, (220, 200, 50),
                        (cx + int(s * 0.04), cy - int(s * 0.18), int(s * 0.06), int(s * 0.04)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx - int(s * 0.05), cy - int(s * 0.16)), max(1, int(s * 0.015)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.07), cy - int(s * 0.16)), max(1, int(s * 0.015)))
    # Nose
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.16), cy - int(s * 0.02)), max(2, int(s * 0.03)))


def _draw_leopard(surf, cx, cy, r):
    """Leopard: spotted body, long curved tail, round ears."""
    s = r * 2
    # Long curved tail
    pygame.draw.arc(surf, COLOR_WHITE,
                    (cx - int(s * 0.40), cy - int(s * 0.05), int(s * 0.25), int(s * 0.30)),
                    0.5, 2.8, 3)
    # Body (sleek)
    pygame.draw.ellipse(surf, COLOR_ORANGE,
                        (cx - int(s * 0.22), cy + int(s * 0.04), int(s * 0.38), int(s * 0.22)))
    # Rosette spots on body (leopard's signature)
    spots = [(-0.12, 0.10), (0.02, 0.12), (-0.04, 0.16), (0.10, 0.09), (-0.18, 0.13)]
    for dx, dy in spots:
        pygame.draw.circle(surf, COLOR_DARK_ORANGE, (cx + int(s * dx), cy + int(s * dy)), max(2, int(s * 0.04)))
        pygame.draw.circle(surf, COLOR_ORANGE, (cx + int(s * dx), cy + int(s * dy)), max(1, int(s * 0.02)))
    # Head
    pygame.draw.circle(surf, COLOR_ORANGE, (cx + int(s * 0.06), cy - int(s * 0.10)), int(s * 0.15))
    # Small round ears
    pygame.draw.circle(surf, COLOR_ORANGE, (cx - int(s * 0.04), cy - int(s * 0.22)), int(s * 0.06))
    pygame.draw.circle(surf, COLOR_PINK, (cx - int(s * 0.04), cy - int(s * 0.22)), int(s * 0.03))
    pygame.draw.circle(surf, COLOR_ORANGE, (cx + int(s * 0.16), cy - int(s * 0.22)), int(s * 0.06))
    pygame.draw.circle(surf, COLOR_PINK, (cx + int(s * 0.16), cy - int(s * 0.22)), int(s * 0.03))
    # Spots on head
    pygame.draw.circle(surf, COLOR_DARK_ORANGE, (cx - int(s * 0.02), cy - int(s * 0.14)), max(1, int(s * 0.025)))
    pygame.draw.circle(surf, COLOR_DARK_ORANGE, (cx + int(s * 0.14), cy - int(s * 0.14)), max(1, int(s * 0.025)))
    # Eyes
    pygame.draw.circle(surf, (200, 200, 50), (cx + int(s * 0.02), cy - int(s * 0.12)), max(2, int(s * 0.03)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.02), cy - int(s * 0.12)), max(1, int(s * 0.015)))
    # Nose
    pygame.draw.polygon(surf, COLOR_BLACK, [
        (cx + int(s * 0.14), cy - int(s * 0.06)),
        (cx + int(s * 0.11), cy - int(s * 0.04)),
        (cx + int(s * 0.17), cy - int(s * 0.04)),
    ])


def _draw_tiger(surf, cx, cy, r):
    """Tiger: bold orange body with black stripes, round face, thick tail."""
    s = r * 2
    # Thick tail
    pygame.draw.arc(surf, COLOR_ORANGE,
                    (cx - int(s * 0.35), cy - int(s * 0.10), int(s * 0.22), int(s * 0.30)),
                    0.3, 2.5, 4)
    # Body (large, powerful, orange)
    pygame.draw.ellipse(surf, COLOR_ORANGE,
                        (cx - int(s * 0.22), cy + int(s * 0.04), int(s * 0.38), int(s * 0.24)))
    # Body stripes (tiger's signature)
    for dx in [-0.10, 0.04, 0.18]:
        x = cx + int(s * dx)
        pygame.draw.line(surf, COLOR_BLACK, (x, cy + int(s * 0.08)), (x, cy + int(s * 0.20)), 3)
    # White belly
    pygame.draw.ellipse(surf, COLOR_WHITE,
                        (cx - int(s * 0.08), cy + int(s * 0.12), int(s * 0.16), int(s * 0.10)))
    # Head (round, large)
    pygame.draw.circle(surf, COLOR_ORANGE, (cx + int(s * 0.04), cy - int(s * 0.08)), int(s * 0.19))
    # White cheeks
    pygame.draw.circle(surf, COLOR_WHITE, (cx - int(s * 0.04), cy - int(s * 0.02)), int(s * 0.07))
    pygame.draw.circle(surf, COLOR_WHITE, (cx + int(s * 0.12), cy - int(s * 0.02)), int(s * 0.07))
    # Round ears
    pygame.draw.circle(surf, COLOR_ORANGE, (cx - int(s * 0.10), cy - int(s * 0.22)), int(s * 0.07))
    pygame.draw.circle(surf, COLOR_ORANGE, (cx + int(s * 0.18), cy - int(s * 0.22)), int(s * 0.07))
    # Face stripes
    pygame.draw.line(surf, COLOR_BLACK, (cx - int(s * 0.08), cy - int(s * 0.12)),
                     (cx - int(s * 0.18), cy - int(s * 0.08)), 2)
    pygame.draw.line(surf, COLOR_BLACK, (cx + int(s * 0.16), cy - int(s * 0.12)),
                     (cx + int(s * 0.26), cy - int(s * 0.08)), 2)
    # Eyes
    pygame.draw.circle(surf, (200, 200, 50), (cx, cy - int(s * 0.10)), max(2, int(s * 0.035)))
    pygame.draw.circle(surf, (200, 200, 50), (cx + int(s * 0.10), cy - int(s * 0.10)), max(2, int(s * 0.035)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx, cy - int(s * 0.10)), max(1, int(s * 0.018)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.10), cy - int(s * 0.10)), max(1, int(s * 0.018)))
    # Nose
    pygame.draw.polygon(surf, COLOR_PINK, [
        (cx + int(s * 0.05), cy - int(s * 0.03)),
        (cx + int(s * 0.02), cy + int(s * 0.0)),
        (cx + int(s * 0.08), cy + int(s * 0.0)),
    ])


def _draw_lion(surf, cx, cy, r):
    """Lion: large radiating mane, regal face, tufted tail."""
    s = r * 2
    # Tufted tail
    pygame.draw.line(surf, COLOR_ORANGE, (cx - int(s * 0.18), cy + int(s * 0.12)),
                     (cx - int(s * 0.28), cy - int(s * 0.05)), 3)
    pygame.draw.circle(surf, COLOR_DARK_ORANGE, (cx - int(s * 0.30), cy - int(s * 0.08)), int(s * 0.06))
    # Body
    pygame.draw.ellipse(surf, COLOR_ORANGE,
                        (cx - int(s * 0.20), cy + int(s * 0.08), int(s * 0.36), int(s * 0.22)))
    # Mane — the signature feature (large circle with radial lines)
    mane_r = int(s * 0.24)
    pygame.draw.circle(surf, COLOR_DARK_ORANGE, (cx + int(s * 0.02), cy - int(s * 0.06)), mane_r)
    # Mane texture
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        ix = cx + int(s * 0.02) + int((mane_r - int(s * 0.05)) * math.cos(rad))
        iy = cy - int(s * 0.06) + int((mane_r - int(s * 0.05)) * math.sin(rad))
        ex = cx + int(s * 0.02) + int(mane_r * math.cos(rad))
        ey = cy - int(s * 0.06) + int(mane_r * math.sin(rad))
        pygame.draw.line(surf, COLOR_ORANGE, (ix, iy), (ex, ey), 3)
    # Head (inside mane)
    pygame.draw.circle(surf, COLOR_BEIGE, (cx + int(s * 0.02), cy - int(s * 0.06)), int(s * 0.12))
    # Eyes
    pygame.draw.circle(surf, (200, 200, 50), (cx - int(s * 0.03), cy - int(s * 0.09)), max(2, int(s * 0.03)))
    pygame.draw.circle(surf, (200, 200, 50), (cx + int(s * 0.07), cy - int(s * 0.09)), max(2, int(s * 0.03)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx - int(s * 0.03), cy - int(s * 0.09)), max(1, int(s * 0.015)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.07), cy - int(s * 0.09)), max(1, int(s * 0.015)))
    # Nose
    pygame.draw.polygon(surf, COLOR_DARK_PINK, [
        (cx + int(s * 0.02), cy - int(s * 0.03)),
        (cx - int(s * 0.02), cy + int(s * 0.0)),
        (cx + int(s * 0.06), cy + int(s * 0.0)),
    ])


def _draw_elephant(surf, cx, cy, r):
    """Elephant: large round body, long curved trunk, big ears, tusks."""
    s = r * 2
    # Body (very large)
    pygame.draw.ellipse(surf, COLOR_GRAY,
                        (cx - int(s * 0.22), cy + int(s * 0.06), int(s * 0.40), int(s * 0.28)))
    # Head
    pygame.draw.circle(surf, COLOR_GRAY, (cx, cy - int(s * 0.08)), int(s * 0.19))
    # Big ears (elephant signature)
    pygame.draw.ellipse(surf, COLOR_GRAY,
                        (cx - int(s * 0.25), cy - int(s * 0.22), int(s * 0.16), int(s * 0.22)))
    pygame.draw.ellipse(surf, COLOR_PINK,
                        (cx - int(s * 0.23), cy - int(s * 0.18), int(s * 0.12), int(s * 0.16)))
    pygame.draw.ellipse(surf, COLOR_GRAY,
                        (cx + int(s * 0.11), cy - int(s * 0.22), int(s * 0.16), int(s * 0.22)))
    pygame.draw.ellipse(surf, COLOR_PINK,
                        (cx + int(s * 0.13), cy - int(s * 0.18), int(s * 0.12), int(s * 0.16)))
    # Trunk (curving down — the most distinctive feature)
    trunk_pts = [
        (cx + int(s * 0.04), cy + int(s * 0.02)),
        (cx + int(s * 0.12), cy + int(s * 0.10)),
        (cx + int(s * 0.10), cy + int(s * 0.18)),
        (cx + int(s * 0.04), cy + int(s * 0.22)),
        (cx - int(s * 0.02), cy + int(s * 0.18)),
    ]
    pygame.draw.polygon(surf, COLOR_GRAY, trunk_pts)
    pygame.draw.lines(surf, COLOR_DARK_GRAY, False, trunk_pts, 2)
    # Tusks
    pygame.draw.arc(surf, COLOR_WHITE,
                    (cx - int(s * 0.02), cy + int(s * 0.0), int(s * 0.10), int(s * 0.16)),
                    -0.8, 0.5, 3)
    pygame.draw.arc(surf, COLOR_WHITE,
                    (cx + int(s * 0.06), cy + int(s * 0.0), int(s * 0.10), int(s * 0.16)),
                    -0.8, 0.5, 3)
    # Eyes (small, wise)
    pygame.draw.circle(surf, COLOR_BLACK, (cx - int(s * 0.05), cy - int(s * 0.12)), max(2, int(s * 0.03)))
    pygame.draw.circle(surf, COLOR_WHITE, (cx - int(s * 0.055), cy - int(s * 0.13)), max(1, int(s * 0.01)))
    pygame.draw.circle(surf, COLOR_BLACK, (cx + int(s * 0.07), cy - int(s * 0.12)), max(2, int(s * 0.03)))
    pygame.draw.circle(surf, COLOR_WHITE, (cx + int(s * 0.065), cy - int(s * 0.13)), max(1, int(s * 0.01)))


# Mapping from piece type to draw function
DRAW_FUNCTIONS = {
    PieceType.RAT: _draw_rat,
    PieceType.CAT: _draw_cat,
    PieceType.DOG: _draw_dog,
    PieceType.WOLF: _draw_wolf,
    PieceType.LEOPARD: _draw_leopard,
    PieceType.TIGER: _draw_tiger,
    PieceType.LION: _draw_lion,
    PieceType.ELEPHANT: _draw_elephant,
}


class PieceRenderer:
    """Pre-renders and caches piece surfaces for efficient drawing."""

    def __init__(self, cell_size: int = 72):
        self.cell_size = cell_size
        self.piece_radius = int(cell_size * 0.42)
        self._surfaces: dict[tuple[PieceType, Player], pygame.Surface] = {}
        self._selected_surfaces: dict[tuple[PieceType, Player], pygame.Surface] = {}
        self._name_font = None
        self._rank_font = None
        self._prerender_all()

    def _init_fonts(self):
        """Initialize fonts for piece labels. Called lazily."""
        if self._name_font is not None:
            return
        # Name font: sized to fit inside the piece circle below the drawing
        name_size = max(9, int(self.cell_size * 0.17))
        rank_size = max(8, int(self.cell_size * 0.14))
        try:
            self._name_font = pygame.font.SysFont("arial", name_size, bold=True)
        except Exception:
            self._name_font = pygame.font.Font(None, name_size)
        try:
            self._rank_font = pygame.font.SysFont("arial", rank_size, bold=True)
        except Exception:
            self._rank_font = pygame.font.Font(None, rank_size)

    def _render_piece(self, piece_type: PieceType, player: Player,
                      selected: bool = False) -> pygame.Surface:
        """Render a single piece to an offscreen surface.

        Layout: animal drawing in upper portion, name label at bottom.
        """
        self._init_fonts()

        size = self.cell_size
        if selected:
            size = int(self.cell_size * 1.08)

        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        r = self.piece_radius

        # Fill color
        fill = COLOR_BLUE_FILL if player == Player.BLUE else COLOR_RED_FILL
        border = COLOR_BLUE_BORDER if player == Player.BLUE else COLOR_RED_BORDER
        dark = COLOR_BLUE_DARK if player == Player.BLUE else COLOR_RED_DARK

        # Glow for selected
        if selected:
            glow_r = int(r * 1.15)
            pygame.draw.circle(surface, COLOR_SELECTED, (cx, cy), glow_r + 3)

        # Main circle with gradient-like effect
        pygame.draw.circle(surface, fill, (cx, cy), r)
        highlight_r = int(r * 0.7)
        highlight_color = tuple(min(255, c + 40) for c in fill)
        pygame.draw.circle(surface, highlight_color,
                           (cx - int(r * 0.1), cy - int(r * 0.1)),
                           highlight_r)
        pygame.draw.circle(surface, border, (cx, cy), r, 3)

        # Draw animal icon (shifted up to make room for name)
        draw_fn = DRAW_FUNCTIONS.get(piece_type)
        if draw_fn:
            draw_fn(surface, cx, cy - int(size * 0.06), r)

        # Animal name at bottom of circle
        name = PIECE_DISPLAY_NAMES[piece_type]
        name_surf = self._name_font.render(name, True, COLOR_WHITE)
        name_shadow = self._name_font.render(name, True, dark)
        name_rect = name_surf.get_rect(centerx=cx, bottom=cy + r - 3)
        shadow_rect = name_rect.move(1, 1)
        surface.blit(name_shadow, shadow_rect)
        surface.blit(name_surf, name_rect)

        # Rank number (small, top-left corner)
        rank_text = str(int(piece_type))
        rank_surf = self._rank_font.render(rank_text, True, COLOR_WHITE)
        rank_shadow = self._rank_font.render(rank_text, True, dark)
        rank_rect = rank_surf.get_rect(
            left=cx - r + 5,
            top=cy - r + 3
        )
        surface.blit(rank_shadow, rank_rect.move(1, 1))
        surface.blit(rank_surf, rank_rect)

        return surface

    def _prerender_all(self):
        """Pre-render all piece variants."""
        for ptype in PieceType:
            for player in Player:
                self._surfaces[(ptype, player)] = self._render_piece(ptype, player, False)
                self._selected_surfaces[(ptype, player)] = self._render_piece(ptype, player, True)

    def get_surface(self, piece_type: PieceType, player: Player,
                    selected: bool = False) -> pygame.Surface:
        """Get a pre-rendered piece surface."""
        if selected:
            return self._selected_surfaces[(piece_type, player)]
        return self._surfaces[(piece_type, player)]

    def render_piece(self, surface: pygame.Surface, piece: Piece,
                     cx: int, cy: int, selected: bool = False,
                     trapped: bool = False):
        """Draw a piece centered at (cx, cy) on the target surface."""
        piece_surf = self.get_surface(piece.piece_type, piece.player, selected)
        rect = piece_surf.get_rect(center=(cx, cy))
        surface.blit(piece_surf, rect)
        # Draw trapped indicator: red ring + dim overlay
        if trapped:
            r = self.piece_radius
            trapped_surf = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
            tc = r + 3
            # Red ring
            pygame.draw.circle(trapped_surf, (255, 50, 50, 160), (tc, tc), r + 2, 3)
            # Semi-transparent dim
            pygame.draw.circle(trapped_surf, (0, 0, 0, 60), (tc, tc), r)
            surface.blit(trapped_surf, (cx - tc, cy - tc))

    def render_captured(self, surface: pygame.Surface, piece: Piece,
                        x: int, y: int, scale: float = 0.5):
        """Draw a small captured piece indicator."""
        small_surf = pygame.transform.smoothscale(
            self._surfaces[(piece.piece_type, piece.player)],
            (int(self.cell_size * scale), int(self.cell_size * scale))
        )
        rect = small_surf.get_rect(topleft=(x, y))
        surface.blit(small_surf, rect)