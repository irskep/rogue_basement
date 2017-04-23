import random
import weakref
from collections import deque
from enum import Enum
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap

from .level_generator import generate_dungeon
from .const import (
  EnumEventNames,
  EnumTerrain,
  EnumMonsterMode,
  ITEM_TYPES_BY_ID,
  MONSTER_TYPES_BY_ID,
)
from .entity import Item


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


class StandardEnemyBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [EnumEventNames.player_took_action])


@behavior('sleep')
class SleepBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, player, data):
    self.entity.mode = EnumMonsterMode.DEFAULT
    return True


@behavior('random_walk')
class RandomWalkBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, player, data):
    if self.entity.position.manhattan_distance_to(self.level_state.player.position) > 40:
      self.entity.mode = EnumMonsterMode.SLEEPING
      return True

    self.entity.mode = EnumMonsterMode.DEFAULT
    possibilities = self.level_state.get_passable_neighbors(self.entity)
    if not possibilities:
      return False
    self.level_state.action_monster_move(self.entity, random.choice(possibilities))
    return True


@behavior('beeline_visible')
@behavior('beeline_target')  # temporary
class BeelineBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, player, data):
    if not self.level_state.test_line_of_sight(self.entity, self.level_state.player):
      return False

    candidates = self.level_state.get_passable_neighbors(self.entity, allow_player=True)
    if not candidates:
      return False

    self.entity.mode = EnumMonsterMode.CHASING

    point = self.level_state.player.position.get_closest_point(candidates)
    self.level_state.action_monster_move(self.entity, point)
    return True


@behavior('range_5_visible')
class Range5VisibleBehavior(StandardEnemyBehavior):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.best_range = 5

  def on_player_took_action(self, player, data):
    if not self.level_state.test_line_of_sight(self.entity, self.level_state.player):
      return False

    candidates = self.level_state.get_passable_neighbors(self.entity)
    if not candidates:
      return False

    dist = self.entity.position.manhattan_distance_to(self.level_state.player.position)

    if dist < self.best_range - 1:
      self.entity.mode = EnumMonsterMode.FLEEING
      self.level_state.action_monster_move(
        self.entity, self.level_state.player.position.get_farthest_point(candidates))
      return True
    elif dist > self.best_range:
      self.entity.mode = EnumMonsterMode.CHASING
      self.level_state.action_monster_move(
        self.entity, self.level_state.player.position.get_closest_point(candidates))
      return True
    else:
      return False  # probably cascade to some kind of ranged attack


@behavior('range_7_visible')
class Range7VisibleBehavior(Range5VisibleBehavior):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.best_range = 7


@behavior('throw_rock_slow')
class ThrowRockSlowBehavior(StandardEnemyBehavior):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.rock_speed = 1

  def on_player_took_action(self, player, data):
    if not self.level_state.test_line_of_sight(self.entity, self.level_state.player):
      return False

    self.entity.behavior_state.setdefault('throw_rock_cooldown', 1)
    self.entity.behavior_state['throw_rock_cooldown'] -= 1

    if self.entity.behavior_state['throw_rock_cooldown'] <= 0:
      self.entity.behavior_state['throw_rock_cooldown'] = 6
      path = list(self.entity.position.points_bresenham_to(self.level_state.player.position))
      while self.level_state.get_entity_at(path[0]) == self.entity:
        path.pop(0)
      entity_in_the_way = self.level_state.get_entity_at(path[0])
      if entity_in_the_way and not entity_in_the_way.is_player:
        print("Can't throw, something's in the way")
        return False

      self.level_state.create_entity(MONSTER_TYPES_BY_ID['ROCK_IN_FLIGHT'], path[0], {
        'path': [None] + path[1:],  # behavior executes immediately but rock is already placed
        'speed': self.rock_speed,
      })


@behavior('path_until_hit')
class PathUntilHitBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, player, data):
    p = self.entity.position
    if not self.entity.behavior_state.get('path', None):
      self.level_state.remove_entity(self.entity)
      self.level_state.drop_item(Item(ITEM_TYPES_BY_ID['ROCK']), p, entity=self.entity)
      return True

    next_point = self.entity.behavior_state['path'].pop(0)
    if next_point is None:
      # this is basically a "wait" instruction
      return True

    entity_to_hit = self.level_state.get_entity_at(next_point)
    if entity_to_hit:
      p = entity_to_hit.position
      self.level_state.action_attack(self.entity, entity_to_hit)
    elif self.level_state.get_is_terrain_passable(next_point):
      self.level_state.action_monster_move(self.entity, next_point)
      return True

    self.level_state.remove_entity(self.entity)
    self.level_state.drop_item(Item(ITEM_TYPES_BY_ID['ROCK']), p, entity=self.entity)
    return True
    