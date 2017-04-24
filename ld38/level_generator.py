from collections import namedtuple
from math import floor
from random import randrange, uniform
from uuid import uuid4

from .const import (
  EnumTerrain,
  EnumFeature,
  EnumRoomShape,
  ROOM_TYPES,
  MONSTER_TYPES_BY_ID,
  ITEM_TYPES_BY_ID,
)

from clubsandwich.geom import Rect, Point, Size
from clubsandwich.generators import RandomBSPTree
from clubsandwich.tilemap import TileMap, CellOutOfBoundsError


DEBUG_ALL_DOORS_OPEN = False


def weighted_choice(choices):
  """``[(choice, weight)]``"""
  total = sum(w for c, w in choices)
  r = uniform(0, total)
  upto = 0
  for c, w in choices:
    if w == 0:
      continue
    if upto + w >= r:
      return c
    upto += w
  assert False, "Shouldn't get here"


class Room:
  def __init__(self, rect, room_type):
    self.room_id = uuid4().hex
    self.room_type = room_type
    self.neighbor_ids = set()
    self.difficulty = None

    if room_type.shape == EnumRoomShape.BOX_RANDOM:
      self.rect = rect.get_random_rect(Size(5, 5))
    if room_type.shape == EnumRoomShape.BOX_FULL:
      self.rect = rect


def _get_difficulty(bsp_leaf, difficulty_map):
  for ancestor in bsp_leaf.ancestors:
    for (k, v) in difficulty_map.items():
      if v == ancestor:
        return k
  raise ValueError("Cannot determine difficulty for this room")


def generate_room(bsp_leaf, difficulty_map):
  """Decorate ``bsp_leaf`` with a :py:class:`Room` object"""
  difficulty = _get_difficulty(bsp_leaf, difficulty_map)

  room_type_options = [
    rt for rt in ROOM_TYPES if rt.difficulty is None or rt.difficulty == difficulty]

  bsp_leaf.data['room'] = Room(
    bsp_leaf.rect,
    weighted_choice([(rt, rt.chance) for rt in room_type_options]))
  return bsp_leaf.data['room']


def get_room_nearest(leaves, target_point):
  leaves = list(leaves)
  room = leaves[0].data['room']
  distance = room.rect.center.manhattan_distance_to(target_point)
  for leaf in leaves:
    inner_room = leaf.data['room']
    inner_distance = inner_room.rect.center.manhattan_distance_to(target_point)
    if inner_distance < distance:
      room = inner_room
      distance = inner_distance
  return room


def generate_random_path(tilemap, rect1, rect2):
  start = rect1.get_random_point()
  end = rect2.get_random_point()
  points_in_path = set()
  doors = set()
  corridors = set()
  for point in start.path_L_to(end):
    points_in_path.add(point)
    has_corridor_neighbor = False
    for neighbor in point.neighbors:
      if neighbor in points_in_path:
        continue
      try:
        has_corridor_neighbor = tilemap.cell(neighbor).terrain == EnumTerrain.CORRIDOR
      except CellOutOfBoundsError:
        pass
      if has_corridor_neighbor:
        continue
    cell = tilemap.cell(point)
    if cell.terrain == EnumTerrain.WALL:
      doors.add(cell)
    elif (cell.terrain == EnumTerrain.EMPTY or not cell.terrain) and not has_corridor_neighbor:
      corridors.add(cell)
  return (doors, corridors)


def engrave_rooms(tilemap, rooms):
  for room in rooms:
    tilemap.rooms_by_id[room.room_id] = room
    for corner in room.rect.points_corners:
      tilemap.cell(corner).terrain = EnumTerrain.WALL
    tilemap.cell(room.rect.origin).annotations.add('corner_top_left')
    tilemap.cell(room.rect.point_top_right).annotations.add('corner_top_right')
    tilemap.cell(room.rect.point_bottom_left).annotations.add('corner_bottom_left')
    tilemap.cell(room.rect.point_bottom_right).annotations.add('corner_bottom_right')

    for point in room.rect.points_top:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('horz')
    for point in room.rect.points_bottom:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('horz')
    for point in room.rect.points_left:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('vert')
    for point in room.rect.points_right:
      tilemap.cell(point).terrain = EnumTerrain.WALL
      tilemap.cell(point).annotations.add('vert')
    for point in room.rect.with_inset(1).points:
      tilemap.cell(point).terrain = EnumTerrain.FLOOR

    for point in room.rect.points:
      tilemap.assign_room(point, room.room_id)


