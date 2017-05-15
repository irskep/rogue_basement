"""
Exports one function, draw_game(), which turns a GameState into a grid of
cells.
"""
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
C_MONSTER_STUNNED = '#0088ff


def draw_game(game_state, bounds, ctx):
  with ctx.translate(bounds.origin * -1):
    _draw_game(game_state, bounds, ctx)


def _draw_game(game_state, bounds, ctx):
  level_state = game_state.level

  # This is a super effective optimiziation that is a little tricky to
  # understand.
  #
  # Python calls to C shared libraries are SLOW. In a naive implementation,
  # we'd make two calls per cell: terminal_color() and terminal_put(). Early
  # version of Rogue Basement did this, and it resulted in 100% CPU and <30
  # FPS.
  #
  # To speed things up, we can make use of three facts:
  #
  # * BearLibTerminal has a terminal_print() function which accepts multiple
  #   characters.
  # * If two X-adjacent cells have the same color, they can be drawn in a
  #   single terminal_print() call.
  # * If a cell is EMPTY, then it doesn't matter what color it is!
  #
  # The following block of code deals with storing and printing characters
  # in groups. The rules are:
  #
  # * If pointscache_color is None, start a new group.
  # * If the current cell is empty, continue the current group.
  # * If the current cell is non-empty and the color is the same as the group
  #   color, continue the current group.
  # * If the current cell is non-empty and the color is NOT the same as the
  #   group color, print the current group and start a new group
  # * If the end of a line is reached, print the current group and set
  #   pointscache_color to None.
  #
  # By doing this, the number of calls to BearLibTerminal.dylib (or .dll, etc)
  # is about 8% of what it would otherwise be!

  # color of the current group; None if no group is active
  pointscache_color = None
  # values in the current group
  pointscache_values = None
  # point where the current group starts, continuing to the right
  pointscache_origin = None
  def dump_points():
    """Write current group to BearLibTerminal"""
    nonlocal pointscache_color
    nonlocal pointscache_values
    nonlocal pointscache_origin
    if pointscache_values:
      ctx.color(pointscache_color)
      ctx.print(pointscache_origin, ''.join(pointscache_values))
    pointscache_color = None
    pointscache_values = None
    pointscache_origin = None

  color = '#abcdef' # if you see this in the UI, you messed up
  char = ' '
  for y in range(bounds.origin.y, bounds.origin.y + bounds.size.height):
    # bounds are not guaranteed to be within map coordinates, may be negative.
    # if we ask for negative-valued cells in the map, we will get values
    # starting from the bottom/right, due to Python array indexing!
    if y < 0:
      continue
    for x in range(bounds.origin.x, bounds.origin.x + bounds.size.width):
      point = Point(x, y)

      # by default, cell is empty
      char = ' '

      # if player can see or has ever seen this point, show it
      if level_state.get_can_player_remember(point):
        cell = level_state.tilemap[point]
        (char, color) = get_char_and_color(level_state, cell)

      if pointscache_values and (pointscache_color == color or char == ' '):
        # Happy path: continue current group
        pointscache_values.append(char)
      else:
        # Sad path: print group, start a new one
        dump_points()
        pointscache_values = [char]
        pointscache_color = color
        pointscache_origin = point

    # Print last group in line
    dump_points()


def get_char_and_color(level_state, cell):
  """
  Returns drawing data for the given point.

  For a larger game, it might make sense to store drawing data in a data file.
  For a tiny game like Rogue Basement, a giant if-statement works just fine!
  """
  line_chars = LINE_STYLES['single']

  char = ' '
  color = C_DEFAULT

  ### terrain ###

  if cell.terrain == terrain_types.FLOOR:
    char = '.'
    color = level_state.tilemap.get_room(cell.point).room_type.color
  # For walls, the level generator left us some hints about how to draw. This
  # is one of the primary purposes of the cell.annotations property.
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

  ### debug (mostly for level generator) ###

  if cell.debug_character:
    color = C_DEBUG
    char = cell.debug_character

  ### feature (stairs) ###

  if cell.feature:
    if cell.feature == EnumFeature.STAIRS_UP:
      color = C_STAIRS_UP
      char = '<'
    if cell.feature == EnumFeature.STAIRS_DOWN:
      color = C_STAIRS_DOWN
      char = '>'

  ### items ###

  items = level_state.items_by_position.get(cell.point, None)
  if items:
    color = items[-1].item_type.color
    char = items[-1].item_type.char

  ### entities ###

  if level_state.get_can_player_see(cell.point):
    if cell.point in level_state.entity_by_position:
      entity = level_state.entity_by_position[cell.point]
      color = entity.monster_type.color
      char = entity.monster_type.char
      if entity.mode == EnumMonsterMode.STUNNED:
        color = C_MONSTER_STUNNED
  else:
    color = '#444444'
  
  return (char, color)