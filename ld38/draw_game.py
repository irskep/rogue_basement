from math import floor

from .const import terrain_types, EnumFeature, EnumMonsterMode

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.draw import LINE_STYLES
from clubsandwich.geom import Rect, Point, Size
from clubsandwich.tilemap import CellOutOfBoundsError
from clubsandwich.line_of_sight import get_visible_points


C_DEFAULT = '#ffffff'
C_FLOOR = '#666666'
C_DEBUG = '#ff00ff'
C_STAIRS_UP = '#ff6600'
C_STAIRS_DOWN = '#ffff00'
C_TRANSITION_1_2 = '#00ff00'
C_TRANSITION_2_3 = '#00ff88'
C_TRANSITION_3_4 = '#00ffff'
C_MONSTER_STUNNED = '#0088ff'


def draw_game(game_state, bounds, ctx):
  level_state = game_state.active_level_state
  entity_cache = {}
  for entity in level_state.entities:
    if entity.position and bounds.contains(entity.position):
      entity_cache[entity.position] = entity

  with ctx.translate(bounds.origin * -1):
    _draw_game(game_state, bounds, ctx, entity_cache)


def _draw_game(game_state, bounds, ctx, entity_cache):
  level_state = game_state.active_level_state

  pointscache_color = None
  pointscache_values = None
  pointscache_origin = None
  def dump_points():
    nonlocal pointscache_color
    nonlocal pointscache_values
    nonlocal pointscache_origin
    if pointscache_values:
      ctx.color(pointscache_color)
      ctx.print(pointscache_origin, ''.join(pointscache_values))
    pointscache_color = None
    pointscache_values = None
    pointscache_origin = None

  color = '#abcdef'
  char = ' '
  for y in range(bounds.origin.y, bounds.origin.y + bounds.size.height):
    if y < 0:
      continue
    for x in range(bounds.origin.x, bounds.origin.x + bounds.size.width):
      point = Point(x, y)

      char = ' '
      if level_state.get_can_player_remember(point):
        cell = level_state.tilemap[point]
        (char, color) = get_char_and_color(level_state, entity_cache, cell)

      if pointscache_values and (pointscache_color == color or char == ' '):
          pointscache_values.append(char)
      else:
        dump_points()
        pointscache_values = [char]
        pointscache_color = color
        pointscache_origin = point

    dump_points()


def get_char_and_color(level_state, entity_cache, cell):
  line_chars = LINE_STYLES['single']

  char = ' '
  color = C_DEFAULT
  if cell.terrain == terrain_types.FLOOR:
    char = '.'
    color = level_state.tilemap.get_room(cell.point).room_type.color
  if cell.terrain == terrain_types.WALL:
    if 'horz' in cell.annotations:
      char = line_chars['T']
    if 'vert' in cell.annotations:
      char = line_chars['L']
    if 'corner_top_left' in cell.annotations:
      char = line_chars['TL']
    if 'corner_top_right' in cell.annotations:
      char = line_chars['TR']
    if 'corner_bottom_left' in cell.annotations:
      char = line_chars['BL']
    if 'corner_bottom_right' in cell.annotations:
      char = line_chars['BR']
    color = level_state.tilemap.get_room(cell.point).room_type.color
  if cell.terrain == terrain_types.DOOR_CLOSED:
    char = '+'
  if cell.terrain == terrain_types.DOOR_OPEN:
    char = "'"
  if cell.terrain == terrain_types.CORRIDOR:
    color = C_FLOOR
    char = "#"

    if 'transition-1-2' in cell.annotations:
      color = C_TRANSITION_1_2
    if 'transition-2-3' in cell.annotations:
      color = C_TRANSITION_2_3
    if 'transition-3-4' in cell.annotations:
      color = C_TRANSITION_3_4

  if cell.debug_character:
    color = C_DEBUG
    char = cell.debug_character

  if cell.feature:
    if cell.feature == EnumFeature.STAIRS_UP:
      color = C_STAIRS_UP
      char = '<'
    if cell.feature == EnumFeature.STAIRS_DOWN:
      color = C_STAIRS_DOWN
      char = '>'

  items = level_state.items_by_position.get(cell.point, None)
  if items:
    color = items[-1].item_type.color
    char = items[-1].item_type.char

  if level_state.get_can_player_see(cell.point):
    if cell.point in entity_cache:
      entity = entity_cache[cell.point]
      color = entity.monster_type.color
      char = entity.monster_type.char
      if entity.mode == EnumMonsterMode.STUNNED:
        color = C_MONSTER_STUNNED
  else:
    color = '#444444'
  
  return (char, color)