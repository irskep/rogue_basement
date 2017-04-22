from collections import deque, defaultdict
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap, Cell

from .entity import Entity, Player
from .behavior import KeyboardMovementBehavior, MovementBehavior
from .level_generator import generate_dungeon
from .const import EnumEntityKind, EnumEventNames, EnumTerrain
from .dispatcher import EventDispatcher


LEVEL_SIZE = Size(160, 80)


def get_is_terrain_passable(terrain):
  return terrain in (EnumTerrain.FLOOR, EnumTerrain.CORRIDOR, EnumTerrain.DOOR_OPEN)


class RogueBasementCell(Cell):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.room_id = None


class RogueBasementTileMap(TileMap):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, cell_class=RogueBasementCell, **kwargs)
    self.rooms_by_id = {}
    self.cells_by_room_id = defaultdict(list)

  def assign_room(self, point, room_id):
    cell = self.cell(point)
    assert not cell.room_id
    cell.room_id = room_id
    self.cells_by_room_id[room_id].append(cell)

  def get_neighbors(self, room):
    return [self.rooms_by_id[room_id] for room_id in room.neighbor_ids]

  def get_room(self, point):
    return self.rooms_by_id[self.cell(point).room_id]


class LevelState:
  def __init__(self, tilemap):
    self.tilemap = tilemap
    self.uuid = uuid4().hex
    self.entities = []
    self.event_queue = deque()
    self._is_applying_events = False

    self.dispatcher = EventDispatcher()
    for name in EnumEventNames:
      self.dispatcher.register_event_type(name)

    self.player = Player()
    self.player.position = self.tilemap.points_of_interest['stairs_up']
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

  @property
  def visible_room_ids(self):
    player_room = self.tilemap.get_room(self.player.position)
    return {player_room.room_id} | player_room.neighbor_ids

  @property
  def active_rooms(self):
    return self.visible_rooms  # for now

  ### event stuff ###

  def fire(self, name, data=None, entity=None):
    self.event_queue.append((name, data, entity))

  def consume_events(self):
    assert not self._is_applying_events
    self._is_applying_events = True
    while self.event_queue:
      (name, data, entity) = self.event_queue.popleft()
      self.dispatcher.fire(name, data, entity)
    self._is_applying_events = False

  ### actions ###

  def move(self, entity, position):
    cell = self.tilemap.cell(position)
    if get_is_terrain_passable(cell.terrain):
      entity.position = position
      self.fire(EnumEventNames.entity_moved, data=entity, entity=entity)
    elif cell.terrain == EnumTerrain.DOOR_CLOSED:
      self.open_door(entity, position)
    else:
      self.fire(EnumEventNames.entity_bumped, data=cell, entity=entity)

  def open_door(self, entity, position):
    # this is where the logic goes for doors that are hard to open.
    cell = self.tilemap.cell(position)
    cell.terrain = EnumTerrain.DOOR_OPEN
    self.fire(EnumEventNames.door_open, data=cell, entity=entity)


class GameState:
  def __init__(self):
    self.turn_number = 0
    self.level_states_by_id = {}

    self.active_id = self.add_level().uuid

  @property
  def active_level_state(self):
    return self.level_states_by_id[self.active_id]

  def add_level(self):
    level_state = LevelState(generate_dungeon(RogueBasementTileMap(LEVEL_SIZE)))
    self.level_states_by_id[level_state.uuid] = level_state
    return level_state
