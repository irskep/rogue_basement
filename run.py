#!/usr/bin/env python
import os
import sys
from pathlib import Path

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.director import DirectorLoop
from clubsandwich.geom import Size

from ld38.game_scene import GameScene
from ld38.scenes import MainMenuScene


WINDOW_SIZE = Size(100, 46)
HALF_WINDOW_SIZE = (Size(80, 25) / 2).floored

root = Path(os.path.abspath(sys.argv[0])).parent


class GameLoop(DirectorLoop):
  def terminal_init(self):
    super().terminal_init()
    terminal.set("""
    window.resizeable=true;
    window.size={size.width}x{size.height};
    font: {root}/assets/NotoMono-Regular.ttf, size=10x16;
    """.format(size=WINDOW_SIZE, root=str(root)))

  def get_initial_scene(self):
    return MainMenuScene(GameScene)


if __name__ == '__main__':
  GameLoop().run()
