from clubsandwich.ui import (
  LabelView,
  ButtonView,
  LayoutOptions,
  UIScene,
  WindowView,
)

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


TEXT_GAME_OVER = """
      __.      
    _/ / \\
   /   \\  *      ______________________________________
──/─────\\──     / Ah, well... another body to feed the \\
  \\ - - /    ──/  mutated skunks...                    |
&  \\ - /  &    \\_______________________________________/ 
 \\───+───/
     |
\\────|────/
_\\       /_
"""[1:].rstrip()


TEXT_YOU_WIN = """
      __.      
    _/ / \\
   /   \\  *      _______________________________________
──/─────\\──     / Oh, thank you so much! You might want \\
  \\ - - /    ──/  to talk to my neighbor, he's also in  |
&  \\ - /  &    |  the Netherwizard Club...             / 
 \\───+───/     \\______________________________________/ 
     |
\\────|────/
_\\       /_
"""[1:].rstrip()


class PauseScene(UIScene):
  def __init__(self, *args, **kwargs):
    view = WindowView(
      'Pause',
      layout_options=LayoutOptions.centered(40, 10),
      subviews=[
          ButtonView(
              text='Resume', callback=self.resume,
              layout_options=LayoutOptions.row_top(5)),
          ButtonView(
              text='Quit', callback=self.quit,
              layout_options=LayoutOptions.row_bottom(5)),
      ])
    super().__init__(view, *args, **kwargs)
    self.covers_screen = False

  def resume(self):
    self.director.pop_scene()

  def quit(self):
    self.director.pop_to_first_scene()


class LoseScene(UIScene):
  def __init__(self, score, *args, **kwargs):
    view = WindowView(
      'Game Over',
      layout_options=LayoutOptions.centered(80, 30),
      subviews=[
          LabelView(TEXT_GAME_OVER, layout_options=LayoutOptions.centered('intrinsic', 'intrinsic')),
          LabelView("Your score: {}".format(score),
            layout_options=LayoutOptions.row_bottom(1).with_updates(bottom=6)),
          ButtonView(
              text='Aaauuuuggghhhhhh...', callback=self.done,
              layout_options=LayoutOptions.row_bottom(3)),
      ])
    super().__init__(view, *args, **kwargs)
    self.covers_screen = False

  def done(self):
    self.director.pop_to_first_scene()


class WinScene(UIScene):
  def __init__(self, score, *args, **kwargs):
    view = WindowView(
      'You win!',
      layout_options=LayoutOptions.centered(80, 30),
      subviews=[
          LabelView(TEXT_YOU_WIN, layout_options=LayoutOptions.centered('intrinsic', 'intrinsic')),
          LabelView("Your score: {}".format(score),
            layout_options=LayoutOptions.row_bottom(1).with_updates(bottom=6)),
          ButtonView(
              text='Thanks!', callback=self.done,
              layout_options=LayoutOptions.row_bottom(3)),
      ])
    super().__init__(view, *args, **kwargs)
    self.covers_screen = False

  def done(self):
    self.director.pop_to_first_scene()
