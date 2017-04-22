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

  def on_key_u(self, data): self.level_state.fire(EnumEventNames.move_u, self.entity)
  def on_key_d(self, data): self.level_state.fire(EnumEventNames.move_d, self.entity)
  def on_key_l(self, data): self.level_state.fire(EnumEventNames.move_l, self.entity)
  def on_key_r(self, data): self.level_state.fire(EnumEventNames.move_r, self.entity)
  def on_key_ul(self, data): self.level_state.fire(EnumEventNames.move_ul, self.entity)
  def on_key_ur(self, data): self.level_state.fire(EnumEventNames.move_ur, self.entity)
  def on_key_dl(self, data): self.level_state.fire(EnumEventNames.move_dl, self.entity)
  def on_key_dr(self, data): self.level_state.fire(EnumEventNames.move_dr, self.entity)


class MovementBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [
      EnumEventNames.move_u,
      EnumEventNames.move_d,
      EnumEventNames.move_l,
      EnumEventNames.move_r,
      EnumEventNames.move_ul,
      EnumEventNames.move_ur,
      EnumEventNames.move_dl,
      EnumEventNames.move_dr,
    ])
    self.is_local_to_entity = True

  def on_move_u(self, data): self.level_state.move(self.entity, self.entity.position + Point(0, -1))
  def on_move_d(self, data): self.level_state.move(self.entity, self.entity.position + Point(0, 1))
  def on_move_l(self, data): self.level_state.move(self.entity, self.entity.position + Point(-1, 0))
  def on_move_r(self, data): self.level_state.move(self.entity, self.entity.position + Point(1, 0))
  def on_move_ul(self, data): self.level_state.move(self.entity, self.entity.position + Point(-1, -1))
  def on_move_ur(self, data): self.level_state.move(self.entity, self.entity.position + Point(1, -1))
  def on_move_dl(self, data): self.level_state.move(self.entity, self.entity.position + Point(-1, 1))
  def on_move_dr(self, data): self.level_state.move(self.entity, self.entity.position + Point(1, 1))
