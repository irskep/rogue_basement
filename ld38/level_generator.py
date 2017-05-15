# This is the largest file in Rogue Basement, and there's a lot going on,
# but it's easy to understand if you take it a bit at a time.
#
# In the comments, I will assume you've read my blog post which has some
# important information about the level generator:
# http://steveasleep.com/the-design-and-implementation-of-rogue-basement.html
from collections import namedtuple
from math import floor
from random import randrange, uniform
from uuid import uuid4

from clubsandwich.geom import Rect, Point, Size
# You should probably go read the docs for this:
# http://steveasleep.com/clubsandwich/api_generators.html
from clubsandwich.generators import RandomBSPTree
from clubsandwich.tilemap import CellOutOfBoundsError

from .const import (
  EnumFeature,
  EnumRoomShape,
  room_types,
  monster_types,
  item_types,
  terrain_types,
)
from .tilemap import RogueBasementCell, RogueBasementTileMap


def weighted_choice(choices):
  """``weighted_choice([(choice, weight)]) -> choice``"""
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


def _get_difficulty(bsp_leaf, difficulty_map):
  """
  *difficulty_map* is a dict mapping difficulty (int 1-4) to a BSPNode. Returns
  the difficulty of the given leaf, based on which difficulty_map value is its
  ancestor.
  """
  for ancestor in bsp_leaf.ancestors:
    for (k, v) in difficulty_map.items():
      if v == ancestor:
        return k
  raise ValueError("Cannot determine difficulty for this room")


class Room:
  """
  Represents a fully connected set of points. Mutually exclusive to other
  rooms.
  """
  def __init__(self, rect, room_type):
    self.room_id = uuid4().hex
    self.room_type = room_type
    # Corridors are always None, rooms are 1-4. Determined by quadrant, i.e.
    # 2nd-topmost ancestor.
    self.difficulty = None

    # If only I had had time to make more room shapes...
    if room_type.shape == EnumRoomShape.BOX_RANDOM:
      self.rect = rect.get_random_rect(Size(5, 5))
    if room_type.shape == EnumRoomShape.BOX_FULL:
      self.rect = rect


def generate_room(bsp_leaf, difficulty_map):
  """
  Decorate *bsp_leaf* with a Room object
  """
  difficulty = _get_difficulty(bsp_leaf, difficulty_map)

  assert(bsp_leaf.rect)

  room_type_options = [
    rt for rt in room_types.items
    if rt.difficulty is None or rt.difficulty == difficulty]

  bsp_leaf.data['room'] = Room(
    bsp_leaf.rect,
    weighted_choice([(rt, rt.chance) for rt in room_type_options]))
  return bsp_leaf.data['room']


def get_room_nearest(leaves, target_point):
  """
  From the iterable of leaves, find the room closes to the given point.
  This is used for placement of stairs and inter-quadrant special corridors.
  """
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


def engrave_rooms(tilemap, rooms):
  """
  Apply individual cell terrain values based on where we've decided all the
  rooms go. This involves setting cell "annotations" for walls so that
  draw_game() knows how to render pieces of walls.

  A better system for multiple wall types would be to base movement checks on
  terrain *characteristics* instead of the terrain type. Then there could just
  be multiple terrian types for walls and we wouldn't need this fancy
  "annotation" system.
  """
  for room in rooms:
    tilemap.rooms_by_id[room.room_id] = room
    for corner in room.rect.points_corners:
      tilemap.cell(corner).terrain = terrain_types.WALL
    tilemap.cell(room.rect.origin).annotations.add('corner_top_left')
    tilemap.cell(room.rect.point_top_right).annotations.add('corner_top_right')
    tilemap.cell(room.rect.point_bottom_left).annotations.add('corner_bottom_left')
    tilemap.cell(room.rect.point_bottom_right).annotations.add('corner_bottom_right')

    for point in room.rect.points_top:
      tilemap.cell(point).terrain = terrain_types.WALL
      tilemap.cell(point).annotations.add('horz')
    for point in room.rect.points_bottom:
      tilemap.cell(point).terrain = terrain_types.WALL
      tilemap.cell(point).annotations.add('horz')
    for point in room.rect.points_left:
      tilemap.cell(point).terrain = terrain_types.WALL
      tilemap.cell(point).annotations.add('vert')
    for point in room.rect.points_right:
      tilemap.cell(point).terrain = terrain_types.WALL
      tilemap.cell(point).annotations.add('vert')
    for point in room.rect.with_inset(1).points:
      tilemap.cell(point).terrain = terrain_types.FLOOR

    # tell cells what room they are in
    for point in room.rect.points:
      tilemap.assign_room(point, room.room_id)


