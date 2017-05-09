from .const import EnumMonsterMode

# Every moving game object is an Entity. There is no subclassing. The
# differences are all in the properties.
class Entity:
  def __init__(self, monster_type):
    # This is how we know what kind of thing it is
    self.monster_type = monster_type

    # Stats for entities do not change during the game, unless some permanent
    # buff or debuff is applied. Rogue Basement has neither of those.
    self.stats = {
      'hp_max': monster_type.hp_max,
      'strength': monster_type.strength,
    }

    # "State" can and should change during gameplay. Hit points is the most
    # obvious application.
    self.state = {
      'hp': self.stats['hp_max']
    }
    self.position = None

    # Entities have positions if they are alive in the level.
    self.behaviors = []

    # Entities can carry items. Their inventory is an unlimited flat list of
    # Item objects. This is probably not a great inventory system, but it
    # basically works.
    self.inventory = []

    # Some monster types might use this to store the state of some state
    # machine. For example, it might decide not to move if it is stunned.
    #
    # From a software design perspective, keeping this in an enum is very
    # limiting. If monsters had both a "sleep" and "stunned" state, it would
    # become tedious to check for both states in the AI before trying to move.
    # A better solution would be to have a CSV file where the ID is the state
    # name, and there are columns for things like "can I walk?", "can I see?"
    # etc. Then the AI can just check simple flags before taking the
    # corresponding action.
    self.mode = EnumMonsterMode.DEFAULT

    # Entities are modified by Behaviors (see behaviors.py). This is a bucket
    # for them to store things in.
    self.behavior_state = {}

  @property
  def is_player(self):
    # It is basically up to the level generator to make sure there is only one
    # player. :-)
    return self.monster_type.id == 'PLAYER'

  def add_behavior(self, behavior):
    # Simply keep references to all behaviors. The LevelState object will take
    # care of the rest.
    self.behaviors.append(behavior)

  def __repr__(self):
    return "{}(monster_type={})".format(self.__class__.__name__, self.monster_type.id)


# Item objects are extremely simple. They just know what kind of thing they
# are, and where they are in the map. Rogue Basement just has rocks, so that
# is enough.
class Item:
  def __init__(self, item_type):
    self.item_type = item_type
    self.position = None  # None if in someone's inventory
