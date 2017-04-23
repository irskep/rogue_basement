from math import floor

from .const import EnumTerrain, EnumFeature, EnumEntityKind, EnumMonsterMode

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.draw import LINE_STYLES
from clubsandwich.geom import Rect, Point


C_DEFAULT = '#ffffff'
C_FLOOR = '#666666'
C_DEBUG = '#ff00ff'
C_STAIRS_UP = '#ff6600'
C_STAIRS_DOWN = '#ffff00'
C_TRANSITION_1_2 = '#00ff00'
C_TRANSITION_2_3 = '#00ff88'
C_TRANSITION_3_4 = '#00ffff'

C_PLAYER = '#ffffff'
C_VERP = {
  10: '#ffff00',
  20: '#ff8800',
  30: '#ff0000',
  40: '#aa0066',
}


def draw_game(gamestate, bounds, ctx):
  with ctx.translate(bounds.origin * -1):
    #with ctx.crop_before_send(Rect(Point(0, 0), size)):
    _draw_game(gamestate, bounds, ctx)

def _draw_game(gamestate, bounds, ctx):
  line_chars = LINE_STYLES['single']

  level_state = gamestate.active_level_state

  entity_cache = {}

  for entity in level_state.entities:
    if entity.position:
      entity_cache[entity.position] = entity

  for point in bounds.points:
    try:
      cell = level_state.tilemap.cell(point)
    except IndexError:
      continue
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

    if cell.point in entity_cache:
      entity = entity_cache[cell.point]
      if entity.kind == EnumEntityKind.PLAYER:
        color = C_PLAYER
        char = '@'
      if entity.kind == EnumEntityKind.VERP:
        color = C_VERP[entity.stats['hp_max']]
        char = 'v'

    with ctx.temporary_fg(color):
      ctx.put(cell.point, char)