def generate_and_engrave_corridors(tilemap, root):
  # generate corridors between rooms WITHIN a quadrant
  sibling_pairs = [(a, b) for (a, b) in root.sibling_pairs if a.level > 2 and b.level > 2]
  for (a, b) in sibling_pairs:
    engrave_corridor_between_rooms(tilemap, a.leftmost_leaf.data['room'], b.leftmost_leaf.data['room'])

  # generate corridors between quadrants
  room_aa_bottom = get_room_nearest(
    root.get_node_at_path('aa').leaves,
    Point(0, tilemap.size.height / 2))
  room_ab_top = get_room_nearest(
    root.get_node_at_path('ab').leaves,
    room_aa_bottom.rect.center)
  engrave_corridor_between_rooms(tilemap, room_aa_bottom, room_ab_top, 'transition-1-2')

  room_ab_right = get_room_nearest(
    root.get_node_at_path('ab').leaves,
    Point(tilemap.size.width / 2, tilemap.size.height))
  room_bb_left = get_room_nearest(
    root.get_node_at_path('bb').leaves,
    room_ab_right.rect.center)
  engrave_corridor_between_rooms(tilemap, room_ab_right, room_bb_left, 'transition-2-3')

  room_bb_top = get_room_nearest(
    root.get_node_at_path('bb').leaves,
    Point(tilemap.size.width, tilemap.size.height / 2))
  room_ba_bottom = get_room_nearest(
    root.get_node_at_path('ba').leaves,
    room_bb_top.rect.center)
  engrave_corridor_between_rooms(tilemap, room_bb_top, room_ba_bottom, 'transition-3-4')


def engrave_corridor_between_rooms(tilemap, a, b, annotation=None):
  (doors, corridors) = generate_random_path(
    tilemap,
    a.rect.with_inset(1),
    b.rect.with_inset(1))
  iter_count = 0
  while len(doors) > 4 and iter_count < 10:
    iter_count += 1
    (doors, corridors) = generate_random_path(
      tilemap,
      a.rect.with_inset(1),
      b.rect.with_inset(1))
  for door in doors:
    door.terrain = EnumTerrain.DOOR_OPEN if DEBUG_ALL_DOORS_OPEN else EnumTerrain.DOOR_CLOSED
  for corridor in corridors:
    corridor.terrain = EnumTerrain.CORRIDOR
    if annotation:
      corridor.annotations.add(annotation)


def engrave_bsp_divisions(tilemap, node):
  if node.level > 1:
    return
  if node.value:
    if node.is_horz:
      x = node.rect.x + node.value
      for y in range(node.rect.y, node.rect.y2 + 1):
        tilemap.cell(Point(x, y)).debug_character = '|'
    else:
      y = node.rect.y + node.value
      for x in range(node.rect.x, node.rect.x2 + 1):
        tilemap.cell(Point(x, y)).debug_character = '-'
  if node.child_a:
    engrave_bsp_divisions(tilemap, node.child_a)
  if node.child_b:
    engrave_bsp_divisions(tilemap, node.child_b)


def engrave_difficulty(root):
  for i, path in enumerate(['aa', 'ab', 'bb', 'ba']):
    for leaf in root.get_node_at_path(path).leaves:
      leaf.data['room'].difficulty = i


def get_can_add_monster_at_point(tilemap, point):
  if point in tilemap.occupied_cells:
    return False
  if tilemap.cell(point).feature is not None:
    return False
  return True



get_can_add_item_at_point = get_can_add_monster_at_point


