# Because Python is a reference counted language, it's important not to create
# reference cycles! Weakref is used to hold a reference to the parent
# GameState object.
import weakref
# Everything that happens is associated with an event. The event processing
# system keeps events to be processed in a queue.
from collections import deque
# Levels assign their own arbitrary unique IDs.
from uuid import uuid4

# You should really go read the docs on this:
# http://steveasleep.com/clubsandwich/api_event_dispatcher.html
from clubsandwich.event_dispatcher import EventDispatcher
# "Better to ask forgiveness than beg for permission" - LevelState's approach
# to querying cell data
from clubsandwich.tilemap import CellOutOfBoundsError
# Implementation of recursive shadowcasting for FoV
from clubsandwich.line_of_sight import get_visible_points

# The rest of the imports will be explained later.
from .entity import Entity, Item
from .behavior import (
  CompositeBehavior,
  BEHAVIORS_BY_ID,
)
from .const import (
  EnumEventNames,
  monster_types,
  item_types,
)


# LevelState stores all information related to a single map and its
# inhabitants. It also handles the event loop.
class LevelState:
  def __init__(self, tilemap, game_state):
    # Things that don't change
    self._game_state = weakref.ref(game_state)
    self.tilemap = tilemap
    self.uuid = uuid4().hex

    # Things that do change
    self.event_queue = deque()
    self.entity_by_position = {}
    self.items_by_position = {}
    self._is_applying_events = False

    # This is the object that remembers who wants to know about what, and what
    # methods to call when things do happen.
    self.dispatcher = EventDispatcher()
    # We have to tell the dispatcher what all the possible events are before we
    # fire them. This makes typos easy to catch.
    for name in EnumEventNames:
      self.dispatcher.register_event_type(name)

    # Player is special, create them explicitly
    self.player = None
    self.player = self.create_entity(
      monster_types.PLAYER,
      self.tilemap.points_of_interest['stairs_up'])

    # The level generator has helpfully told us where all the items should go.
    # Just follow its directions.
    for item_data in self.tilemap.points_of_interest['items']:
      self.drop_item(Item(item_data.item_type), item_data.position)

    # The level generator also told us about all the monsters. How nice!
    for monster_data in self.tilemap.points_of_interest['monsters']:
      self.create_entity(monster_data.monster_type, monster_data.position)

    # There are two sets of points: points the player can see right now
    # (self.los_cache), and points the player has seen in the past
    # (self.level_memory_cache). self.update_los_cache() keeps both up to date.
    self.level_memory_cache = set()
    self.update_los_cache()

  # Expose the GameState weakref as a property for convenience
  @property
  def game_state(self):
    return self._game_state()

  # FoV/line of sight can be a big deal in roguelikes, but it's really easy to
  # compute using clubsandwich, so I won't spend much time explaining this.
  # Just know that get_visible_points() returns a set of points that can be
  # seen from the given vantage point.
  def update_los_cache(self):
    self.los_cache = get_visible_points(self.player.position, self.get_can_see)
    self.level_memory_cache.update(self.los_cache)

  # Create an entity, instantiate its behaviors, put it on the map
  def create_entity(self, monster_type, position, behavior_state=None):
    mt = monster_type
    if mt.id == 'PLAYER':
      # Only create one player at a time!
      assert self.player is None

    # No overlapping entities, please
    assert position not in self.entity_by_position

    # Instantiate the entity
    entity = Entity(monster_type=mt)
    entity.position = position
    entity.behavior_state = behavior_state or {}

    # Populate its inventory    
    for it_id in entity.monster_type.items:
      entity.inventory.append(Item(item_types[it_id]))

    # Instantiate the entity's behaviors. (See behavior.py.) If there's only
    # one we can create it immediately; if there's more than one, we have to
    # wrap them in a CompositeBehavior.
    if len(mt.behaviors) == 1:
      entity.add_behavior(BEHAVIORS_BY_ID[mt.behaviors[0]](entity, self))
    else:
      entity.add_behavior(CompositeBehavior(entity, self, [
        BEHAVIORS_BY_ID[behavior_id](entity, self)
        for behavior_id in mt.behaviors]))

    # Remember the entity, process its events, draw it, let us look it up by
    # position later
    self.add_entity(entity)
    return entity

  def add_entity(self, entity):
    # Behaviors are just buckets of event handlers attached to entities. They
    # know how to subscribe themselves to dispatchers.
    for behavior in entity.behaviors:
      behavior.add_to_event_dispatcher(self.dispatcher)
    # Remember this entity's position
    if entity.position:
      self.entity_by_position[entity.position] = entity

  def remove_entity(self, entity):
    # Unsubscribe behaviors from dispatcher
    for behavior in entity.behaviors:
      behavior.remove_from_event_dispatcher(self.dispatcher)
    # Remove from the position index
    if entity.position:
      del self.entity_by_position[entity.position]
      entity.position = None

  # Item storage in the map is extremely simple. There's just a flat list of
  # items per cell.
  def drop_item(self, item, point, entity=None):
    self.items_by_position.setdefault(point, [])
    self.items_by_position[point].append(item)
    if entity is not None:
      self.fire(EnumEventNames.entity_dropped_item, data=item, entity=entity)
    return True

  ### event stuff ###

  # "Firing" an event just means remembering it for later. We don't want to get
  # into a situation where we are handling event X, and some handler emits
  # event Y before all the X handlers have finished, and then Y gets handled
  # before the rest of the X handlers.
  #
  # This might not matter much in practice, but it makes things easier to
  # reason about.
  def fire(self, name, data=None, entity=None):
    self.event_queue.append((name, entity, data))

  # GameScene calls this each frame. It iterates over all the events in the
  # queue and dispatches each one.
  def consume_events(self):
    # This is an overly paranoid check to make sure this doesn't get called
    # inside itself.
    assert not self._is_applying_events
    self._is_applying_events = True

    while self.event_queue:
      (name, entity, data) = self.event_queue.popleft()
      # Remember, the dispatcher is what actually remembers what objects want
      # to get called for what events. Some events are associated with an
      # entity. For those events, objects may subscribe only for that entity.
      #
      # If any of the handlers fire new events, they just get added to
      # self.event_queue.
      self.dispatcher.fire(name, entity, data)

    self._is_applying_events = False

  ### action helper methods ###

  # Super basic wrapper around firing the player_took_action event. Every enemy
  # monster moves in response to this event, but if the player is dead, they
  # are not on the map, and all kinds of stuff breaks. Easier to just not fire
  # it if the player is dead.
  def fire_player_took_action_if_alive(self, position=None):
    if self.player.position is None:
      return
    position = position or self.player.position
    self.fire(EnumEventNames.player_took_action, data=position, entity=None)

  # The functions in actions.py call these methods to do what they do.
  # They are general utility methods for querying and mutating the level.
  # These methods are also used by draw_game.py for a few things.

  def get_can_player_see(self, point):
    # Sight test is super easy!
    return point in self.los_cache

  def get_can_player_remember(self, point):
    # So is memory test!
    return point in self.level_memory_cache

  # This could potentially just be a call to get_can_player_see(), since right
  # now nobody's trying to look at anything but the player with the same max
  # distance, but it is instructive to leave it here as it is.
  def test_line_of_sight(self, source, dest):  # both args are entities
    # always fail LOS when far away
    if source.position is None or dest.position is None:
      return False  # someone is dead, so they can't see each other
    if source.position.manhattan_distance_to(dest.position) > 30:
      # Arbitrary distance limit on sight
      return False

    # Just make sure all the points on a bresenham line between the two
    # entities are unblocked
    for point in source.position.points_bresenham_to(dest.position):
      if not self.get_can_see(point):
        return False
    return True

  def get_entity_at(self, position):
    try:
      return self.entity_by_position[position]
    except KeyError:
      return None

  def get_items_at(self, position):
    try:
      return self.items_by_position[position]
    except KeyError:
      return []

  def get_is_terrain_passable(self, point):
    try:
      return self.tilemap.cell(point).terrain.walkable
    except CellOutOfBoundsError:
      return False

  def get_can_move(self, entity, position, allow_player=False):
    try:
      # Don't allow moving if there's someone there already, unless the entity
      # is allowed to try to move into the player's space (i.e. attack them).
      #
      # This method is currently only used by monsters to make AI decisions.
      # Players just do what they want, and the move action just fails if they
      # try to do something impossible.
      if self.entity_by_position[position] == self.player and not allow_player:
        return False
      elif self.entity_by_position[position] != self.player:
        return False
    except KeyError:
      pass

    try:
      cell = self.tilemap.cell(position)
    except CellOutOfBoundsError:
      return False
    return cell.terrain.walkable

  def get_can_see(self, position):
    try:
      cell = self.tilemap.cell(position)
      return cell.terrain.lightable
    except CellOutOfBoundsError:
      return False

  def get_can_open_door(self, entity):
    # muahahaha only players can open doors. In practice this doesn't matter
    # because enemies don't try to follow the player through doors, as their
    # AI relies on line of sight.
    return entity.is_player

  def get_passable_neighbors(self, entity, allow_player=True):
    return [
      p for p in
      list(entity.position.neighbors) + list(entity.position.diagonal_neighbors)
      if self.get_can_move(entity, p, allow_player=True)]
