from clubsandwich.geom import Size

from .level_generator import generate_dungeon
from .level_state import LevelState


LEVEL_SIZE = Size(100, 60)


class GameState:
  def __init__(self):
    self.turn_number = 0
    self.level_states_by_id = {}
    self.score = 0
    self.active_id = self.add_level().uuid

  @property
  def level(self):
    return self.level_states_by_id[self.active_id]

  def add_level(self):
    level_state = LevelState(generate_dungeon(LEVEL_SIZE), self)
    self.level_states_by_id[level_state.uuid] = level_state
    return level_state
