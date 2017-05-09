import os
import re
import sys
from math import floor
from pathlib import Path
from enum import Enum, unique

from bearlibterminal import terminal
from clubsandwich.datastore import DataStore, CSVReader
from clubsandwich.geom import Point


GAME_ROOT = Path(os.path.abspath(sys.argv[0])).parent


### field types ###

# Rogue Basement uses clubsandwich's DataStore class to read and store
# information from CSV files. Each row is converted to a namedtuple using a
# mapping of (field name, conversion_function), where conversion_function
# takes a string and returns some value.
#
# These are all the field value conversion functions used by Rogue Basement.

def _bool(val):
  """
  Return ``True`` iff *val* is "1", "yes", or "true", otherwise ``False``.

  >>> _bool('TRUE')
  True
  >>> _bool('nah')
  False
  """
  return val.lower() in ('1', 'yes', 'true')

def _int(val):
  """
  Parse string as an int, even if it has decimals.

  >>> _int('1.0')
  1
  >>> _int('1.5')
  1
  """
  return floor(float(val))

def _enum_value(TheEnum):
  """
  Returns a *function* that converts strings into values of the given Enum
  subclass.

  >>> _enum_value(EnumFeature)("STAIRS_DOWN")
  EnumFeature.STAIRS_DOWN
  """
  def _specific_enum_value(val):
    try:
      return TheEnum[val]
    except KeyError:
      raise ValueError("Invalid value for enum {!r}: {!r}".format(TheEnum, val))
  return _specific_enum_value

def _int_or_wildcard(val):
  """
  Returns ``None`` if *val* is ``'*'``, otherwise parse as an int.

  >>> _int_or_wildcard("5")
  5
  >>> _int_or_wildcard("*")
  None
  """
  return None if val == '*' else _int(val)

def _pipe_separated_uppercase(val):
  """
  Returns ``None`` if *val* is ``'*'``. Otherwise, split *val* on the ``'|'``
  character and return a list of the items, transformed to all caps.

  >>> _pipe_separated_uppercase("a|b|c")
  ['A', 'B', 'C']
  >>> _pipe_separated_uppercase("*")
  None
  """
  return None if val == '*' else set(s.upper() for s in val.split('|'))

def _pipe_separated(val):
  """
  Returns *val* split on the ``'|'`` character.

  >>> _pipe_separated("a|b|c")
  ['a', 'b', 'c]
  """
  return [s.strip() for s in val.split('|') if s.strip()]

def _upper(val):
  """
  Returns *val*, uppercased.

  >>> _upper('a')
  'A'
  """
  return val.upper()

def _color(val):
  """
  Parse string as hex color string. The scim CSV does some dumb things like
  truncate, convert to float, and remove #, so fix all that crap.

  >>> _color('#ff0000')
  '#ff0000'
  >>> _color('ff0000')
  '#ff0000'
  >>> _color('668800.00')
  '#668800'
  >>> _color('345')
  '#000345'
  """
  if val.startswith('#'):
    return val  # already ok
  if val.endswith('.00'):
    val = val[:-3]
  while len(val) < 6:
    val = '0' + val
  return '#' + val

def _float_list(str_list):
  """
  Converts all items in the given list to floats.

  Most other conversion functions take strings. But the readers for items.csv
  and key_bindings.csv aggregate several columns into a single value before
  passing them to the DataStore.

  This is probably confusing. I'm sorry.
  """
  return [float(s) for s in str_list]

def _key_list(str_list):
  """
  key_bindings.csv's values are BearLibTerminal constant names, minus the 3-
  character ``TK_`` prefix. This function takes a list of those values and adds
  back the prefix, and looks it up in the ``terminal`` namespace to get the
  actual value of the constant.

  >>> _key_list('UP|DOWN')
  [terminal.TK_UP, terminal.TK_DOWN]
  """
  return [getattr(terminal, 'TK_' + s.strip()) for s in str_list]

ITEM_RE = re.compile(r'(.*)x(\d+)')
def _items(val):
  """
  Parser for the monsters.csv column specifying what items a monster is
  carrying. There may be multiple values split on the ``'|'`` character,
  and each value looks like ``ITEM_IDx2``, where the number to the right of the
  ``x`` specifies how many of the given item there are.

  >>> _items("ROCKx4")
  ['ROCK', 'ROCK', 'ROCK', 'ROCK']
  """
  if not val:
    return []
  items = []
  for s in val.split('|'):
    m = ITEM_RE.match(s)
    for _ in range(int(m.group(2))):
      items.append(m.group(1).upper())
  return items


