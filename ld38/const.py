from enum import Enum

class EnumTerrain(Enum):
  EMPTY = 0
  FLOOR = 1
  WALL = 2
  DOOR_CLOSED = 3
  DOOR_OPEN = 4
  CORRIDOR = 5


class EnumEntityKind(Enum):
  PLAYER = 0
  VERP = 1


class EnumFeature(Enum):
  NONE = 0
  STAIRS_UP = 1
  STAIRS_DOWN = 2
