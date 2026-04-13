"""Board rendering for Jungle (Dou Shou Qi).

Draws terrain tiles (land, water, trap, den), grid lines, and highlights.
"""

import pygame
from jungle_game.engine.board import (
    Board, COLS, ROWS, LAND, WATER, TRAP, DEN,
    WATER_SQUARES, BLUE_DEN, RED_DEN, BLUE_TRAPS, RED_TRAPS,
)
from jungle_game.engine.pieces import Player


# Colors
COLOR_LAND = (139, 195, 74)         # Soft green
COLOR_LAND_ALT = (124, 179, 66)     # Slightly darker green for checkerboard
COLOR_WATER = (66, 165, 245)        # Blue
COLOR_WATER_ALT = (41, 150, 243)    # Darker blue for wave effect
COLOR_TRAP = (120, 120, 120)        # Dark gray/stone
COLOR_TRAP_MARKER = (180, 180, 180) # Lighter gray for X
COLOR_DEN_BLUE = (255, 215, 0)      # Gold
COLOR_DEN_RED = (255, 215, 0)       # Gold
COLOR_GRID = (60, 60, 60)          # Dark grid lines
COLOR_BOARD_BORDER = (101, 67, 33)  # Wood brown
COLOR_SELECTED = (255, 235, 59)     # Yellow glow
COLOR_LEGAL_MOVE = (76, 175, 80, 140)  # Semi-transparent green
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

        # Pre-render the static board surface (terrain + grid)
        self._board_surface = self._render_static_board()
        self._wave_offset = 0

    def _cell_rect(self, col: int, row: int) -> pygame.Rect:
        """Get the pixel rectangle for a cell (board-local coordinates)."""
        x = self.border_width + col * self.cell_size
        y = self.border_width + row * self.cell_size
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
        col = bx // self.cell_size
        row = by // self.cell_size
        if 0 <= col < COLS and 0 <= row < ROWS:
            return (col, row)
        return None

    def _render_static_board(self) -> pygame.Surface:
        """Pre-render the static board (terrain + grid + border)."""
        surface = pygame.Surface((self.total_width, self.total_height))

        # Border (wooden frame)
        surface.fill(COLOR_BOARD_BORDER)

        # Draw terrain tiles
        for row in range(ROWS):
            for col in range(COLS):
                rect = self._cell_rect(col, row)
                terrain = self.board.terrain_at(col, row)

                if terrain == WATER:
                    # Water squares get animated separately, use base color
                    color = COLOR_WATER if (row + col) % 2 == 0 else COLOR_WATER_ALT
                    pygame.draw.rect(surface, color, rect)
                elif terrain == TRAP:
                    pygame.draw.rect(surface, COLOR_TRAP, rect)
                    # Draw X marker
                    cx, cy = rect.centerx, rect.centery
                    s = self.cell_size // 4
                    pygame.draw.line(surface, COLOR_TRAP_MARKER,
                                     (cx - s, cy - s), (cx + s, cy + s), 2)
                    pygame.draw.line(surface, COLOR_TRAP_MARKER,
                                     (cx + s, cy - s), (cx - s, cy + s), 2)
                elif terrain == DEN:
                    pygame.draw.rect(surface, COLOR_DEN_BLUE, rect)
                    # Draw star marker
                    cx, cy = rect.centerx, rect.centery
                    s = self.cell_size // 4
                    # Simple 4-point star
                    points = [
                        (cx, cy - s), (cx + s // 3, cy - s // 3),
                        (cx + s, cy), (cx + s // 3, cy + s // 3),
                        (cx, cy + s), (cx - s // 3, cy + s // 3),
                        (cx - s, cy), (cx - s // 3, cy - s // 3),
                    ]
                    pygame.draw.polygon(surface, (200, 160, 0), points)
                    pygame.draw.polygon(surface, (160, 120, 0), points, 2)
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
               last_move: tuple | None = None,
               tick: int = 0):
        """Render the board with all overlays."""
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
            for from_pos, to_pos in legal_moves:
                cx, cy = self._cell_center(to_pos[0], to_pos[1])
                cx += ox
                cy += oy
                # Draw a semi-transparent green dot
                dot_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                radius = self.cell_size // 6
                pygame.draw.circle(dot_surface, COLOR_LEGAL_MOVE,
                                   (self.cell_size // 2, self.cell_size // 2), radius)
                surface.blit(dot_surface,
                             (cx - self.cell_size // 2, cy - self.cell_size // 2))

    def _render_water_animation(self, surface: pygame.Surface, ox: int, oy: int, tick: int):
        """Subtle wave animation on water squares."""
        self._wave_offset = (tick // 15) % 2  # Toggle every 15 ticks
        for col, row in WATER_SQUARES:
            rect = self._cell_rect(col, row)
            rect.x += ox
            rect.y += oy
            # Alternate between two shades for wave effect
            if (row + col + self._wave_offset) % 2 == 0:
                pygame.draw.rect(surface, COLOR_WATER, rect)
            else:
                pygame.draw.rect(surface, COLOR_WATER_ALT, rect)
            # Subtle wave line
            wave_y = rect.y + rect.height // 2 + (2 if self._wave_offset else -2)
            pygame.draw.line(surface, (100, 190, 255),
                             (rect.x + 4, wave_y), (rect.x + rect.width - 4, wave_y), 1)