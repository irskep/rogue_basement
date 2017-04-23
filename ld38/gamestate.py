from collections import deque, defaultdict
from uuid import uuid4

from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap, Cell, CellOutOfBoundsError

from .entity import Entity, Item
from .behavior import (
  CompositeBehavior,
  BEHAVIORS_BY_ID,
)
from .level_generator import generate_dungeon
from .const import (
  EnumEventNames,
  EnumTerrain,
  MONSTER_TYPES_BY_ID,
  ITEM_TYPES_BY_ID,
)
from .dispatcher import EventDispatcher


LEVEL_SIZE = Size(100, 60)


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
    room_id = self.cell(point).room_id
    if room_id is None:
      return None
    return self.rooms_by_id[room_id]


class LevelState:
  def __init__(self, tilemap):
    self.tilemap = tilemap
    self.uuid = uuid4().hex
    self.entities = []
    self.event_queue = deque()
    self.entity_by_position = {}
    self.items_by_position = {}
    self._is_applying_events = False

    self.dispatcher = EventDispatcher()
    for name in EnumEventNames:
      self.dispatcher.register_event_type(name)

    self.player = None
    self.player = self.create_entity(
      MONSTER_TYPES_BY_ID['PLAYER'],
      self.tilemap.points_of_interest['stairs_up'])

    for item_data in self.tilemap.points_of_interest['items']:
      self.drop_item(Item(item_data.item_type), item_data.position)

    for monster_data in self.tilemap.points_of_interest['monsters']:
      self.create_entity(monster_data.monster_type, monster_data.position)

  def create_entity(self, monster_type, position, behavior_state=None):
    mt = monster_type
    if mt.id == 'PLAYER':
      assert self.player is None

    assert position not in self.entity_by_position

    entity = Entity(monster_type=mt)
    entity.position = position
    entity.behavior_state = behavior_state or {}

    for it_id in entity.monster_type.items:
      entity.inventory.append(Item(ITEM_TYPES_BY_ID[it_id]))

    if len(mt.behaviors) == 1:
      entity.add_behavior(BEHAVIORS_BY_ID[mt.behaviors[0]](entity, self))
    else:
      entity.add_behavior(CompositeBehavior(entity, self, [
        BEHAVIORS_BY_ID[behavior_id](entity, self)
        for behavior_id in mt.behaviors]))
    self.add_entity(entity)
    return entity

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
      entity.position = None

  def drop_item(self, item, point, entity=None):
    self.items_by_position.setdefault(point, [])
    self.items_by_position[point].append(item)
    if entity is not None:
      self.fire(EnumEventNames.entity_dropped_item, data=item, entity=entity)
    return True

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
    # always fail LOS when far away
    if source.position is None or dest.position is None:
      return False  # someone is dead, so you can't see them of course
    if source.position.manhattan_distance_to(dest.position) > 20:
      return False

    for point in source.position.points_bresenham_to(dest.position):
      if not self.get_can_see(source, point):
        return False
    return True

  def get_entity_at(self, position):
    try:
      return self.entity_by_position[position]
    except KeyError:
      return None

  def get_items_at(self, position):
    try:
      return self.items_by_position[position]
    except KeyError:
      return []

  def get_is_terrain_passable(self, point):
    try:
      return get_is_terrain_passable(self.tilemap.cell(point).terrain)
    except CellOutOfBoundsError:
      return False

  def get_can_move(self, entity, position, allow_player=False):
    # disallow swapping and such for now
    try:
      if self.entity_by_position[position] == self.player and not allow_player:
        return False
      elif self.entity_by_position[position] != self.player:
        return False
    except KeyError:
      pass

    try:
      cell = self.tilemap.cell(position)
    except CellOutOfBoundsError:
      return False
    return get_is_terrain_passable(cell.terrain)

  def get_can_see(self, entity, position):
    cell = self.tilemap.cell(position)
    return get_is_terrain_passable(cell.terrain)

  def get_can_open_door(self, entity):
    return entity.is_player

  def get_passable_neighbors(self, entity, allow_player=True):
    return [
      p for p in
      list(entity.position.neighbors) + list(entity.position.diagonal_neighbors)
      if self.get_can_move(entity, p, allow_player=True)]

  def _fire_player_took_action_if_alive(self, position):
    if self.player.position is None:
      return
    self.fire(EnumEventNames.player_took_action, data=position, entity=None)

  def action_close(self, entity, position):
    try:
      cell = self.tilemap.cell(position)
    except CellOutOfBoundsError:
      return False
    if cell.terrain != EnumTerrain.DOOR_OPEN:
      return False
    cell.terrain = EnumTerrain.DOOR_CLOSED
    self._fire_player_took_action_if_alive(position)
    return True

  def action_throw(self, entity, item, target_position, speed):
    entity.inventory.remove(item)

    path = list(entity.position.points_bresenham_to(target_position))
    while self.get_entity_at(path[0]) == entity:
      path.pop(0)
    entity_in_the_way = self.get_entity_at(path[0])
    if (not entity.is_player and
        entity_in_the_way and
        not entity_in_the_way.is_player):
      return False

    mk_id = item.item_type.id + '_IN_FLIGHT'
    rock_in_flight = self.create_entity(MONSTER_TYPES_BY_ID[mk_id], path[0], {
      'path': [None] + path[1:],  # behavior executes immediately but rock is already placed
      'speed': speed,
    })
    rock_in_flight.inventory.append(item)
    
    if entity.is_player:
      self._fire_player_took_action_if_alive(entity.position)
    return True

  def action_player_move(self, entity, position):
    cell = self.tilemap.cell(position)

    target_entity = self.get_entity_at(position)
    if target_entity:
      self.action_attack(entity, target_entity)
      self._fire_player_took_action_if_alive(position)
      return True

    if self.get_can_move(entity, position):
      del self.entity_by_position[entity.position]
      entity.position = position
      self.entity_by_position[position] = entity
      self.fire(EnumEventNames.entity_moved, data=entity, entity=entity)
      self._fire_player_took_action_if_alive(position)
      return True
    elif cell.terrain == EnumTerrain.DOOR_CLOSED and self.get_can_open_door(entity):
      self.open_door(entity, position)
      self._fire_player_took_action_if_alive(position)
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
        return True
      else:
        return False  # it's another monster

    if self.get_can_move(entity, position):
      try:
        del self.entity_by_position[entity.position]
      except KeyError:
        import pudb; pu.db()
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
      if b.is_player:
        print("Aborting all events due to player death")
        self.dispatcher._force_abandon_current_events = True

  def action_pickup_item(self, entity):
    try:
      items = self.items_by_position[entity.position]
    except KeyError:
      return False
    for item in items:
      item.position = None
      entity.inventory.extend(items)
      del self.items_by_position[entity.position]
      self.fire(EnumEventNames.entity_picked_up_item, data=item, entity=entity)

  def open_door(self, entity, position):
    # this is where the logic goes for doors that are hard to open.
    cell = self.tilemap.cell(position)
    cell.terrain = EnumTerrain.DOOR_OPEN
    self.fire(EnumEventNames.door_open, data=cell, entity=entity)

  def action_die(self):
    self.fire(EnumEventNames.entity_died, data=None, entity=self.player)


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
