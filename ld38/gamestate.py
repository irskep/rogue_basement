from uuid import uuid4

from clubsandwich.geom import Size
from clubsandwich.tilemap import TileMap
from ld38.level_generator import generate_dungeon


LEVEL_SIZE = Size(80, 25)


class Entity:
  def __init__(self):
    self.stats = {}
    self.state = {}
    self.position = None
    self.is_player = False


class Level:
  def __init__(self):
    self.tilemap = TileMap(LEVEL_SIZE)
    generate_dungeon(self.tilemap)
    self.uuid = uuid4().hex


class GameState:
  def __init__(self):
    self.turn_number = 0
    self.active_world_id = None
    self.player = Entity()
    self.player.stats = {}
    self.player.state = {'hp': 100}
    self.levels_by_id = {}
    self.active_level_id = self.add_level().uuid

  @property
  def active_level(self):
    return self.levels_by_id[self.active_level_id]

  def add_level(self):
    level = Level()
    self.levels_by_id[level.uuid] = level
    return level