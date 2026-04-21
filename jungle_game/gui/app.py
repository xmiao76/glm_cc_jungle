"""Main application for Jungle (Dou Shou Qi) — Pygame game loop and input handling."""

import pygame
import sys
import ctypes
import threading
import time

from jungle_game.engine.game import GameState
from jungle_game.engine.pieces import Player
from jungle_game.engine.ai import find_best_move, clear_tt
from jungle_game.engine.rules import generate_legal_moves
from jungle_game.engine.board import COLS, ROWS
from jungle_game.gui.board_renderer import BoardRenderer
from jungle_game.gui.piece_renderer import PieceRenderer
from jungle_game.gui.ui_overlay import UIOverlay

# Window settings
SIDEBAR_WIDTH = 200
BORDER_WIDTH = 12
FPS = 60
AI_TIME_LIMIT_MS = 1500
AI_VS_AI_DELAY_MS = 500  # Delay between AI moves in AI-vs-AI mode
TITLE_BAR_HEIGHT = 40    # Windows title bar
SAFETY_PAD = 10          # Extra safety margin so window isn't edge-to-edge


def _get_work_area() -> tuple[int, int]:
    """Get the Windows work area (screen minus taskbar) in pixels.

    Returns (width, height). Falls back to pygame display info on failure.
    """
    try:
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                         ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        rect = RECT()
        # SPI_GETWORKAREA = 0x30
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0)
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    # Fallback: use pygame display info (full screen, not work area)
    try:
        info = pygame.display.Info()
        return info.current_w, info.current_h
    except Exception:
        return 0, 0


def _compute_cell_size() -> int:
    """Compute the largest cell_size that fits the screen.

    Uses the Windows work area (excludes taskbar) and reserves room for
    the window title bar. Falls back to 72 if detection fails.
    """
    work_w, work_h = _get_work_area()
    if work_w <= 0 or work_h <= 0:
        return 72

    # Available space for the Pygame window content
    available_h = work_h - TITLE_BAR_HEIGHT - SAFETY_PAD
    available_w = work_w - SAFETY_PAD

    # Height constraint: (ROWS * cell) + 2 * border <= available_h
    max_from_h = (available_h - 2 * BORDER_WIDTH) // ROWS
    # Width constraint: (COLS * cell) + 2 * border + sidebar <= available_w
    max_from_w = (available_w - 2 * BORDER_WIDTH - SIDEBAR_WIDTH) // COLS
    cell = min(max_from_h, max_from_w)
    return max(40, min(cell, 72))


class CaptureAnimation:
    """Brief flash/fade animation when a piece is captured."""

    def __init__(self, col: int, row: int, duration_frames: int = 20):
        self.col = col
        self.row = row
        self.duration = duration_frames
        self.frame = 0
        self.active = True

    def update(self):
        self.frame += 1
        if self.frame >= self.duration:
            self.active = False

    @property
    def alpha(self) -> int:
        """Fading alpha from 255 to 0."""
        progress = self.frame / self.duration
        return int(255 * (1 - progress))


