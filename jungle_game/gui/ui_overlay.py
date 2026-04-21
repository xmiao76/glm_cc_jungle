"""UI overlay for Jungle (Dou Shou Qi).

Renders turn indicator, captured pieces display, buttons, and game-over messages.
"""

import pygame
from jungle_game.engine.pieces import Player, PieceType


# Colors
COLOR_BG = (45, 45, 45)
COLOR_TEXT = (230, 230, 230)
COLOR_BLUE = (66, 133, 244)
COLOR_RED = (229, 57, 53)
COLOR_BUTTON = (70, 70, 70)
COLOR_BUTTON_HOVER = (90, 90, 90)
COLOR_BUTTON_TEXT = (230, 230, 230)
COLOR_GOLD = (255, 215, 0)
COLOR_OVERLAY = (0, 0, 0, 180)


class Button:
    """A clickable button."""

    def __init__(self, x: int, y: int, w: int, h: int, text: str):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self._hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]):
        self._hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def render(self, surface: pygame.Surface, font: pygame.font.Font):
        color = COLOR_BUTTON_HOVER if self._hovered else COLOR_BUTTON
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_TEXT, self.rect, 2, border_radius=6)
        text_surf = font.render(self.text, True, COLOR_BUTTON_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class UIOverlay:
    """Manages and renders UI elements."""

    def __init__(self, board_width: int, board_height: int, sidebar_width: int):
        self.sidebar_width = sidebar_width
        self.board_width = board_width
        self.board_height = board_height

        # Fonts
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self._init_fonts()

        # Buttons
        btn_x = board_width + 20
        btn_w = sidebar_width - 40
        self.btn_new_game = Button(btn_x, board_height - 170, btn_w, 40, "New Game")
        self.btn_ai_vs_ai = Button(btn_x, board_height - 120, btn_w, 40, "AI vs AI")
        self.btn_flip = Button(btn_x, board_height - 70, btn_w, 40, "Flip Board")
        self.buttons = [self.btn_new_game, self.btn_ai_vs_ai, self.btn_flip]

        # Game over buttons
        self.btn_restart = Button(0, 0, 160, 44, "New Game")
        self.btn_ai_vs_ai_restart = Button(0, 0, 160, 44, "AI vs AI")

    def _init_fonts(self):
        """Initialize fonts (called after pygame.init)."""
        try:
            self.font_large = pygame.font.SysFont("segoeui", 28, bold=True)
            self.font_medium = pygame.font.SysFont("segoeui", 20)
            self.font_small = pygame.font.SysFont("segoeui", 16)
        except Exception:
            self.font_large = pygame.font.Font(None, 32)
            self.font_medium = pygame.font.Font(None, 24)
            self.font_small = pygame.font.Font(None, 18)

    def render_turn_indicator(self, surface: pygame.Surface,
                               current_player: Player,
                               ai_thinking: bool = False):
        """Render whose turn it is."""
        if current_player == Player.BLUE:
            text = "Blue's Turn"
            color = COLOR_BLUE
        else:
            text = "Red's Turn"
            color = COLOR_RED

        if ai_thinking:
            text += " (AI thinking...)"

        text_surf = self.font_large.render(text, True, color)
        text_rect = text_surf.get_rect(
            midtop=(self.board_width // 2, 8)
        )
        surface.blit(text_surf, text_rect)

    def render_captured_pieces(self, surface: pygame.Surface,
                                blue_captured: list, red_captured: list,
                                piece_renderer, offset_x: int, offset_y: int):
        """Render captured pieces on the sidebar."""
        # Blue's captured pieces (Red pieces captured by Blue)
        header = self.font_medium.render("Blue captured:", True, COLOR_BLUE)
        surface.blit(header, (offset_x + 10, offset_y))
        y = offset_y + 30
        for i, piece in enumerate(blue_captured):
            piece_renderer.render_captured(surface, piece, offset_x + 10 + i * 32, y)

        # Red's captured pieces (Blue pieces captured by Red)
        header = self.font_medium.render("Red captured:", True, COLOR_RED)
        y += 60
        surface.blit(header, (offset_x + 10, y))
        y += 30
        for i, piece in enumerate(red_captured):
            piece_renderer.render_captured(surface, piece, offset_x + 10 + i * 32, y)

    def render_buttons(self, surface: pygame.Surface, mouse_pos: tuple[int, int]):
        """Render sidebar buttons."""
        for btn in self.buttons:
            btn.update_hover(mouse_pos)
            btn.render(surface, self.font_medium)

    def render_game_over(self, surface: pygame.Surface, winner: Player,
                          mouse_pos: tuple[int, int]):
        """Render game-over overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        surface.blit(overlay, (0, 0))

        # Winner text
        if winner == Player.BLUE:
            text = "Blue Wins!"
            color = COLOR_BLUE
        else:
            text = "Red Wins!"
            color = COLOR_RED

        text_surf = self.font_large.render(text, True, color)
        text_rect = text_surf.get_rect(center=(self.board_width // 2, self.board_height // 2 - 40))
        surface.blit(text_surf, text_rect)

        # Subtitle
        sub = self.font_medium.render("Game Over", True, COLOR_TEXT)
        sub_rect = sub.get_rect(center=(self.board_width // 2, self.board_height // 2))
        surface.blit(sub, sub_rect)

        # Buttons
        cx = self.board_width // 2
        cy = self.board_height // 2 + 50
        self.btn_restart.rect.center = (cx - 90, cy)
        self.btn_ai_vs_ai_restart.rect.center = (cx + 90, cy)
        self.btn_restart.update_hover(mouse_pos)
        self.btn_ai_vs_ai_restart.update_hover(mouse_pos)
        self.btn_restart.render(surface, self.font_medium)
        self.btn_ai_vs_ai_restart.render(surface, self.font_medium)

    def check_new_game_click(self, mouse_pos: tuple[int, int]) -> bool:
        return self.btn_new_game.is_clicked(mouse_pos) or self.btn_restart.is_clicked(mouse_pos)

    def check_ai_vs_ai_click(self, mouse_pos: tuple[int, int]) -> bool:
        return self.btn_ai_vs_ai.is_clicked(mouse_pos) or self.btn_ai_vs_ai_restart.is_clicked(mouse_pos)

    def check_flip_click(self, mouse_pos: tuple[int, int]) -> bool:
        return self.btn_flip.is_clicked(mouse_pos)

    def render_rank_legend(self, surface: pygame.Surface, offset_x: int, offset_y: int):
        """Render piece rank legend on sidebar."""
        header = self.font_medium.render("Ranks:", True, COLOR_TEXT)
        surface.blit(header, (offset_x + 10, offset_y))
        y = offset_y + 28
        for ptype in reversed(PieceType):
            name = f"{int(ptype)}. {ptype.name}"
            text = self.font_small.render(name, True, COLOR_TEXT)
            surface.blit(text, (offset_x + 10, y))
            y += 20

        # Keyboard hint
        y += 10
        hint = self.font_small.render("(or press F)", True, (140, 140, 140))
        surface.blit(hint, (offset_x + 10, y))