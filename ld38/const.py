from enum import Enum, unique

@unique
class EnumTerrain(Enum):
  EMPTY = 0
  FLOOR = 1
  WALL = 2
  DOOR_CLOSED = 3
  DOOR_OPEN = 4
  CORRIDOR = 5


@unique
class EnumEntityKind(Enum):
  PLAYER = 0
  VERP = 1


@unique
class EnumFeature(Enum):
  NONE = 0
  STAIRS_UP = 1
  STAIRS_DOWN = 2


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
  door_open = "door_open"
  player_took_action = "player_took_action"
