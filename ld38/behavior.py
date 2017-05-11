# "Behaviors" specify how the monsters move.
# The companion to this file is actions.py, which is a bunch of helper
# functions for behaviors.
import random
import weakref
from collections import deque
from enum import Enum
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap

from .actions import (
  action_attack,
  action_pickup_item,
  action_move,
  action_throw,
)
from .level_generator import generate_dungeon
from .const import (
  EnumEventNames,
  EnumMonsterMode,
)
from .entity import Item


# This is a simple decorator that collects classes by name.
# For example, if you put ``@behavior('bloop')`` above a class, and then in
# monsters.csv you put "bloop" in the behavior column of a monster, it will
# act according to the class.
BEHAVIORS_BY_ID = {}
def behavior(behavior_id):
  def dec(cls):
    BEHAVIORS_BY_ID[behavior_id] = cls
    return cls
  return dec


# Behaviors are just event listeners with entities and levels attached! When an
# event fires, the dispatcher calls the appropriate method, and the behavior
# can do whatever it wants with Entity + LevelState.
class Behavior:
  def __init__(self, entity, level_state, event_names):
    self.event_names = event_names
    self._entity = weakref.ref(entity)
    self._level_state = weakref.ref(level_state)

  @property
  def entity(self):
    return self._entity()

  @property
  def level_state(self):
    return self._level_state()

  def add_to_event_dispatcher(self, dispatcher):
    for name in self.event_names:
      # Subscribe to events for all entities.
      # This is a pretty "meh" design decision and the biggest shortcoming of
      # the behavior system.
      dispatcher.add_subscriber(self, name, None)

  def remove_from_event_dispatcher(self, dispatcher):
    for name in self.event_names:
      dispatcher.remove_subscriber(self, name, None)


# There is a significant shortcoming in the event handling system: if you want
# one event to prevent others from firing, you basically can't! Or if you want
# several handlers to try to "match" an event, one after the other. For
# example, "If I can see the player, move toward them. Otherwise move randoly."
#
# That logic could be written in a single behavior, but it's more powerful to
# solve the problem generally. CompositeBehavior has a list of behaviors, and
# for each event, it calls its sub-behaviors in order until one returns True.
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

    def handler(*args, **kwargs):
      for method in methods:
        if method(*args, **kwargs):
          return True
      return False
    return handler


# Superclass for behaviors that simply respond to the player's movements
class StandardEnemyBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [EnumEventNames.player_took_action])


@behavior('sleep')
class SleepBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, event):
    self.entity.mode = EnumMonsterMode.DEFAULT
    return True


# When an enemy is hit, it cannot move for 2 turns.
@behavior('stunnable')
class StunnableBehavior(Behavior):
  def __init__(self, entity, level_state):
    super().__init__(entity, level_state, [
      EnumEventNames.entity_attacked,
      EnumEventNames.player_took_action,
    ])

  # When this entity is attacked, go into the "stunned" state and start the
  # cooldown.
  # Other behaviors do not need to worry about the STUNNED state, because this
  # behavior pre-empts them by returning True if the entity is stunned.
  def on_entity_attacked(self, event):
    if event.entity is not self.entity:
      return False
    self.entity.behavior_state['stun_cooldown'] = 2
    self.entity.mode = EnumMonsterMode.STUNNED

  # Decrease the cooldown when the player moves.
  def on_player_took_action(self, event):
    cooldown = self.entity.behavior_state.get('stun_cooldown', 0)
    if cooldown:
      self.entity.behavior_state['stun_cooldown'] -= 1
      return True
    else:
      return False


@behavior('random_walk')
class RandomWalkBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, event):
    if self.entity.position.manhattan_distance_to(self.level_state.player.position) > 40:
      self.entity.mode = EnumMonsterMode.SLEEPING
      return True

    self.entity.mode = EnumMonsterMode.DEFAULT
    possibilities = self.level_state.get_passable_neighbors(self.entity)
    if not possibilities:
      return False
    action_move(self.level_state, self.entity, random.choice(possibilities))
    return True


@behavior('pick_up_rocks')
class PickUpRocksBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, event):
    possibilities = self.level_state.get_passable_neighbors(self.entity)
    if not possibilities:
      return False
    self.entity.mode = EnumMonsterMode.DEFAULT

    for i in self.level_state.get_items_at(self.entity.position):
      if i.item_type.id == 'ROCK':
        action_pickup_item(self.level_state, self.entity)
        return True

    for p in possibilities:
      for i in self.level_state.get_items_at(p):
        if i.item_type.id == 'ROCK':
          action_move(self.level_state, self.entity, p)
          return True
    return False