### enums, probably to promote to CSV ###


@unique
class EnumFeature(Enum):
  NONE = 0
  STAIRS_UP = 1
  STAIRS_DOWN = 2


@unique
class EnumMonsterMode(Enum):
  DEFAULT = 0
  CHASING = 1
  FLEEING = 2
  SLEEPING = 3
  STUNNED = 4


@unique
class EnumRoomShape(Enum):
  BOX_RANDOM = 0
  BOX_FULL = 1


@unique
class EnumEventNames(Enum):
  key_u = "key_u"
  key_d = "key_d"
  key_l = "key_l"
  key_r = "key_r"
  key_ul = "key_ul"
  key_ur = "key_ur"
  key_dl = "key_dl"
  key_dr = "key_dr"
  key_get = "key_get"

  entity_moved = "entity_moved"
  entity_bumped = "entity_bumped"
  entity_died = "entity_died"
  entity_attacking = "entity_attacking"
  entity_attacked = "entity_attacked"
  entity_took_damage = "entity_took_damage"
  entity_picked_up_item = "entity_picked_up_item"
  entity_dropped_item = "entity_dropped_item"
  door_open = "door_open"
  player_took_action = "player_took_action"
  score_increased = "score_increased"


### CSVs ###

terrain_types = DataStore('TerrainType', (
  ('id', str),
  ('walkable', _bool),
  ('lightable', _bool),
))

entity_names = DataStore('EntityName', (
  ('id', _upper),
  ('name', str),
  ('is_second_person', _bool),
))

verbs = DataStore('Verb', (
  ('id', str),
  ('present_2p', str),
  ('present_3p', str),
))

room_types = DataStore('RoomType', (
  ('id', str),
  ('shape', _enum_value(EnumRoomShape)),
  ('difficulty', _int_or_wildcard),
  ('monsters', _pipe_separated_uppercase),
  ('chance', float),
  ('color', _color),
  ('monster_density', float),
  ('item_density', float),
))

monster_types = DataStore('MonsterType', (
  ('id', _upper),
  ('char', str),
  ('color', _color),
  ('difficulty', _int),
  ('chance', float),
  ('behaviors', _pipe_separated),
  ('hp_max', _int),
  ('strength', _int),
  ('items', _items),
))

item_types = DataStore('ItemType', (
  ('id', str),
  ('char', str),
  ('color', _color),
  ('chance_by_difficulty', _float_list),
))
class ItemTypeReader(CSVReader):
  """Combines cols 6-10 into a list"""
  def read(self):
    for line in super().read():
      yield line[:3] + [line[3:]]

key_bindings = DataStore('KeyBinding', (
  ('id', str),
  ('keys', _key_list)
))
class KeyBindingsReader(CSVReader):
  """Combines cols 1-end as list"""
  def read(self):
    for line in super().read():
      yield [line[0], line[1:]]


def reload():
  terrain_types.unload()
  entity_names.unload()
  verbs.unload()
  room_types.unload()
  monster_types.unload()
  item_types.unload()
  key_bindings.unload()

  terrain_types.add_source(CSVReader(str(GAME_ROOT / 'data' / 'terrain.csv')))
  entity_names.add_source(CSVReader(str(GAME_ROOT / 'data' / 'names.csv')))
  verbs.add_source(CSVReader(str(GAME_ROOT / 'data' / 'verbs.csv')))
  room_types.add_source(CSVReader(str(GAME_ROOT / 'data' / 'rooms.csv')))
  monster_types.add_source(CSVReader(str(GAME_ROOT / 'data' / 'monsters.csv')))
  item_types.add_source(ItemTypeReader(str(GAME_ROOT / 'data' / 'items.csv')))
  key_bindings.add_source(KeyBindingsReader(
    str(GAME_ROOT / 'data' / 'key_bindings.csv'), skip_first_line=False))
reload()


### assorted code constants ###


BINDINGS_BY_KEY = {}
for binding in key_bindings.items:
  for key in binding.keys:
    BINDINGS_BY_KEY[key] = binding.id


KEYS_TO_DIRECTIONS = {
  'U': Point(0, -1),
  'D': Point(0, 1),
  'L': Point(-1, 0),
  'R': Point(1, 0),
  'UL': Point(-1, -1),
  'UR': Point(1, -1),
  'DL': Point(-1, 1),
  'DR': Point(1, 1),
}