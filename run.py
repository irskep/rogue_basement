#!/usr/bin/env python
import random
import string
from enum import Enum

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.blt.state import blt_state
from clubsandwich.director import DirectorLoop, Scene
from clubsandwich.geom import Rect, Point, Size
from clubsandwich.draw import LINE_STYLES
from clubsandwich.generators import RandomBSPTree
from clubsandwich.tilemap import TileMap, CellOutOfBoundsError
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


class EnumTerrain(Enum):
  EMPTY = 0
  FLOOR = 1
  WALL = 2
  DOOR_CLOSED = 3
  DOOR_OPEN = 4
  CORRIDOR = 5


class Room:
  def __init__(self, rect):
    self.rect = rect


def generate_room(bsp_leaf):
  """Decorate *bsp_leaf* with a :py:class:`Room` object"""
  bsp_leaf.data['room'] = Room(bsp_leaf.rect.get_random_rect(Size(4, 4)))
  return bsp_leaf.data['room']


def generate_random_path(tilemap, rect1, rect2):
  start = rect1.get_random_point()
  end = rect2.get_random_point()
  points_in_path = set()
  doors = set()
  corridors = set()
  for point in start.path_L_to(end):
    points_in_path.add(point)
    has_corridor_neighbor = False
    for neighbor in point.neighbors:
      if neighbor in points_in_path:
        continue
      try:
        has_corridor_neighbor = tilemap.cell(neighbor).terrain == EnumTerrain.CORRIDOR
      except CellOutOfBoundsError:
        pass
      if has_corridor_neighbor:
        continue
    cell = tilemap.cell(point)
    if cell.terrain == EnumTerrain.WALL:
      doors.add(cell)
    elif (cell.terrain == EnumTerrain.EMPTY or not cell.terrain) and not has_corridor_neighbor:
      corridors.add(cell)
  return (doors, corridors)



def generate_dungeon(tilemap):
  generator = RandomBSPTree(tilemap.size, 4)

  rooms = [generate_room(leaf) for leaf in generator.root.leaves]

  for room in rooms:
    for corner in room.rect.points_corners:
      tilemap.cell(corner).terrain = EnumTerrain.WALL
    tilemap.cell(room.rect.origin).annotations.add('corner_top_left')
    tilemap.cell(room.rect.point_top_right).annotations.add('corner_top_right')
    tilemap.cell(room.rect.point_bottom_left).annotations.add('corner_bottom_left')
    tilemap.cell(room.rect.point_bottom_right).annotations.add('corner_bottom_right')

    for point in room.rect.points_top:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('horz')
    for point in room.rect.points_bottom:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('horz')
    for point in room.rect.points_left:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('vert')
    for point in room.rect.points_right:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('vert')
    for point in room.rect.with_inset(1).points:
      tilemap.cell(point).terrain = EnumTerrain.FLOOR

  for (a, b) in generator.root.sibling_pairs:
    a = a.leftmost_leaf
    b = b.rightmost_leaf
    (doors, corridors) = generate_random_path(
      tilemap,
      a.data['room'].rect.with_inset(1),
      b.data['room'].rect.with_inset(1))
    iter_count = 0
    while len(doors) > 4 and iter_count < 10:
      iter_count += 1
      (doors, corridors) = generate_random_path(
        tilemap,
        a.data['room'].rect.with_inset(1),
        b.data['room'].rect.with_inset(1))
    for door in doors:
      door.terrain = EnumTerrain.DOOR_CLOSED
    for corridor in corridors:
      corridor.terrain = EnumTerrain.CORRIDOR


def draw_tilemap(tilemap, ctx=terminal):
  line_chars = LINE_STYLES['single']
  for cell in tilemap.cells:
    char = ' '
    color = '#ffffff'
    if cell.terrain == EnumTerrain.FLOOR:
      char = '.'
      color = '#666666'
    if cell.terrain == EnumTerrain.WALL:
      char = '#'
      if 'horz' in cell.annotations:
        char = line_chars['T']
      if 'vert' in cell.annotations:
        char = line_chars['L']
      if 'corner_top_left' in cell.annotations:
        char = line_chars['TL']
      if 'corner_top_right' in cell.annotations:
        char = line_chars['TR']
      if 'corner_bottom_left' in cell.annotations:
        char = line_chars['BL']
      if 'corner_bottom_right' in cell.annotations:
        char = line_chars['BR']
    if cell.terrain == EnumTerrain.DOOR_CLOSED:
      char = '+'
    if cell.terrain == EnumTerrain.DOOR_OPEN:
      char = "'"
    if cell.terrain == EnumTerrain.CORRIDOR:
      char = "#"
    if cell.debug_character:
      char = cell.debug_character
    ctx.color(color)
    ctx.put(cell.point, char)


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
