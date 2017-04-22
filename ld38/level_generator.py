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
  for (a, b) in root.sibling_pairs:
    a = a.leftmost_leaf
    b = b.rightmost_leaf
    (doors, corridors) = generate_random_path(
      tilemap,
      a.data['room'].rect.with_inset(1),
      b.data['room'].rect.with_inset(1))
    iter_count = 0
    while len(doors) > 4 and iter_count < 10:
      iter_count += 1
      (doors, corridors) = generate_random_path(
        tilemap,
        a.data['room'].rect.with_inset(1),
        b.data['room'].rect.with_inset(1))
    for door in doors:
      door.terrain = EnumTerrain.DOOR_OPEN if DEBUG_ALL_DOORS_OPEN else EnumTerrain.DOOR_CLOSED
    for corridor in corridors:
      corridor.terrain = EnumTerrain.CORRIDOR


def generate_dungeon(tilemap):
  generator = RandomBSPTree(tilemap.size, 4)
  rooms = [generate_room(leaf) for leaf in generator.root.leaves]
  points_of_interest = {}
  engrave_rooms(tilemap, rooms)  
  generate_and_engrave_corridors(tilemap, generator.root)

  stair_candidate_pairs = [
    (generator.root.random_leaf.data['room'].rect.with_inset(2).get_random_point(),
     generator.root.random_leaf.data['room'].rect.with_inset(2).get_random_point())
    for _ in range(10)
  ]
  (stairs_up, stairs_down) = stair_candidate_pairs[0]
  best_distance = stairs_up.manhattan_distance_to(stairs_down)
  for (a, b) in stair_candidate_pairs:
    if a.manhattan_distance_to(b) > best_distance:
      (stairs_up, stairs_down) = (a, b)
  points_of_interest['stairs_up'] = stairs_up
  points_of_interest['stairs_down'] = stairs_down

  tilemap.cell(points_of_interest['stairs_up']).feature = EnumFeature.STAIRS_UP
  tilemap.cell(points_of_interest['stairs_down']).feature = EnumFeature.STAIRS_DOWN

  return points_of_interest
