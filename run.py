#!/usr/bin/env python
from enum import Enum

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.director import DirectorLoop
from clubsandwich.ui import (
  LabelView,
  ButtonView,
  FirstResponderContainerView,
  WindowView,
  SettingsListView,
  LayoutOptions,
  UIScene,
  CyclingButtonView,
  SingleLineTextInputView,
  IntStepperView,
)

from ld38.draw_game import draw_game
from ld38.gamestate import GameState
from ld38.const import EnumEventNames


LOGO = """
"""


class GameLoop(DirectorLoop):
  def terminal_init(self):
    super().terminal_init()
    terminal.set("""
    window.resizeable=true;
    """)

  def get_initial_scene(self):
    return GameScene()
    #return MainMenuScene()


### Menus ###


class MainMenuScene(UIScene):
    def __init__(self, *args, **kwargs):
        views = [
            LabelView(
                LOGO[1:].rstrip(),
                layout_options=LayoutOptions.row_top(0.5)),
            ButtonView(
                text="Play", callback=self.play,
                layout_options=LayoutOptions.row_bottom(4).with_updates(
                    left=0.2, width=0.2, right=None)),
            ButtonView(
                text="Quit", callback=self.director.pop_scene,
                layout_options=LayoutOptions.row_bottom(4).with_updates(
                    left=0.6, width=0.2, right=None)),
        ]
        super().__init__(views, *args, **kwargs)

    def play(self):
        self.director.push_scene(GameScene())


### Game ###


class GameScene(UIScene):
  def __init__(self, *args, **kwargs):
    views = []
    self.gamestate = GameState()
    super().__init__(views, *args, **kwargs)

  def terminal_read(self, val):
    if val in (terminal.TK_UP, terminal.TK_K, terminal.TK_KP_8):
      self.gamestate.active_level_state.fire(EnumEventNames.key_u)
    if val in (terminal.TK_DOWN, terminal.TK_J, terminal.TK_KP_2):
      self.gamestate.active_level_state.fire(EnumEventNames.key_d)
    if val in (terminal.TK_LEFT, terminal.TK_H, terminal.TK_KP_4):
      self.gamestate.active_level_state.fire(EnumEventNames.key_l)
    if val in (terminal.TK_RIGHT, terminal.TK_L, terminal.TK_KP_6):
      self.gamestate.active_level_state.fire(EnumEventNames.key_r)
    if val in (terminal.TK_Y, terminal.TK_KP_7):
      self.gamestate.active_level_state.fire(EnumEventNames.key_ul)
    if val in (terminal.TK_U, terminal.TK_KP_9):
      self.gamestate.active_level_state.fire(EnumEventNames.key_ur)
    if val in (terminal.TK_B, terminal.TK_KP_1):
      self.gamestate.active_level_state.fire(EnumEventNames.key_dl)
    if val in (terminal.TK_N, terminal.TK_KP_3):
      self.gamestate.active_level_state.fire(EnumEventNames.key_dr)

  def terminal_update(self, is_active=True):
    super().terminal_update(is_active)
    self.gamestate.active_level_state.consume_events()
    draw_game(self.gamestate)


if __name__ == '__main__':
    GameLoop().run()
