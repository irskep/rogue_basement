"""
Classes representing the map and its contents.

The docs for the superclasses are important:

http://steveasleep.com/clubsandwich/api_tilemap.html
"""
from collections import defaultdict

from clubsandwich.tilemap import TileMap, Cell

from .const import (
  terrain_types,
)


class RogueBasementCell(Cell):
  """
  One cell in the RogueBasementTilemap. It changes the default terrain to
  terrain_types.EMPTY instead of the int ``0``, and adds a *room_id* property
  to tie it to the Room object created by the level generator.
  """
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.room_id = None
    self.terrain = terrain_types.EMPTY


class RogueBasementTileMap(TileMap):
  """
  Extensions to the base TileMap class:

  * Stores dicts mapping room_id -> Room, and room_id -> [RogueBasementCell].
  * Stores a set of cells that have been "used" by the level generator
  """
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

  def get_room(self, point):
    room_id = self.cell(point).room_id
    if room_id is None:
      return None
    return self.rooms_by_id[room_id]