import random
import weakref
from collections import deque
from enum import Enum
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap

from .level_generator import generate_dungeon
from .const import EnumEventNames, EnumTerrain, EnumMonsterMode


BEHAVIORS_BY_ID = {}
def behavior(behavior_id):
  def dec(cls):
    BEHAVIORS_BY_ID[behavior_id] = cls
    return cls
  return dec


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


@behavior('keyboard_movement')
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

  def on_key_u(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(0, -1))
  def on_key_d(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(0, 1))
  def on_key_l(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(-1, 0))
  def on_key_r(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(1, 0))
  def on_key_ul(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(-1, -1))
  def on_key_ur(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(1, -1))
  def on_key_dl(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(-1, 1))
  def on_key_dr(self, entity, data):
    self.level_state.action_player_move(self.entity, self.entity.position + Point(1, 1))


class CompositeBehavior(Behavior):
  def __init__(self, entity, level_state, sub_behaviors):
    self.sub_behaviors = sub_behaviors
    event_names = set()
    for b in sub_behaviors:
      event_names = event_names | set(b.event_names)
    for e in event_names:
      setattr(self, 'on_' + e.value, self.get_handler(e))
    super().__init__(entity, level_state, list(event_names))

  def get_handler(self, e):
    k = 'on_' + e.value
    methods = [
      getattr(b, k)
      for b in self.sub_behaviors
      if hasattr(b, k)]

    def handler(entity, data):
      for method in methods:
        if method(entity, data):
          return True
      return False
    return handler


@behavior('random_walk')
class RandomWalkBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [EnumEventNames.player_took_action])

  def on_player_took_action(self, entity, data):
    self.entity.mode = EnumMonsterMode.DEFAULT
    possibilities = [
      p for p in
      list(self.entity.position.neighbors) + list(self.entity.position.diagonal_neighbors)
      if self.level_state.get_can_move(self.entity, p)
    ]
    if not possibilities:
      return False
    self.level_state.action_monster_move(self.entity, random.choice(possibilities))
    return True


@behavior('beeline_visible')
@behavior('beeline_target')  # temporary
class BeelineBehavior(RandomWalkBehavior):
  def on_player_took_action(self, entity, data):
    if self.entity.position.manhattan_distance_to(self.level_state.player.position) > 20:
      return False

    if not self.level_state.test_line_of_sight(self.entity, self.level_state.player):
      return False

    candidates = [
      p for p in
      list(self.entity.position.neighbors) + list(self.entity.position.diagonal_neighbors)
      if self.level_state.tilemap.contains_point(p)]

    if not candidates:
      return False

    self.entity.mode = EnumMonsterMode.CHASING_PLAYER

    best_point = candidates[0]
    best_distance = best_point.manhattan_distance_to(self.level_state.player.position)
    for point in candidates:
      distance = point.manhattan_distance_to(self.level_state.player.position)
      if distance < best_distance:
        best_distance = distance
        best_point = point
    
    self.level_state.action_monster_move(self.entity, best_point)
    return True
    