# If there is a clear line of sight to the player, move into the neighboring
# cell closest to them.
#
# Distance is measured in "manhattan distance," which does not count diagonals!
# This is technically suboptimal, but in this game I erred on the side of
# making the game easier.
@behavior('beeline_visible')
class BeelineBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, event):
    if not self.level_state.test_line_of_sight(self.entity, self.level_state.player):
      return False

    candidates = self.level_state.get_passable_neighbors(self.entity, allow_player=True)
    if not candidates:
      return False

    self.entity.mode = EnumMonsterMode.CHASING

    point = self.level_state.player.position.get_closest_point(candidates)
    action_move(self.level_state, self.entity, point)
    return True


# Stay precisely 5 tiles away from the player. Great for ranged enemies! Not
# the smartest possible AI, but decent for Ludum Dare...
@behavior('range_5_visible')
class Range5VisibleBehavior(StandardEnemyBehavior):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.best_range = 5

  def on_player_took_action(self, event):
    if not self.level_state.test_line_of_sight(
        self.entity, self.level_state.player):
      return False

    candidates = self.level_state.get_passable_neighbors(self.entity)
    if not candidates:
      return False

    dist = self.entity.position.manhattan_distance_to(
      self.level_state.player.position)

    # Because manhattan distance does not map to our actual possible moves,
    # allow for a one-tile margin
    if dist < self.best_range - 1:
      self.entity.mode = EnumMonsterMode.FLEEING
      action_move(self.level_state,
        self.entity, self.level_state.player.position.get_farthest_point(candidates))
      return True
    elif dist > self.best_range:
      self.entity.mode = EnumMonsterMode.CHASING
      action_move(self.level_state,
        self.entity, self.level_state.player.position.get_closest_point(candidates))
      return True
    else:
      return False  # probably cascade to some kind of ranged attack


# Same as previous but with 7 tiles instead of 5, to make it harder, or at
# least different.
@behavior('range_7_visible')
class Range7VisibleBehavior(Range5VisibleBehavior):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.best_range = 7


# If the player is visible, throw a rock at them!
#
# At this point we've defined the complete AI for wibbles:
#
# * If stunned, wait for cooldown
# * If player is visible and we are not X tiles away from them, move toward
#   that goal
# * If player is visible and we are X tiles away from them, throw a rock
# * If player cannot be seen, sleep
@behavior('throw_rock_slow')
class ThrowRockSlowBehavior(StandardEnemyBehavior):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.rock_speed = 1

  def on_player_took_action(self, event):
    if not self.level_state.test_line_of_sight(self.entity, self.level_state.player):
      return False

    self.entity.behavior_state.setdefault('throw_rock_cooldown', 1)
    self.entity.behavior_state['throw_rock_cooldown'] -= 1

    if self.entity.behavior_state['throw_rock_cooldown'] <= 0:
      try:
        item = next(item for item in self.entity.inventory if item.item_type.id == 'ROCK')
      except StopIteration:
        item = None
      if not item:
        print("Can't throw, no more rocks in inventory")
        return False

      self.entity.behavior_state['throw_rock_cooldown'] = 6
      action_throw(self.level_state,
        self.entity, item, self.level_state.player.position, self.rock_speed)


# Thrown rocks are entities! This behavior moves them along a predetermined
# set of points (computed when the rock was thrown) until they it the end of
# their path, or they are attacked. 
@behavior('path_until_hit')
class PathUntilHitBehavior(StandardEnemyBehavior):
  def on_player_took_action(self, event, iterations_left=None):
    if iterations_left is None:
      iterations_left = self.entity.behavior_state['speed']
    iterations_left -= 1
    if iterations_left < 0:
      return False
    # the item to drop at the end must be the entity's only inventory item.

    p = self.entity.position
    if not self.entity.behavior_state.get('path', None):
      self.level_state.drop_item(self.entity.inventory.pop(0), p, entity=self.entity)
      self.level_state.remove_entity(self.entity)
      return True

    next_point = self.entity.behavior_state['path'].pop(0)
    if next_point is None:
      # this is basically a "wait" instruction
      return True

    entity_to_hit = self.level_state.get_entity_at(next_point)
    if entity_to_hit:
      p = entity_to_hit.position
      action_attack(self.level_state, self.entity, entity_to_hit)
    elif self.level_state.get_is_terrain_passable(next_point):
      action_move(self.level_state, self.entity, next_point)
      return True

    self.level_state.drop_item(self.entity.inventory.pop(0), p, entity=self.entity)
    self.level_state.remove_entity(self.entity)

    self.on_player_took_action(event, iterations_left - 1)
    return True
