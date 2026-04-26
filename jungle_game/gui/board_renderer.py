"""Board rendering for Jungle (Dou Shou Qi).

Draws terrain tiles (land, water, trap, den), grid lines, and highlights.
"""

import pygame
import math
from jungle_game.engine.board import (
    Board, COLS, ROWS, LAND, WATER, TRAP, DEN,
    WATER_SQUARES, BLUE_DEN, RED_DEN, BLUE_TRAPS, RED_TRAPS,
)


# Colors
COLOR_LAND = (139, 195, 74)         # Soft green
COLOR_LAND_ALT = (124, 179, 66)     # Slightly darker green for checkerboard
COLOR_WATER = (66, 165, 245)        # Blue
COLOR_WATER_ALT = (41, 150, 243)    # Darker blue for wave effect
COLOR_TRAP_BLUE = (170, 175, 210)   # Blue-tinted gray for Blue's traps
COLOR_TRAP_RED = (210, 175, 175)    # Red-tinted gray for Red's traps
COLOR_TRAP_MARKER = (180, 180, 180) # Lighter gray for X
COLOR_DEN_BLUE = (200, 210, 255)     # Blue-tinted for Blue's den
COLOR_DEN_RED = (255, 200, 200)     # Red-tinted for Red's den
COLOR_GRID = (60, 60, 60)          # Dark grid lines
COLOR_BORDER_OUTER = (70, 45, 20)   # Dark wood outer
COLOR_BORDER_MID = (101, 67, 33)   # Medium wood
COLOR_BORDER_INNER = (140, 100, 55) # Light wood highlight
COLOR_SELECTED = (255, 235, 59)     # Yellow glow
COLOR_LEGAL_MOVE = (76, 175, 80, 140)  # Semi-transparent green
COLOR_CAPTURE_MOVE = (220, 50, 50, 180) # Semi-transparent red for captures
COLOR_LAST_MOVE = (255, 255, 0, 60)   # Subtle yellow highlight


