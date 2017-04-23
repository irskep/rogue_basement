from collections import deque, defaultdict
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap, Cell, CellOutOfBoundsError

from .entity import Entity, Player
from .behavior import (
  KeyboardMovementBehavior,
  RandomWalkBehavior,
  BeelineBehavior,
  CompositeBehavior,
)
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
    self.occupied_cells = set()

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
    self.entity_by_position = {}
    self._is_applying_events = False

    self.dispatcher = EventDispatcher()
    for name in EnumEventNames:
      self.dispatcher.register_event_type(name)

    self.player = Player()
    self.player.position = self.tilemap.points_of_interest['stairs_up']
    self.player.add_behavior(KeyboardMovementBehavior(self.player, self))
    self.add_entity(self.player)

    for monster_data in self.tilemap.points_of_interest['monsters']:
      entity = Entity(kind=monster_data.kind)
      entity.stats = {'hp_max': 10 * (monster_data.difficulty + 1), 'strength': 2}
      entity.state = {'hp': entity.stats['hp_max']}
      entity.position = monster_data.position
      if entity.kind == EnumEntityKind.VERP:
        entity.add_behavior(CompositeBehavior(entity, self, [
          BeelineBehavior(entity, self),
          RandomWalkBehavior(entity, self),
        ]))
      self.add_entity(entity)

  def add_entity(self, entity):
    self.entities.append(entity)
    for behavior in entity.behaviors:
      behavior.add_to_event_dispatcher(self.dispatcher)
    if entity.position:
      self.entity_by_position[entity.position] = entity

  def remove_entity(self, entity):
    self.entities.remove(entity)
    for behavior in entity.behaviors:
      behavior.remove_from_event_dispatcher(self.dispatcher)
    if entity.position:
      del self.entity_by_position[entity.position]

  @property
  def active_rooms(self):
    return self.tilemap.get_room(self.player.position)  # for now

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

  def test_line_of_sight(self, source, dest):  # both args are entities
    for point in source.position.points_bresenham_to(dest.position):
      if not self.get_can_see(source, point):
        return False
    return True
  
  def get_entity_at(self, position):
    try:
      return self.entity_by_position[position]
    except KeyError:
      return None

  def get_can_move(self, entity, position):
    # disallow swapping and such for now
    if position in self.entity_by_position:
      return False

    cell = self.tilemap.cell(position)
    return get_is_terrain_passable(cell.terrain)

  def get_can_see(self, entity, position):
    cell = self.tilemap.cell(position)
    return get_is_terrain_passable(cell.terrain)

  def get_can_open_door(self, entity):
    return entity.kind == EnumEntityKind.PLAYER

  def action_close(self, entity, position):
    try:
      cell = self.tilemap.cell(position)
    except CellOutOfBoundsError:
      return False
    if cell.terrain != EnumTerrain.DOOR_OPEN:
      return False
    cell.terrain = EnumTerrain.DOOR_CLOSED
    self.fire(EnumEventNames.player_took_action, data=position, entity=None)
    return True

  def action_player_move(self, entity, position):
    cell = self.tilemap.cell(position)

    target_entity = self.get_entity_at(position)
    if target_entity:
      self.action_attack(entity, target_entity)
      self.fire(EnumEventNames.player_took_action, data=position, entity=None)
      return True

    if self.get_can_move(entity, position):
      del self.entity_by_position[entity.position]
      entity.position = position
      self.entity_by_position[position] = entity
      self.fire(EnumEventNames.entity_moved, data=entity, entity=entity)
      self.fire(EnumEventNames.player_took_action, data=position, entity=None)
      return True
    elif cell.terrain == EnumTerrain.DOOR_CLOSED and self.get_can_open_door(entity):
      self.open_door(entity, position)
      self.fire(EnumEventNames.player_took_action, data=position, entity=None)
      return True
    else:
      self.fire(EnumEventNames.entity_bumped, data=cell, entity=entity)
      return False

  def action_monster_move(self, entity, position):
    cell = self.tilemap.cell(position)

    target_entity = self.get_entity_at(position)
    if target_entity:
      if target_entity == self.player:
        self.action_attack(entity, target_entity)
      else:
        return False  # it's another monster

    if self.get_can_move(entity, position):
      del self.entity_by_position[entity.position]
      entity.position = position
      self.entity_by_position[position] = entity
      self.fire(EnumEventNames.entity_moved, data=entity, entity=entity)
      return True
    elif cell.terrain == EnumTerrain.DOOR_CLOSED and self.get_can_open_door(entity):
      self.open_door(entity, position)
      return True
    else:
      return False

  def action_attack(self, a, b):
    self.fire(EnumEventNames.entity_attacking, data=b, entity=a)
    self.fire(EnumEventNames.entity_attacked, data=a, entity=b)
    print(a.stats, b.state)
    b.state['hp'] -= a.stats['strength']
    self.fire(EnumEventNames.entity_took_damage, data=a, entity=b)
    if b.state['hp'] <= 0:
      self.fire(EnumEventNames.entity_died, data=None, entity=b)
      self.remove_entity(b)

  def open_door(self, entity, position):
    # this is where the logic goes for doors that are hard to open.
    cell = self.tilemap.cell(position)
    cell.terrain = EnumTerrain.DOOR_OPEN
    self.fire(EnumEventNames.door_open, data=cell, entity=entity)

  def action_die(self):
    self.fire(EnumEventNames.player_died)


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
