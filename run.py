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

from ld38.draw_tilemap import draw_tilemap
from ld38.gamestate import GameState


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

    def terminal_update(self, is_active=True):
        super().terminal_update(is_active)
        draw_tilemap(self.gamestate.active_level.tilemap)


if __name__ == '__main__':
    GameLoop().run()