def generate_random_path(tilemap, rect1, rect2):
  """
  Returns two lists based on an L-shaped path between a random point in *rect1*
  and a random point in *rect2*.

  The first list contains all points in the path that have WALL terrain. These
  are for doors.

  The second list contains all points in the path that have EMPTY terrain. These
  are for corridor tiles.
  """
  start = rect1.get_random_point()
  end = rect2.get_random_point()
  points_in_path = set()
  doors = set()
  corridors = set()
  for point in start.path_L_to(end):
    points_in_path.add(point)
    cell = tilemap.cell(point)
    if cell.terrain == terrain_types.WALL:
      doors.add(cell)
    elif (cell.terrain == terrain_types.EMPTY or not cell.terrain):
      corridors.add(cell)
  return (doors, corridors)


def engrave_corridor_between_rooms(tilemap, a, b, annotation=None):
  """
  Draw an L-shaped corridor between the two given rooms, making doors where it
  intersects with a wall.

  Optionally set an annotation on each cell. This is used to mark the
  transitions between difficulty quadrants, so that GameScene can transition
  the music and heal the player.
  """
  (doors, corridors) = generate_random_path(
    tilemap,
    a.rect.with_inset(1),
    b.rect.with_inset(1))
  iter_count = 0
  # If path contains more than 4 doors, try again, but don't try more than
  # 10 times.
  while len(doors) > 4 and iter_count < 10:
    iter_count += 1
    (doors, corridors) = generate_random_path(
      tilemap,
      a.rect.with_inset(1),
      b.rect.with_inset(1))
  for door in doors:
    door.terrain = terrain_types.DOOR_CLOSED
  for corridor in corridors:
    corridor.terrain = terrain_types.CORRIDOR
    if annotation:
      corridor.annotations.add(annotation)


def generate_and_engrave_corridors(tilemap, root):
  """
  Rooms have already been engraved, so add corridors. Rules for corridors:

  * There is one corridor between each pair of siblings in the BSP tree. If
    that statement doesn't make sense to you, then please go read more
    Wikipedia.
  * There is an exception to that rule: the sole ancestor for each quadrant
    (remember the blog post!) does not have a corridor to its sibling. Instead,
    explicitly draw corridors between specific rooms in each quadrant.
  """
  # generate corridors between rooms WITHIN a quadrant
  sibling_pairs = [(a, b) for (a, b) in root.sibling_pairs if a.level > 2 and b.level > 2]
  for (a, b) in sibling_pairs:
    engrave_corridor_between_rooms(
      tilemap, a.leftmost_leaf.data['room'], b.leftmost_leaf.data['room'])

  # generate corridors between quadrants (the glowing ones)
  room_aa_bottom = get_room_nearest(
    root.get_node_at_path('aa').leaves,
    Point(0, tilemap.size.height / 2))
  room_ab_top = get_room_nearest(
    root.get_node_at_path('ab').leaves,
    room_aa_bottom.rect.center)
  engrave_corridor_between_rooms(
    tilemap, room_aa_bottom, room_ab_top, 'transition-1-2')

  room_ab_right = get_room_nearest(
    root.get_node_at_path('ab').leaves,
    Point(tilemap.size.width / 2, tilemap.size.height))
  room_bb_left = get_room_nearest(
    root.get_node_at_path('bb').leaves,
    room_ab_right.rect.center)
  engrave_corridor_between_rooms(
    tilemap, room_ab_right, room_bb_left, 'transition-2-3')

  room_bb_top = get_room_nearest(
    root.get_node_at_path('bb').leaves,
    Point(tilemap.size.width, tilemap.size.height / 2))
  room_ba_bottom = get_room_nearest(
    root.get_node_at_path('ba').leaves,
    room_bb_top.rect.center)
  engrave_corridor_between_rooms(
    tilemap, room_bb_top, room_ba_bottom, 'transition-3-4')


def engrave_bsp_divisions(tilemap, node):
  """
  Debugging method. Sets the debug_character on the cells on the dividing lines
  between the 4 difficulty quadrants.
  """
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
  """
  Tell all the cells what their difficulty is. This is mostly so GameScene
  can fade up the appropriate music. :-)
  """
  for i, path in enumerate(['aa', 'ab', 'bb', 'ba']):
    for leaf in root.get_node_at_path(path).leaves:
      leaf.data['room'].difficulty = i


def get_can_add_monster_at_point(tilemap, point):
  """Returns True iff you can add a monster at the given point"""
  if point in tilemap.occupied_cells:
    return False
  if tilemap.cell(point).feature is not None:
    return False
  return True


# logic for items is the same
get_can_add_item_at_point = get_can_add_monster_at_point


