#!/usr/bin/env python
from enum import Enum

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.director import DirectorLoop
from clubsandwich.draw import draw_line_vert
from clubsandwich.geom import Size, Point, Rect
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
  View,
)

from ld38.draw_game import draw_game
from ld38.gamestate import GameState
from ld38.game_scene import GameScene
from ld38.const import EnumEventNames


WINDOW_SIZE = Size(100, 46)
HALF_WINDOW_SIZE = (Size(80, 25) / 2).floored


LOGO = """
.-,--.                  ,-,---.                           .  
 `|__/ ,-. ,-. . . ,-.   '|___/ ,-. ,-. ,-. ,-,-. ,-. ,-. |- 
 )| \  | | | | | | |-'   ,|   \ ,-| `-. |-' | | | |-' | | |  
 `'  ` `-' `-| `-^ `-'  `-^---' `-^ `-' `-' ' ' ' `-' ' ' `' 
            ,|                                               
            `'       
"""


class GameLoop(DirectorLoop):
  def terminal_init(self):
    super().terminal_init()
    terminal.set("""
    window.resizeable=true;
    window.size={size.width}x{size.height};
    font: NotoMono-Regular.ttf, size=10x16;
    """.format(size=WINDOW_SIZE))

  def get_initial_scene(self):
    return MainMenuScene()


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
        text="Quit", callback=lambda: self.director.pop_scene(),
        layout_options=LayoutOptions.row_bottom(4).with_updates(
          left=0.6, width=0.2, right=None)),
    ]
    super().__init__(views, *args, **kwargs)

  def play(self):
    self.director.push_scene(GameScene())


if __name__ == '__main__':
  GameLoop().run()
