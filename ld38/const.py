import csv
import re
from math import floor
from collections import namedtuple
from pathlib import Path
from enum import Enum, unique

from clubsandwich.blt.nice_terminal import terminal


def csv_iterator(filename):
  with (Path(__name__).parent.parent / 'data' / filename).open() as f:
    reader = csv.reader(f)
    skip_next_line = True
    for line in reader:
      if skip_next_line:
        skip_next_line = False
        continue
      yield line


def _int(val):
  return floor(float(val))

def _color(val):
  if val.startswith('#'):
    return val  # already ok
  if val.endswith('.00'):
    val = val[:-3]
  while len(val) < 6:
    val = '0' + val
  return '#' + val


ITEM_RE = re.compile(r'(.*)x(\d+)')
def _items(val):
  if not val:
    return []
  items = []
  for s in val.split('|'):
    m = ITEM_RE.match(s)
    for _ in range(int(m.group(2))):
      items.append(m.group(1).upper())
  return items



class EnumUppercaseWithLookup(Enum):
  @classmethod
  def lookup(cls, k):
    return getattr(cls, k.upper())


@unique
class EnumMode(EnumUppercaseWithLookup):
  DEFAULT = 0
  CLOSE = 1
  THROW = 2


@unique
class EnumTerrain(EnumUppercaseWithLookup):
  EMPTY = 0
  FLOOR = 1
  WALL = 2
  DOOR_CLOSED = 3
  DOOR_OPEN = 4
  CORRIDOR = 5


@unique
class EnumFeature(EnumUppercaseWithLookup):
  NONE = 0
  STAIRS_UP = 1
  STAIRS_DOWN = 2


@unique
class EnumMonsterMode(EnumUppercaseWithLookup):
  DEFAULT = 0
  CHASING = 1
  FLEEING = 2
  SLEEPING = 3


@unique
class EnumRoomShape(EnumUppercaseWithLookup):
  BOX_RANDOM = 0
  BOX_FULL = 1


@unique
class EnumEventNames(EnumUppercaseWithLookup):
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


KEYS_U = (terminal.TK_UP, terminal.TK_K, terminal.TK_KP_8)
KEYS_D = (terminal.TK_DOWN, terminal.TK_J, terminal.TK_KP_2)
KEYS_L = (terminal.TK_LEFT, terminal.TK_H, terminal.TK_KP_4)
KEYS_R = (terminal.TK_RIGHT, terminal.TK_L, terminal.TK_KP_6)
KEYS_UL = (terminal.TK_Y, terminal.TK_KP_7)
KEYS_UR = (terminal.TK_U, terminal.TK_KP_9)
KEYS_DL = (terminal.TK_B, terminal.TK_KP_1)
KEYS_DR = (terminal.TK_N, terminal.TK_KP_3)
KEYS_WAIT = (terminal.TK_PERIOD, terminal.TK_KP_5)
KEYS_CLOSE = (terminal.TK_C,)
KEYS_CANCEL = (terminal.TK_ESCAPE,)
KEYS_GET = (terminal.TK_G,)
KEYS_THROW = (terminal.TK_T,)

ENTITY_NAME_BY_KIND = {}

EntityName = namedtuple(
  'EntityName', ['subject', 'object', 'death_verb_active'])
for line in csv_iterator('names.csv'):
  ENTITY_NAME_BY_KIND[line[0].upper()] = EntityName(*line[1:])


RoomType = namedtuple(
  'RoomType', ['shape', 'difficulty', 'monsters', 'chance', 'color', 'monster_density', 'item_density'])
ROOM_TYPES = []

for line in csv_iterator('rooms.csv'):
  ROOM_TYPES.append(RoomType(
    shape=EnumRoomShape.lookup(line[0]),
    difficulty=None if line[1] == '*' else _int(line[1]),
    monsters=None if line[2] == '*' else set(s.upper() for s in line[2].split('|')),
    chance=float(line[3]),
    color=_color(line[4]),
    monster_density=float(line[5]),
    item_density=float(line[6]),
  ))
  

MonsterType = namedtuple('MonsterType', [
  'id', 'char', 'color', 'difficulty', 'chance', 'behaviors', 'hp_max', 'strength', 'items'])
MONSTER_TYPES_BY_ID = {}
for line in csv_iterator('monsters.csv'):
  MONSTER_TYPES_BY_ID[line[0].upper()] = MonsterType(
    id=line[0].upper(),
    char=line[1],
    color=_color(line[2]),
    difficulty=_int(line[3]),
    chance=float(line[4]),
    behaviors=line[5].split('|'),
    hp_max=_int(line[6]),
    strength=_int(line[7]),
    items=_items(line[8])
  )

ItemType = namedtuple('ItemType', [
  'id', 'char', 'color', 'effect', 'uses_min', 'uses_max', 'chance_by_difficulty'])
ITEM_TYPES_BY_ID = {}
for line in csv_iterator('items.csv'):
  ITEM_TYPES_BY_ID[line[0].upper()] = ItemType(
    id=line[0].upper(),
    char=line[1],
    color=_color(line[2]),
    uses_min=_int(line[3]),
    uses_max=_int(line[4]),
    effect=line[5],
    chance_by_difficulty=[float(val) for val in line[6:10]]
  )
