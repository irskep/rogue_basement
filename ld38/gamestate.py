import weakref
from collections import deque
from enum import Enum
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap

from .level_generator import generate_dungeon
from .const import EnumEntityKind, EnumEventNames


LEVEL_SIZE = Size(80, 25)


class EventDispatcher:
  def __init__(self):
    self.handlers = {}

  def register_event_type(self, name):
    if isinstance(name, Enum):
      name = name.value
    self.handlers[name] = []

  def add_subscriber(self, obj, name, entity):
    if isinstance(name, Enum):
      name = name.value
    self.handlers[name].append((obj, entity))

  def remove_subscriber(self, obj, name):
    if isinstance(name, Enum):
      name = name.value
    self.handlers[name].remove((obj, entity))

  def fire(self, name, data, entity):
    if isinstance(name, Enum):
      name = name.value
    method_name = "on_" + name.lower()
    for (obj, inner_entity) in self.handlers[name]:
      if entity is None or inner_entity is None or entity is inner_entity:
        getattr(obj, method_name)(data)


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


class Entity:
  def __init__(self, kind):
    self.kind = kind
    self.stats = {}
    self.state = {}
    self.position = None
    self.behaviors = []

  def add_behavior(self, factory):
    self.behaviors.append(factory(self))

  def __repr__(self):
    return self.__class__.__name__


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
    self.event_queue = deque()
    self._is_applying_events = False

    self.dispatcher = EventDispatcher()
    for name in EnumEventNames:
      self.dispatcher.register_event_type(name)

    self.player = Player()
    self.player.position = self.level.points_of_interest['stairs_up']
    self.player.add_behavior(lambda entity: KeyboardMovementBehavior(entity, self))
    self.player.add_behavior(lambda entity: MovementBehavior(entity, self))
    self.add_entity(self.player)

  def add_entity(self, entity):
    self.entities.append(entity)
    for behavior in entity.behaviors:
      behavior.add_to_event_dispatcher(self.dispatcher)

  def remove_entity(self, entity):
    self.entities.remove(entity)
    for behavior in entity.behaviors:
      behavior.remove_from_event_dispatcher(self.dispatcher)

  ### event stuff ###

  def fire(self, name, data=None, entity=None):
    self.event_queue.append((name, data, entity))

  def consume_events(self):
    assert not self._is_applying_events
    self._is_applying_events = True
    while self.event_queue:
      (name, data, entity) = self.event_queue.popleft()
      print(name.value, data, entity)
      self.dispatcher.fire(name, data, entity)
    self._is_applying_events = False

  ### actions ###

  def move(self, entity, position):
    # TODO: uh lol there are walls and stuff
    entity.position = position


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
