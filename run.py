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
 )| \\  | | | | | | |-'   ,|   \\ ,-| `-. |-' | | | |-' | | |
 `'  ` `-' `-| `-^ `-'  `-^---' `-^ `-' `-' ' ' ' `-' ' ' `' 
            ,|                                               
            `'



      __.        ___________________________________________
    _/ / \\      / Hello there! I'm in a bit of a pickle.    \\
   /   \\  *     | Yesterday I was doing some experiments    |
──/─────\\──     | in the basement, and I may have...        |
  \\ - - /    ──/  ...accidentally...opened a portal to the  |
&  \\ - /  &     | nethervoid. Could you just pop down there |
 \\───+───/      | and close it up for me? It'll be easy!    |
     |          \\___________________________________________/
\\────|────/
_\\       /_
"""


ABOUT = """
Rogue Basement is a roguelike with a "small world," i.e. a single
idiot wizard's basement.

Note that while you can resize the window, it might slow things
down a lot, because this game is very poorly optimized.

Use <tab> and <return> to navigate menus.
""".strip()


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
      LabelView(
        ABOUT,
        color_fg='#ffcb00',
        layout_options=LayoutOptions.centered('intrinsic', 'intrinsic').with_updates(top=28)),
      ButtonView(
        text="Descend the stairs", callback=self.play,
        layout_options=LayoutOptions.row_bottom(10).with_updates(
          left=0.2, width=0.2, right=None)),
      ButtonView(
        text="Quit", callback=lambda: self.director.pop_scene(),
        layout_options=LayoutOptions.row_bottom(10).with_updates(
          left=0.6, width=0.2, right=None)),
    ]
    super().__init__(views, *args, **kwargs)

  def play(self):
    self.director.push_scene(GameScene())


if __name__ == '__main__':
  GameLoop().run()
