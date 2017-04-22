from .const import EnumTerrain, EnumFeature, EnumEntityKind

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.draw import LINE_STYLES


C_DEFAULT = '#ffffff'
C_FLOOR = '#666666'
C_DEBUG = '#ff00ff'
C_STAIRS_UP = '#ff6600'
C_STAIRS_DOWN = '#ffff00'
C_TRANSITION_1_2 = '#00ff00'
C_TRANSITION_2_3 = '#00ff88'
C_TRANSITION_3_4 = '#00ffff'

C_PLAYER = '#ffffff'
C_VERP = '#ff0000'


def draw_game(gamestate, ctx=terminal):
  line_chars = LINE_STYLES['single']

  entity_cache = {}

  for entity in gamestate.active_level_state.entities:
    if entity.position:
      entity_cache[entity.position] = entity

  for cell in gamestate.active_level_state.level.tilemap.cells:
    char = ' '
    color = C_DEFAULT
    if cell.terrain == EnumTerrain.FLOOR:
      char = '.'
      color = C_FLOOR
    if cell.terrain == EnumTerrain.WALL:
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
    if cell.terrain == EnumTerrain.DOOR_CLOSED:
      char = '+'
    if cell.terrain == EnumTerrain.DOOR_OPEN:
      char = "'"
    if cell.terrain == EnumTerrain.CORRIDOR:
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

    try:
      entity = entity_cache[cell.point]
      if entity.kind == EnumEntityKind.PLAYER:
        color = C_PLAYER
        char = '@'
      if entity.kind == EnumEntityKind.VERP:
        color = C_VERP
        char = 'v'
    except KeyError:
      pass

    ctx.color(color)
    ctx.put(cell.point, char)