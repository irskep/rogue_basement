import csv
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


class EnumUppercaseWithLookup(Enum):
  @classmethod
  def lookup(cls, k):
    return getattr(cls, k.upper())


@unique
class EnumMode(EnumUppercaseWithLookup):
  DEFAULT = 0
  CLOSE = 1


@unique
class EnumTerrain(EnumUppercaseWithLookup):
  EMPTY = 0
  FLOOR = 1
  WALL = 2
  DOOR_CLOSED = 3
  DOOR_OPEN = 4
  CORRIDOR = 5


@unique
class EnumEntityKind(EnumUppercaseWithLookup):
  PLAYER = 0
  VERP = 1


@unique
class EnumFeature(EnumUppercaseWithLookup):
  NONE = 0
  STAIRS_UP = 1
  STAIRS_DOWN = 2


@unique
class EnumMonsterMode(EnumUppercaseWithLookup):
  DEFAULT = 0
  CHASING_PLAYER = 1


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

  move_u = "move_u"
  move_d = "move_d"
  move_l = "move_l"
  move_r = "move_r"
  move_ul = "move_ul"
  move_ur = "move_ur"
  move_dl = "move_dl"
  move_dr = "move_dr"

  entity_moved = "entity_moved"
  entity_bumped = "entity_bumped"
  entity_died = "entity_died"
  entity_attacking = "entity_attacking"
  entity_attacked = "entity_attacked"
  entity_took_damage = "entity_took_damage"
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

ENTITY_NAME_BY_KIND = {}

EntityName = namedtuple('EntityName', ['subject', 'object', 'death_verb_active'])
for line in csv_iterator('names.csv'):
  ENTITY_NAME_BY_KIND[EnumEntityKind.lookup(line[0])] = EntityName(*line[1:])


RoomType = namedtuple('RoomType', ['shape', 'difficulty', 'monsters', 'chance', 'color'])
ROOM_TYPES = []

for line in csv_iterator('rooms.csv'):
  ROOM_TYPES.append(RoomType(
    shape=EnumRoomShape.lookup(line[0]),
    difficulty=None if line[1] == '*' else int(line[1]),
    monsters=set(s.upper() for s in line[2].split(',')),
    chance=float(line[3]),
    color=line[4]
  ))
  