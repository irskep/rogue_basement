from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap
from .level_generator import generate_dungeon
from .const import EnumEntityKind


LEVEL_SIZE = Size(80, 25)


class Entity:
  def __init__(self, kind):
    self.kind = kind
    self.stats = {}
    self.state = {}
    self.position = None


class Player(Entity):
  def __init__(self):
    super().__init__(EnumEntityKind.PLAYER)
    self.stats = {}
    self.state = {'hp': 100}


class Level:
  def __init__(self):
    self.tilemap = TileMap(LEVEL_SIZE)
    self.points_of_interest = generate_dungeon(self.tilemap)


class LevelState:
  def __init__(self, level):
    self.uuid = uuid4().hex
    self.level = level
    self.entities = []

    self.player = Player()
    self.player.position = self.level.points_of_interest['stairs_up']
    self.add_entity(self.player)
  
  def add_entity(self, entity):
    self.entities.append(entity)
  
  def remove_entity(self, entity):
    self.entities.remove(entity)


class GameState:
  def __init__(self):
    self.turn_number = 0
    self.level_states_by_id = {}

    self.active_id = self.add_level().uuid

  @property
  def active_level_state(self):
    return self.level_states_by_id[self.active_id]

  def add_level(self):
    level_state = LevelState(Level())
    self.level_states_by_id[level_state.uuid] = level_state
    return level_state
