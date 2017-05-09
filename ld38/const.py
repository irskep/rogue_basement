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


### enums ###


# Some values are stored in Enum objects. If I were to develop this game
# further I would probably replace all enums with CSVs, but for now here they
# are.


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

# This section deals with loading data from CSV files. For each individual
# file/type, all rows in the file are converted to namedtuple classes wit the
# given name and schema, and stored by ID in a DataStore object.

# Terrain is an easy example. terrain.csv looks like this:

# id,walkable,lightable
# EMPTY,false,false
# FLOOR,true,true
# WALL,false,false
# DOOR_CLOSED,false,false
# DOOR_OPEN,true,true
# CORRIDOR,true,true
#
# The first line is ignored because it's just the label.
# The remaining lines are converted like this:
#
# row = TerrainType(str(line[0]), _bool(line[1]), _bool(line[2]))
#
# All items are then accessible by ID in a very simple way:
#
# >>> terrain_types.FLOOR
# TerrainType(id='FLOOR', walkable=True, lightable=True)
terrain_types = DataStore('TerrainType', (
  ('id', str),
  ('walkable', _bool),
  ('lightable', _bool),
))

# The entity_names data store knows what the human-readable name of a monster
# is, and whether you refer to it in the second or third person when generating
# text.
entity_names = DataStore('EntityName', (
  ('id', _upper),
  ('name', str),
  ('is_second_person', _bool),
))

# The verbs data store has the second and third person versions of all the
# verbs used in the game.
verbs = DataStore('Verb', (
  ('id', str),
  ('present_2p', str),
  ('present_3p', str),
))

# The room_types data store determines what kinds of rooms there are, what
# shape they have, what they look like, and what's inside them. This is mostly
# used by level_generator.py.
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

# The monster_types data store has all information about monsters at the time
# they are added to the world.
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

# The item_types data store has information about items. There are only 2
# entries, so here they are:
#
# id,character,color,chance_0,chance_1,chance_2,chance_3
# ROCK,*,#6a867d,1,1,1,1
# GOLD,$,#aaaa00,0,0,0,0
#
# This data store is a little bit interesting because it has a custom reader
# object. Originally I had thought I would have different item drop rates per
# area, so I allocated 4 columns to store all that information. As you can see
# it's all the same anyway, so it ended up being a waste of time. And even if
# I did end up using different values, this is not a good way to represent it.
#
# So don't follow my bad example here!
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

# Another data store with a special reader. In this file, the first column is
# the key ID, and all the remaining columns are BearLibTerminal event
# identifiers that map to that "key." So for the Rogue Basement key "UP", we
# want it to fire whenever we get TK_UP, TK_K, or TK_KP_8.
key_bindings = DataStore('KeyBinding', (
  ('id', str),
  ('keys', _key_list)
))
class KeyBindingsReader(CSVReader):
  """Combines cols 1-end as list"""
  def read(self):
    for line in super().read():
      yield [line[0], line[1:]]


# Load all the values from the files, dumping any previously stored data. This
# is how you'd go about implementing a settings screen where you can change the
# key bindings, or live-edit your monster data to tune the game.
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


# A simple reverse mapping of the key_bindings data store. It's a map of
# terminal.TK_BLAH: "Key ID".
#
# >>> BINDINGS_BY_KEY[terminal.TK_KP_8]
# "UP"
BINDINGS_BY_KEY = {}
for binding in key_bindings.items:
  for key in binding.keys:
    BINDINGS_BY_KEY[key] = binding.id


# For the directional keys, it's really nice to be able to just map a key
# to a vector and add it to the player's position to get the next move.
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