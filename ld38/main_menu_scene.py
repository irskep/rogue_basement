from clubsandwich.ui import (
  LabelView,
  ButtonView,
  LayoutOptions,
  UIScene,
)
from .game_scene import GameMainScene

TITLE = """
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


class MainMenuScene(UIScene):
  def __init__(self, *args, **kwargs):
    views = [
      LabelView(
        TITLE[1:].rstrip(),
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
    self.director.push_scene(GameMainScene())
