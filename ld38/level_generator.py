from math import floor
from random import randrange

from .const import EnumTerrain, EnumFeature

from clubsandwich.tilemap import CellOutOfBoundsError
from clubsandwich.geom import Rect, Point, Size
from clubsandwich.generators import RandomBSPTree
from clubsandwich.tilemap import TileMap, CellOutOfBoundsError


DEBUG_ALL_DOORS_OPEN = True


class Room:
  def __init__(self, rect):
    self.rect = rect


def generate_room(bsp_leaf):
  """Decorate *bsp_leaf* with a :py:class:`Room` object"""
  bsp_leaf.data['room'] = Room(bsp_leaf.rect.get_random_rect(Size(4, 4)))
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


def _bsp_randrange(level, a, b):
  if level in (0, 1):
    return floor((a + b) / 2)
  else:
    return randrange(a, b)


def generate_dungeon(tilemap):
  generator = RandomBSPTree(tilemap.size, 4, randrange_func=_bsp_randrange)
  rooms = [generate_room(leaf) for leaf in generator.root.leaves]
  points_of_interest = {}
  engrave_rooms(tilemap, rooms)  
  generate_and_engrave_corridors(tilemap, generator.root)

  stairs_up_room = get_room_nearest(
    generator.root.get_node_at_path('aa').leaves, Point(tilemap.size.width / 2, 0))
  stairs_up = stairs_up_room.rect.with_inset(2).get_random_point()

  stairs_down_room = get_room_nearest(
    generator.root.get_node_at_path('ba').leaves, Point(tilemap.size.width, 0))
  stairs_down = stairs_down_room.rect.with_inset(2).get_random_point()

  points_of_interest['stairs_up'] = stairs_up
  points_of_interest['stairs_down'] = stairs_down

  tilemap.cell(points_of_interest['stairs_up']).feature = EnumFeature.STAIRS_UP
  tilemap.cell(points_of_interest['stairs_down']).feature = EnumFeature.STAIRS_DOWN

  engrave_bsp_divisions(tilemap, generator.root)

  return points_of_interest
