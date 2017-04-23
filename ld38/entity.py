from .const import EnumMonsterMode

class Entity:
  def __init__(self, monster_type):
    self.monster_type = monster_type
    self.stats = {
      'hp_max': monster_type.hp_max,
      'strength': monster_type.strength,
    }
    self.state = {
      'hp': self.stats['hp_max']
    }
    self.position = None
    self.behaviors = []
    self.mode = EnumMonsterMode.DEFAULT

  @property
  def is_player(self):
    return self.monster_type.id == 'PLAYER'

  def add_behavior(self, behavior):
    self.behaviors.append(behavior)

  def __repr__(self):
    return self.__class__.__name__