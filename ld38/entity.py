from random import randint

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
    self.inventory = []
    self.mode = EnumMonsterMode.DEFAULT

    self.behavior_state = {}

  @property
  def is_player(self):
    return self.monster_type.id == 'PLAYER'

  def add_behavior(self, behavior):
    self.behaviors.append(behavior)

  def __repr__(self):
    return "{}(monster_type={})".format(self.__class__.__name__, self.monster_type.id)


class Item:
  def __init__(self, item_type):
    self.item_type = item_type
    self.position = None  # None if in someone's inventory
    self.uses_remaining = randint(item_type.uses_min, item_type.uses_max)
