from clubsandwich.geom import Size

from .level_generator import generate_dungeon
from .level_state import LevelState


LEVEL_SIZE = Size(100, 60)


# Originally, Rogue Basement was going to have several levels. This was going
# to be the object that tracked the current level and let you switch between
# them.
#
# It fulfills that purpose, but there is no actual "change current level"
# method! It would be as simple as setting `self.active_id = NEW_VALUE`.
# The screen is redrawn completely every frame, so there is no need to do
# anything else.
#
# This object also tracks the score. LevelState keeps a weak reference to this
# object, so the active LevelState object is what actually increments the
# score.
class GameState:
  def __init__(self):
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

# Your next stop should be level_state.py.