MonsterData = namedtuple('MonsterData', ['monster_type', 'position', 'difficulty'])
def place_monsters(tilemap):
  monster_datas = []
  tilemap.points_of_interest['monsters'] = monster_datas 
  for room in tilemap.rooms_by_id.values():
    rt = room.room_type
    possible_monsters = list(MONSTER_TYPES_BY_ID.values()) if rt.monsters is None else [
      MONSTER_TYPES_BY_ID[mt_k] for mt_k in room.room_type.monsters]
    allowed_monster_types = [
      mt for mt in possible_monsters
      if mt.difficulty is None or mt.difficulty == room.difficulty]

    inner_rect = room.rect.with_inset(1)
    num_monsters = max(1, round(inner_rect.area * room.room_type.monster_density / 100.0))

    for _ in range(num_monsters):
      point = inner_rect.get_random_point()
      mt = weighted_choice([(mt, mt.chance) for mt in allowed_monster_types])

      i = 0
      while not get_can_add_monster_at_point(tilemap, point) and i < 10:
        point = inner_rect.get_random_point()
        i += 1
      if i >= 10:
        print("Unable to place monster; skipping")
        continue

      tilemap.occupied_cells.add(point)
      monster_datas.append(MonsterData(
        monster_type=mt, position=point, difficulty=room.difficulty))


ItemData = namedtuple('ItemData', ['item_type', 'position'])
def place_items(tilemap):
  item_datas = []
  tilemap.points_of_interest['items'] = item_datas 
  for room in tilemap.rooms_by_id.values():
    inner_rect = room.rect.with_inset(1)
    num_items = max(1, round(inner_rect.area * room.room_type.item_density / 100.0))

    ### HACK: spawn exactly one gold in each room ###
    for i in range(num_items + 1):
      point = inner_rect.get_random_point()
      it = weighted_choice([(it, it.chance_by_difficulty[room.difficulty]) for it in ITEM_TYPES_BY_ID.values()])

      if i == 0:
        it = ITEM_TYPES_BY_ID['GOLD']

      i = 0
      while not get_can_add_item_at_point(tilemap, point) and i < 10:
        point = inner_rect.get_random_point()
        i += 1
      if i >= 10:
        print("Unable to place item; skipping")
        continue

      tilemap.occupied_cells.add(point)
      item_datas.append(ItemData(item_type=it, position=point))


def _bsp_randrange(level, a, b):
  if level in (0, 1):
    return floor((a + b) / 2)
  else:
    return randrange(a, b)


def generate_dungeon(tilemap):
  generator = RandomBSPTree(tilemap.size, 4, randrange_func=_bsp_randrange)
  # difficulty: root node for _leaves of that difficulty_
  difficulty_map = {
    0: generator.root.get_node_at_path('aa'),
    1: generator.root.get_node_at_path('ab'),
    2: generator.root.get_node_at_path('bb'),
    3: generator.root.get_node_at_path('ba'),
  }
  rooms = [generate_room(leaf, difficulty_map) for leaf in generator.root.leaves]
  engrave_rooms(tilemap, rooms)  
  generate_and_engrave_corridors(tilemap, generator.root)

  stairs_up_room = get_room_nearest(
    generator.root.get_node_at_path('aa').leaves, Point(tilemap.size.width / 2, tilemap.size.height / 4))
  stairs_up = stairs_up_room.rect.with_inset(1).get_random_point()

  stairs_down_room = get_room_nearest(
    generator.root.get_node_at_path('ba').leaves, Point(tilemap.size.width / 2, 0))
  stairs_down = stairs_down_room.rect.with_inset(1).get_random_point()

  tilemap.points_of_interest['stairs_up'] = stairs_up
  tilemap.points_of_interest['stairs_down'] = stairs_down
  tilemap.occupied_cells.add(stairs_up)
  tilemap.occupied_cells.add(stairs_down)

  tilemap.cell(tilemap.points_of_interest['stairs_up']).feature = EnumFeature.STAIRS_UP
  tilemap.cell(tilemap.points_of_interest['stairs_down']).feature = EnumFeature.STAIRS_DOWN

  engrave_difficulty(generator.root)

  place_monsters(tilemap)
  place_items(tilemap)

  #engrave_bsp_divisions(tilemap, generator.root)
  return tilemap
