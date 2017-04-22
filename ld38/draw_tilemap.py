from .const import EnumTerrain

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.draw import LINE_STYLES

def draw_tilemap(tilemap, ctx=terminal):
  line_chars = LINE_STYLES['single']
  for cell in tilemap.cells:
    char = ' '
    color = '#ffffff'
    if cell.terrain == EnumTerrain.FLOOR:
      char = '.'
      color = '#666666'
    if cell.terrain == EnumTerrain.WALL:
      char = '#'
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
      char = "#"
    if cell.debug_character:
      char = cell.debug_character
    ctx.color(color)
    ctx.put(cell.point, char)