MonsterData = namedtuple('MonsterData', ['monster_type', 'position', 'difficulty'])
def place_monsters(tilemap):
  """
  Tell the tilemap where the monsters go. This just populates the tilemap's
  ``points_of_interest`` property, which is how LevelState knows where to spawn
  monsters.
  """
  monster_datas = []
  # spawn monsters room by room
  for room in tilemap.rooms_by_id.values():
    rt = room.room_type

    # Filter monster types by what this room says it can have
    # (might be None for wildcard)
    possible_monsters = (
      list(monster_types.items) if rt.monsters is None
      else [monster_types[mt_k] for mt_k in room.room_type.monsters])
    # Further filter monster types by whether the monster says it can be in
    # a room of this difficulty (may be None for wildcard)
    allowed_monster_types = [
      mt for mt in possible_monsters
      if mt.difficulty is None or mt.difficulty == room.difficulty]

    # The room rect covers the walls, so inset by 1 before picking a point
    # from it
    inner_rect = room.rect.with_inset(1)
    # Compute how many monsters we can have (data file number is per 100 cells)
    num_monsters = max(
      1, round(inner_rect.area * room.room_type.monster_density / 100.0))

    # The rest of this should be pretty self-explanatory
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
  tilemap.points_of_interest['monsters'] = monster_datas 


ItemData = namedtuple('ItemData', ['item_type', 'position'])
def place_items(tilemap):
  """
  Tell the tilemap where the items go. This just populates the tilemap's
  ``points_of_interest`` property, which is how LevelState knows where to spawn
  items.

  The logic is the same as place_monsters(), but simpler.
  """
  item_datas = []
  tilemap.points_of_interest['items'] = item_datas 
  for room in tilemap.rooms_by_id.values():
    inner_rect = room.rect.with_inset(1)
    num_items = max(1, round(inner_rect.area * room.room_type.item_density / 100.0))

    # +1 = gold
    for i in range(num_items + 1):
      point = inner_rect.get_random_point()
      it = weighted_choice([
        (it, it.chance_by_difficulty[room.difficulty])
        for it in item_types.items])

      # spawn one gold per room
      if i == 0:
        it = item_types.GOLD

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
  """
  Helper function for our invocation of RandomBSPTree, the clubsandwich BSP
  tree dungeon generator.

  This is the "randrange" function that tells RandomBSPTree where to split
  each node. The specialness is that for the first 2 levels, it splits the
  node exactly evenly. This is how we guarantee four evenly-sized quadrants.
  """
  if level in (0, 1):
    # If first 2 levels, split at halfway point
    return floor((a + b) / 2)
  else:
    # Otherwise just be random
    return randrange(a, b)


def generate_dungeon(size):
  """
  Tie it all together. Returns a fully populated RogueBasementTilemap of the
  given size.
  """

  # Make a blank tilemap
  tilemap = RogueBasementTileMap(size)

  # Make a BSP tree where the minimum room size is 4 and the random-split
  # function is the helper defined just above this function
  generator = RandomBSPTree(tilemap.size, 4, randrange_func=_bsp_randrange)

  # key is difficulty (int).
  # values are the topmost ancestor for all nodes of that difficulty. A node
  # knows what difficulty it is based on which ancestor it has.
  difficulty_map = {
    # This 'aa', 'ab' notation is just a quicker, less error-prone way of
    # saying node.child_a.child_b and such.
    0: generator.root.get_node_at_path('aa'),
    1: generator.root.get_node_at_path('ab'),
    2: generator.root.get_node_at_path('bb'),
    3: generator.root.get_node_at_path('ba'),
  }

  # Create a room in each leaf
  rooms = [generate_room(leaf, difficulty_map) for leaf in generator.root.leaves]
  # Set the cell terrain values
  engrave_rooms(tilemap, rooms)  
  # Make corridors
  generate_and_engrave_corridors(tilemap, generator.root)

  # Place stairs up (no game value, just a marker)
  stairs_up_room = get_room_nearest(
    generator.root.get_node_at_path('aa').leaves,
    Point(tilemap.size.width / 2, tilemap.size.height / 4))
  stairs_up = stairs_up_room.rect.with_inset(1).get_random_point()
  tilemap.points_of_interest['stairs_up'] = stairs_up
  tilemap.occupied_cells.add(stairs_up)
  tilemap.cell(tilemap.points_of_interest['stairs_up']).feature = EnumFeature.STAIRS_UP

  # Place stairs down
  stairs_down_room = get_room_nearest(
    generator.root.get_node_at_path('ba').leaves, Point(tilemap.size.width / 2, tilemap.size.height / 2))
  stairs_down = stairs_down_room.rect.with_inset(1).get_random_point()
  tilemap.points_of_interest['stairs_down'] = stairs_down
  tilemap.occupied_cells.add(stairs_down)
  tilemap.cell(tilemap.points_of_interest['stairs_down']).feature = EnumFeature.STAIRS_DOWN

  # Tell all the cells how difficult they are (you know, for the music)
  engrave_difficulty(generator.root)

  # Figure out where the monsters and items go
  place_monsters(tilemap)
  place_items(tilemap)

  #engrave_bsp_divisions(tilemap, generator.root)
  return tilemap
