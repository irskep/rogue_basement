#!/usr/bin/env python
from enum import Enum

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.director import DirectorLoop
from clubsandwich.geom import Size
from clubsandwich.tilemap import TileMap
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

from ld38.level_generator import generate_dungeon
from ld38.draw_tilemap import draw_tilemap


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




class Entity:
    def __init__(self):
        self.stats = {}
        self.state = {}
        self.position = None
        self.is_player = False


class GameState:
    def __init__(self, player_strength):
        self.turn_number = 0
        self.player = Entity()
        self.player.stats = {}
        self.player.state = {'hp': 100}
        self.world = {
            'level_ids': [],
            'levels_by_id': {},
        }
        self.add_level()

    def add_level(self):
        pass


class GameScene(UIScene):
    def __init__(self, *args, **kwargs):
        views = [
        ]
        super().__init__(views, *args, **kwargs)
        self.tilemap = TileMap(Size(80, 25))
        generate_dungeon(self.tilemap)

    def terminal_update(self, is_active=True):
        super().terminal_update(is_active)
        draw_tilemap(self.tilemap)


if __name__ == '__main__':
    GameLoop().run()