class BoardRenderer:
    """Renders the Jungle board terrain, grid, and highlights."""

    def __init__(self, cell_size: int = 72):
        self.cell_size = cell_size
        self.board = Board()
        self.board_width = COLS * cell_size
        self.board_height = ROWS * cell_size
        self.border_width = 12
        self.total_width = self.board_width + 2 * self.border_width
        self.total_height = self.board_height + 2 * self.border_width
        self.flipped = False

        # Pre-render the static board surface (terrain + grid)
        self._board_surface = self._render_static_board()
        self._flipped_surface = None
        self._wave_offset = 0

    def set_flipped(self, flipped: bool):
        """Toggle board flip. When flipped, rows and columns are mirrored visually."""
        if flipped != self.flipped:
            self.flipped = flipped
            self._flipped_surface = None  # Invalidate cache

    def _flip_col(self, col: int) -> int:
        """Mirror a column index when the board is flipped."""
        if self.flipped:
            return COLS - 1 - col
        return col

    def _flip_row(self, row: int) -> int:
        """Mirror a row index when the board is flipped."""
        if self.flipped:
            return ROWS - 1 - row
        return row

    def _cell_rect(self, col: int, row: int) -> pygame.Rect:
        """Get the pixel rectangle for a cell (board-local coordinates)."""
        dc = self._flip_col(col)
        dr = self._flip_row(row)
        x = self.border_width + dc * self.cell_size
        y = self.border_width + dr * self.cell_size
        return pygame.Rect(x, y, self.cell_size, self.cell_size)

    def _cell_center(self, col: int, row: int) -> tuple[int, int]:
        rect = self._cell_rect(col, row)
        return rect.centerx, rect.centery

    def board_to_pixel(self, col: int, row: int) -> tuple[int, int]:
        """Convert board coordinates to pixel center (absolute)."""
        return self._cell_center(col, row)

    def pixel_to_board(self, px: int, py: int) -> tuple[int, int] | None:
        """Convert pixel coordinates to board (col, row), or None if out of bounds."""
        bx = px - self.border_width
        by = py - self.border_width
        if bx < 0 or by < 0:
            return None
        display_col = bx // self.cell_size
        display_row = by // self.cell_size
        if 0 <= display_col < COLS and 0 <= display_row < ROWS:
            # Un-flip to get logical coordinates
            if self.flipped:
                return (COLS - 1 - display_col, ROWS - 1 - display_row)
            return (display_col, display_row)
        return None

    def _render_static_board(self) -> pygame.Surface:
        """Pre-render the static board (terrain + grid + border)."""
        surface = pygame.Surface((self.total_width, self.total_height))

        # Beveled wooden border
        surface.fill(COLOR_BORDER_OUTER)
        bw = self.border_width
        pygame.draw.rect(surface, COLOR_BORDER_MID, (2, 2, self.total_width - 4, self.total_height - 4))
        pygame.draw.rect(surface, COLOR_BORDER_INNER, (4, 4, self.total_width - 8, self.total_height - 8))
        pygame.draw.rect(surface, COLOR_BORDER_MID, (6, 6, self.total_width - 12, self.total_height - 12))
        # Inner shadow line just inside the board edge
        pygame.draw.rect(surface, COLOR_BORDER_OUTER,
                         (bw - 1, bw - 1, self.board_width + 2, self.board_height + 2), 1)

        # Draw terrain tiles
        for row in range(ROWS):
            for col in range(COLS):
                rect = self._cell_rect(col, row)
                terrain = self.board.terrain_at(col, row)

                if terrain == WATER:
                    color = COLOR_WATER if (row + col) % 2 == 0 else COLOR_WATER_ALT
                    pygame.draw.rect(surface, color, rect)
                elif terrain == TRAP:
                    if (col, row) in BLUE_TRAPS:
                        trap_color = COLOR_TRAP_BLUE
                        label_color = (100, 130, 220)
                    else:
                        trap_color = COLOR_TRAP_RED
                        label_color = (220, 100, 100)
                    pygame.draw.rect(surface, trap_color, rect)
                    # Draw X marker
                    cx, cy = rect.centerx, rect.centery
                    s = self.cell_size // 4
                    pygame.draw.line(surface, COLOR_TRAP_MARKER,
                                     (cx - s, cy - s), (cx + s, cy + s), 2)
                    pygame.draw.line(surface, COLOR_TRAP_MARKER,
                                     (cx + s, cy - s), (cx - s, cy + s), 2)
                    # Small player-colored dot in corner
                    dot_r = max(3, self.cell_size // 12)
                    pygame.draw.circle(surface, label_color,
                                       (rect.right - dot_r - 3, rect.top + dot_r + 3), dot_r)
                elif terrain == DEN:
                    if (col, row) == BLUE_DEN:
                        den_color = COLOR_DEN_BLUE
                        label, label_color = "B", (66, 133, 244)
                    else:
                        den_color = COLOR_DEN_RED
                        label, label_color = "R", (229, 57, 53)
                    pygame.draw.rect(surface, den_color, rect)
                    # Draw star marker
                    cx, cy = rect.centerx, rect.centery
                    s = self.cell_size // 4
                    points = [
                        (cx, cy - s), (cx + s // 3, cy - s // 3),
                        (cx + s, cy), (cx + s // 3, cy + s // 3),
                        (cx, cy + s), (cx - s // 3, cy + s // 3),
                        (cx - s, cy), (cx - s // 3, cy - s // 3),
                    ]
                    pygame.draw.polygon(surface, (200, 160, 0), points)
                    pygame.draw.polygon(surface, (160, 120, 0), points, 2)
                    # Player letter in corner
                    try:
                        font = pygame.font.SysFont("arial", max(10, self.cell_size // 6), bold=True)
                    except Exception:
                        font = pygame.font.Font(None, max(12, self.cell_size // 6))
                    label_surf = font.render(label, True, label_color)
                    label_rect = label_surf.get_rect(topright=(rect.right - 4, rect.top + 2))
                    surface.blit(label_surf, label_rect)
                else:
                    # Land
                    checker = (row + col) % 2 == 0
                    color = COLOR_LAND if checker else COLOR_LAND_ALT
                    pygame.draw.rect(surface, color, rect)

        # Grid lines
        for row in range(ROWS + 1):
            y = self.border_width + row * self.cell_size
            pygame.draw.line(surface, COLOR_GRID,
                             (self.border_width, y),
                             (self.border_width + self.board_width, y), 1)
        for col in range(COLS + 1):
            x = self.border_width + col * self.cell_size
            pygame.draw.line(surface, COLOR_GRID,
                             (x, self.border_width),
                             (x, self.border_width + self.board_height), 1)

        return surface

    def render(self, surface: pygame.Surface, offset: tuple[int, int],
               selected_pos: tuple[int, int] | None = None,
               legal_moves: list | None = None,
               capture_targets: set | None = None,
               last_move: tuple | None = None,
               tick: int = 0):
        """Render the board with all overlays."""
        if self.flipped:
            if self._flipped_surface is None:
                self._flipped_surface = pygame.transform.flip(
                    self._board_surface, True, True)
            surface.blit(self._flipped_surface, offset)
        else:
            surface.blit(self._board_surface, offset)

        ox, oy = offset

        # Animate water
        self._render_water_animation(surface, ox, oy, tick)

        # Last move highlight
        if last_move is not None:
            from_pos, to_pos = last_move
            for pos in (from_pos, to_pos):
                rect = self._cell_rect(pos[0], pos[1])
                rect.x += ox
                rect.y += oy
                highlight = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                highlight.fill(COLOR_LAST_MOVE)
                surface.blit(highlight, rect)

        # Selected piece highlight
        if selected_pos is not None:
            rect = self._cell_rect(selected_pos[0], selected_pos[1])
            rect.x += ox
            rect.y += oy
            pygame.draw.rect(surface, COLOR_SELECTED, rect, 3)

        # Legal move indicators
        if legal_moves:
            capture_set = capture_targets or set()
            for from_pos, to_pos in legal_moves:
                cx, cy = self._cell_center(to_pos[0], to_pos[1])
                cx += ox
                cy += oy
                dot_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                if to_pos in capture_set:
                    # Red ring for capture moves
                    radius = self.cell_size // 3
                    pygame.draw.circle(dot_surface, COLOR_CAPTURE_MOVE,
                                       (self.cell_size // 2, self.cell_size // 2), radius, 3)
                else:
                    # Green dot for normal moves
                    radius = self.cell_size // 6
                    pygame.draw.circle(dot_surface, COLOR_LEGAL_MOVE,
                                       (self.cell_size // 2, self.cell_size // 2), radius)
                surface.blit(dot_surface,
                             (cx - self.cell_size // 2, cy - self.cell_size // 2))

    def _render_water_animation(self, surface: pygame.Surface, ox: int, oy: int, tick: int):
        """Multi-wave animation on water squares."""
        self._wave_offset = (tick // 15) % 2
        for col, row in WATER_SQUARES:
            rect = self._cell_rect(col, row)
            rect.x += ox
            rect.y += oy
            if (row + col + self._wave_offset) % 2 == 0:
                pygame.draw.rect(surface, COLOR_WATER, rect)
            else:
                pygame.draw.rect(surface, COLOR_WATER_ALT, rect)
            # Multiple wavy lines using sine offsets
            wave_color = (100, 190, 255, 120)
            for i, y_frac in enumerate([0.25, 0.5, 0.75]):
                wave_y = rect.y + int(rect.height * y_frac)
                phase = (tick * 0.08 + col * 0.5 + i * 1.2)
                offset_x = int(math.sin(phase) * 3)
                wave_surf = pygame.Surface((rect.width - 8, 2), pygame.SRCALPHA)
                pygame.draw.line(wave_surf, wave_color, (0, 0), (rect.width - 8, 0), 1)
                surface.blit(wave_surf, (rect.x + 4 + offset_x, wave_y))