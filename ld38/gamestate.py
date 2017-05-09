from collections import deque, defaultdict
from uuid import uuid4

from clubsandwich.event_dispatcher import EventDispatcher
from clubsandwich.geom import Size, Point
from clubsandwich.tilemap import TileMap, Cell, CellOutOfBoundsError
from clubsandwich.line_of_sight import get_visible_points

from .entity import Entity, Item
from .behavior import (
  CompositeBehavior,
  BEHAVIORS_BY_ID,
)
from .level_generator import generate_dungeon
from .const import (
  EnumEventNames,
  terrain_types,
  monster_types,
  item_types,
)


LEVEL_SIZE = Size(100, 60)


class RogueBasementCell(Cell):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.room_id = None
    self.terrain = terrain_types.EMPTY


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
    # HACK: score stored on level instead of game
    self.score = 0
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
      monster_types.PLAYER,
      self.tilemap.points_of_interest['stairs_up'])

    for item_data in self.tilemap.points_of_interest['items']:
      self.drop_item(Item(item_data.item_type), item_data.position)

    for monster_data in self.tilemap.points_of_interest['monsters']:
      self.create_entity(monster_data.monster_type, monster_data.position)

    self.level_memory_cache = set()
    self.update_los_cache()

  def update_los_cache(self):
    self.los_cache = get_visible_points(self.player.position, self.get_can_see)
    self.level_memory_cache.update(self.los_cache)

  def create_entity(self, monster_type, position, behavior_state=None):
    mt = monster_type
    if mt.id == 'PLAYER':
      assert self.player is None

    assert position not in self.entity_by_position

    entity = Entity(monster_type=mt)
    entity.position = position
    entity.behavior_state = behavior_state or {}

    for it_id in entity.monster_type.items:
      entity.inventory.append(Item(item_types[it_id]))

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

  ### event stuff ###

  def fire(self, name, data=None, entity=None):
    self.event_queue.append((name, entity, data))

  def consume_events(self):
    assert not self._is_applying_events
    self._is_applying_events = True
    while self.event_queue:
      (name, entity, data) = self.event_queue.popleft()
      self.dispatcher.fire(name, entity, data)
    self._is_applying_events = False

  ### action helper methods ###

  def get_can_player_see(self, point):
    return point in self.los_cache

  def get_can_player_remember(self, point):
    return point in self.level_memory_cache

  def test_line_of_sight(self, source, dest):  # both args are entities
    # always fail LOS when far away
    if source.position is None or dest.position is None:
      return False  # someone is dead, so you can't see them of course
    if source.position.manhattan_distance_to(dest.position) > 20:
      return False

    for point in source.position.points_bresenham_to(dest.position):
      if not self.get_can_see(point):
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
      return self.tilemap.cell(point).terrain.walkable
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
    return cell.terrain.walkable

  def get_can_see(self, position):
    try:
      cell = self.tilemap.cell(position)
      return cell.terrain.lightable
    except CellOutOfBoundsError:
      return False

  def get_can_open_door(self, entity):
    return entity.is_player

  def get_passable_neighbors(self, entity, allow_player=True):
    return [
      p for p in
      list(entity.position.neighbors) + list(entity.position.diagonal_neighbors)
      if self.get_can_move(entity, p, allow_player=True)]

  def fire_player_took_action_if_alive(self, position):
    if self.player.position is None:
      return
    self.fire(EnumEventNames.player_took_action, data=position, entity=None)


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