class JungleApp:
    """Main Jungle game application."""

    # Game modes
    MODE_HUMAN_VS_AI = 0
    MODE_AI_VS_AI = 1
    MODE_GAME_OVER = 2

    def __init__(self):
        import contextlib
        with contextlib.redirect_stdout(None):
            pygame.init()

        cell_size = _compute_cell_size()
        self.board_renderer = BoardRenderer(cell_size=cell_size)
        self.piece_renderer = PieceRenderer(cell_size=cell_size)

        window_w = self.board_renderer.total_width + SIDEBAR_WIDTH
        window_h = self.board_renderer.total_height
        self.screen = pygame.display.set_mode((window_w, window_h))
        pygame.display.set_caption("Jungle (Dou Shou Qi)")

        self.clock = pygame.time.Clock()
        self.ui = UIOverlay(self.board_renderer.total_width,
                            self.board_renderer.total_height, SIDEBAR_WIDTH)

        self._init_game()

    def _init_game(self, mode: int = None):
        """Initialize or reset the game state."""
        if mode is not None:
            self.mode = mode
        else:
            self.mode = self.MODE_HUMAN_VS_AI
        clear_tt()  # Reset transposition table for new game
        self.game = GameState()
        self.selected_pos = None
        self.legal_moves_for_selected = []
        self.last_move = None
        self.blue_captured = []
        self.red_captured = []
        self.ai_thinking = False
        self.ai_result = None
        self.ai_done = threading.Event()
        self.ai_thread = None
        self.board_flipped = False
        self.board_renderer.set_flipped(False)
        self.tick = 0
        self.capture_animations: list[CaptureAnimation] = []
        self.last_ai_move_time = 0  # For AI-vs-AI delay

    def run(self):
        """Main game loop."""
        running = True
        while running:
            self.tick += 1
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_f:
                        self.board_flipped = not self.board_flipped
                        self.board_renderer.set_flipped(self.board_flipped)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(mouse_pos)

            # Update capture animations
            for anim in self.capture_animations:
                anim.update()
            self.capture_animations = [a for a in self.capture_animations if a.active]

            # Check AI result
            if self.ai_done.is_set():
                self._execute_ai_move()
                self.ai_result = None
                self.ai_done.clear()
                self.ai_thinking = False

            # AI turn handling
            now = time.time() * 1000
            if not self.game.is_over and not self.ai_thinking:
                if self.mode == self.MODE_AI_VS_AI:
                    # Add delay between AI moves for visual clarity
                    if now - self.last_ai_move_time > AI_VS_AI_DELAY_MS:
                        self._start_ai_turn()
                        self.last_ai_move_time = now
                elif self.mode == self.MODE_HUMAN_VS_AI and self.game.current_player == Player.RED:
                    self._start_ai_turn()

            # Render
            self._render(mouse_pos)
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def _handle_click(self, mouse_pos: tuple[int, int]):
        """Handle mouse click events."""
        # Check UI buttons
        if self.ui.check_new_game_click(mouse_pos):
            self._init_game(self.MODE_HUMAN_VS_AI)
            return
        if self.ui.check_ai_vs_ai_click(mouse_pos):
            self._init_game(self.MODE_AI_VS_AI)
            return
        if self.ui.check_flip_click(mouse_pos):
            self.board_flipped = not self.board_flipped
            self.board_renderer.set_flipped(self.board_flipped)
            return

        # Don't allow clicks during AI thinking or game over
        if self.ai_thinking or self.game.is_over:
            return

        # Only allow clicks during human's turn in HUMAN_VS_AI mode
        if self.mode == self.MODE_HUMAN_VS_AI and self.game.current_player == Player.RED:
            return

        # Convert pixel to board coordinates
        board_pos = self.board_renderer.pixel_to_board(mouse_pos[0], mouse_pos[1])
        if board_pos is None:
            self.selected_pos = None
            self.legal_moves_for_selected = []
            return

        col, row = board_pos

        # If a piece is selected, check if this is a legal move target
        if self.selected_pos is not None:
            for from_pos, to_pos in self.legal_moves_for_selected:
                if to_pos == (col, row):
                    captured = self.game.make_move(self.selected_pos, (col, row))
                    self._record_capture(captured, col, row)
                    self.last_move = (self.selected_pos, (col, row))
                    self.selected_pos = None
                    self.legal_moves_for_selected = []
                    if self.game.is_over:
                        self.mode = self.MODE_GAME_OVER
                    return

            # If clicking another own piece, select it instead
            piece = self.game.piece_at(col, row)
            if piece is not None and piece.player == self.game.current_player:
                self.selected_pos = (col, row)
                all_moves = generate_legal_moves(self.game, self.game.current_player)
                self.legal_moves_for_selected = [m for m in all_moves if m[0] == (col, row)]
                return

            # Otherwise deselect
            self.selected_pos = None
            self.legal_moves_for_selected = []
            return

        # No piece selected - try to select one
        piece = self.game.piece_at(col, row)
        if piece is not None and piece.player == self.game.current_player:
            self.selected_pos = (col, row)
            all_moves = generate_legal_moves(self.game, self.game.current_player)
            self.legal_moves_for_selected = [m for m in all_moves if m[0] == (col, row)]

    def _start_ai_turn(self):
        """Start AI thinking in a background thread."""
        if self.ai_thinking:
            return
        self.ai_thinking = True
        self.ai_result = None
        self.ai_done.clear()

        game_copy = self.game.copy()
        current_player = self.game.current_player

        # Use shorter time limit for AI vs AI to speed up games
        time_limit = AI_TIME_LIMIT_MS
        if self.mode == self.MODE_AI_VS_AI:
            time_limit = 800

        def ai_worker():
            try:
                result = find_best_move(game_copy, current_player, time_limit)
                self.ai_result = result
            except Exception:
                self.ai_result = None
                self.ai_thinking = False
            finally:
                self.ai_done.set()

        self.ai_thread = threading.Thread(target=ai_worker, daemon=True)
        self.ai_thread.start()

    def _execute_ai_move(self):
        """Execute the AI's chosen move."""
        if self.ai_result is None:
            return

        from_pos, to_pos = self.ai_result
        if (from_pos, to_pos) in generate_legal_moves(self.game, self.game.current_player):
            captured = self.game.make_move(from_pos, to_pos)
            self._record_capture(captured, to_pos[0], to_pos[1])
            self.last_move = (from_pos, to_pos)

        if self.game.is_over:
            self.mode = self.MODE_GAME_OVER

    def _record_capture(self, captured, col: int = 0, row: int = 0):
        """Record a captured piece and trigger animation."""
        if captured is not None:
            if captured.player == Player.RED:
                self.blue_captured.append(captured)
            else:
                self.red_captured.append(captured)
            # Add capture flash animation
            self.capture_animations.append(CaptureAnimation(col, row))

    def _render(self, mouse_pos: tuple[int, int]):
        """Render the entire frame."""
        self.screen.fill((30, 30, 30))

        # Board
        board_offset = (0, 0)
        self.board_renderer.render(
            self.screen, board_offset,
            selected_pos=self.selected_pos,
            legal_moves=self.legal_moves_for_selected if self.selected_pos else None,
            last_move=self.last_move,
            tick=self.tick
        )

        # Pieces
        for piece in self.game.pieces:
            cx, cy = self.board_renderer.board_to_pixel(piece.col, piece.row)
            is_selected = (self.selected_pos == (piece.col, piece.row))
            self.piece_renderer.render_piece(self.screen, piece, cx, cy, is_selected)

        # Capture animations
        for anim in self.capture_animations:
            rect = self.board_renderer._cell_rect(anim.col, anim.row)
            rect.x += board_offset[0]
            rect.y += board_offset[1]
            flash = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            flash.fill((255, 100, 100, anim.alpha))
            self.screen.blit(flash, rect)

        # Hover highlight
        board_pos = self.board_renderer.pixel_to_board(mouse_pos[0], mouse_pos[1])
        if board_pos is not None and not self.game.is_over:
            rect = self.board_renderer._cell_rect(board_pos[0], board_pos[1])
            rect.x += board_offset[0]
            rect.y += board_offset[1]
            hover_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            hover_surf.fill((255, 255, 255, 25))
            self.screen.blit(hover_surf, rect)
            # If hovering over own piece, show cursor as selectable
            piece = self.game.piece_at(board_pos[0], board_pos[1])
            if piece is not None and piece.player == self.game.current_player:
                pygame.draw.rect(self.screen, (255, 255, 255, 50), rect, 2)

        # Turn indicator
        self.ui.render_turn_indicator(
            self.screen, self.game.current_player, self.ai_thinking
        )

        # Sidebar
        sidebar_x = self.board_renderer.total_width
        pygame.draw.rect(self.screen, (40, 40, 40),
                         (sidebar_x, 0, SIDEBAR_WIDTH, self.board_renderer.total_height))
        pygame.draw.line(self.screen, (60, 60, 60),
                         (sidebar_x, 0), (sidebar_x, self.board_renderer.total_height), 2)

        # Captured pieces
        self.ui.render_captured_pieces(
            self.screen, self.blue_captured, self.red_captured,
            self.piece_renderer, sidebar_x, 40
        )

        # Rank legend
        self.ui.render_rank_legend(self.screen, sidebar_x, 260)

        # Buttons
        self.ui.render_buttons(self.screen, mouse_pos)

        # Game over overlay
        if self.game.is_over:
            self.ui.render_game_over(self.screen, self.game.winner, mouse_pos)

        pygame.display.flip()