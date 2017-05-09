#!/usr/bin/env python

# Welcome to the Rogue Basement Annotated Source Code! The comments should
# give you a general idea of how things work. You should steal these ideas,
# or learn from my mistakes, as the case may be. :-)

# clubsandwich is my roguelike library that wraps bearlibterminal. We need it
# for some basics which I'll get to in a moment.
from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.director import DirectorLoop
from clubsandwich.geom import Size

# A "scene" is an object that takes over the input and display. We have one
# for the title screen and one for the game.
from ld38.main_menu_scene import MainMenuScene
from ld38.game_scene import GameMainScene

# This is a pathlib.Path object pointing to the game working directory
# containing the executable (and the assets)
from ld38.const import GAME_ROOT


WINDOW_SIZE = Size(100, 46)


# This is a subclass of the clubsandwich game loop object, which takes care of
# a LOT of stuff for us. We just need to do a little configuration to set the
# window size and load the font, and specify what our first scene is.
#
# Once we've provided those things, the DirectorLoop base class will forward
# all input to the active scene, and allow the active scene to draw the screen.
class GameLoop(DirectorLoop):
  def terminal_init(self):
    super().terminal_init()
    terminal.set("""
    window.resizeable=true;
    window.size={size.width}x{size.height};
    font: {root}/assets/NotoMono-Regular.ttf, size=10x16;
    """.format(size=WINDOW_SIZE, root=str(GAME_ROOT)))

  def get_initial_scene(self):
    # The first scene is the main menu scene. It's a standard, boring
    # clubsandwich UI scene, so you don't need to bother reading the code
    # unless you want to know how the layout is done.
    return MainMenuScene()


if __name__ == '__main__':
  # Every frame (as fast as possible up to 80fps), check for input, handle it
  # if it exists, and then draw the screen. Quit if the active scene says so.
  GameLoop().run()

# next stop: ld38/game_scene.py!
