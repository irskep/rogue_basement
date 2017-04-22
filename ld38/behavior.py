import random
import weakref
from collections import deque
from enum import Enum
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap

from .level_generator import generate_dungeon
from .const import EnumEntityKind, EnumEventNames, EnumTerrain


class Behavior:
  def __init__(self, entity, level_state, event_names):
    self.event_names = event_names
    self._entity = weakref.ref(entity)
    self._level_state = weakref.ref(level_state)
    self.is_local_to_entity = False

  @property
  def entity(self):
    return self._entity()

  @property
  def level_state(self):
    return self._level_state()

  def add_to_event_dispatcher(self, dispatcher):
    for name in self.event_names:
      dispatcher.add_subscriber(self, name, self.entity if self.is_local_to_entity else False)

  def remove_from_event_dispatcher(self, dispatcher):
    for name in self.event_names:
      dispatcher.remove_subscriber(self, name, self.entity if self.is_local_to_entity else False)


class KeyboardMovementBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [
      EnumEventNames.key_u,
      EnumEventNames.key_d,
      EnumEventNames.key_l,
      EnumEventNames.key_r,
      EnumEventNames.key_ul,
      EnumEventNames.key_ur,
      EnumEventNames.key_dl,
      EnumEventNames.key_dr,
    ])

  def on_key_u(self, data): self.level_state.move(self.entity, self.entity.position + Point(0, -1))
  def on_key_d(self, data): self.level_state.move(self.entity, self.entity.position + Point(0, 1))
  def on_key_l(self, data): self.level_state.move(self.entity, self.entity.position + Point(-1, 0))
  def on_key_r(self, data): self.level_state.move(self.entity, self.entity.position + Point(1, 0))
  def on_key_ul(self, data): self.level_state.move(self.entity, self.entity.position + Point(-1, -1))
  def on_key_ur(self, data): self.level_state.move(self.entity, self.entity.position + Point(1, -1))
  def on_key_dl(self, data): self.level_state.move(self.entity, self.entity.position + Point(-1, 1))
  def on_key_dr(self, data): self.level_state.move(self.entity, self.entity.position + Point(1, 1))


class RandomWalkBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [EnumEventNames.player_took_action])

  def on_player_took_action(self, data):
    possibilities = [
      poss for poss in [
      self.entity.position + p for p in [
        Point(0, -1), Point(0, 1), Point(-1, 0), Point(1, 0)]
      ] if self.level_state.get_can_move(self.entity, poss)
    ]
    if not possibilities:
      return
    self.level_state.move(self.entity, random.choice(possibilities))
