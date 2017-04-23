import weakref
from collections import deque
from enum import Enum
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap

from .level_generator import generate_dungeon
from .const import EnumEntityKind, EnumEventNames, EnumTerrain


class Entity:
  def __init__(self, kind):
    self.kind = kind
    self.stats = {}
    self.state = {}
    self.position = None
    self.behaviors = []
    self.mode = None

  def add_behavior(self, behavior):
    self.behaviors.append(behavior)

  def __repr__(self):
    return self.__class__.__name__


class Player(Entity):
  def __init__(self):
    super().__init__(EnumEntityKind.PLAYER)
    self.stats = {'hp_max': 100}
    self.state = {'hp': 100}
