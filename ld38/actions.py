# This file contains helper functions for behaviors. They all take at least
# a LevelState and an entity.
#
# These used to all be methods on LevelState, but in general it's a bad idea
# to have a class that grows new methods that quickly. Better to have functions
# that operate on the class, which you can separate into different namespaces
# later.
from clubsandwich.tilemap import CellOutOfBoundsError

from .const import (
  EnumEventNames,
  terrain_types,
  monster_types,
)


def action_close(level_state, entity, position):
  """
  Have the entity close the door at the given cell
  """
  try:
    cell = level_state.tilemap.cell(position)
  except CellOutOfBoundsError:
    return False
  if cell.terrain != terrain_types.DOOR_OPEN:
    return False
  cell.terrain = terrain_types.DOOR_CLOSED
  if entity.is_player:
    # let monsters move
    level_state.fire_player_took_action_if_alive(position)
  # Player may now be able to see less, so update FoV
  level_state.update_los_cache()
  return True


def action_throw(level_state, entity, item, target_position, speed):
  """
  Have the entity throw an item at a specific position. "Speed" is number of
  moves per turn for the item in flight to take.

  When an item is thrown, an entity is created with monster type
  [ITEM_ID]_IN_FLIGHT. So for ROCK, you get a ROCK_IN_FLIGHT. As a long-term
  design this isn't great because you have to specify every throwable item in
  two places. But then again, the throwing mechanic in Rogue Basement where
  thrown items move one tile per turn is generally weird, so I'm not too
  worried about you trying to copy this...
  """
  path = list(entity.position.points_bresenham_to(target_position))
  # first point on the path is probably the entity's current position, so
  # skip it
  while level_state.get_entity_at(path[0]) == entity:
    path.pop(0)

  if not level_state.get_can_move(entity, path[0]):
    return False

  entity_in_the_way = level_state.get_entity_at(path[0])
  if entity_in_the_way:
    return False

  entity.inventory.remove(item)
  mk_id = item.item_type.id + '_IN_FLIGHT'
  rock_in_flight = level_state.create_entity(monster_types[mk_id], path[0], {
    # Hack: first point is "None" because rock is already in first position
    'path': [None] + path[1:],
    'speed': speed,
  })

  ### Thrown object takes strength from thrower ###
  rock_in_flight.stats['strength'] = entity.stats['strength']
  rock_in_flight.inventory.append(item)

  if entity.is_player:
    # If the player threw the item, give monsters a chance to move
    level_state.fire_player_took_action_if_alive(entity.position)
  return True

def action_move(level_state, entity, position):
  """
  For a given entity, "move" to the given position. What actually happens
  depends on what is at *position*. If it's empty, the entity moves. If it's a
  door, the door opens. If it's another entity, then attack.
  """
  cell = level_state.tilemap.cell(position)

  target_entity = level_state.get_entity_at(position)
  if target_entity:
    if entity.is_player:
      # player attacks monster
      action_attack(level_state, entity, target_entity)
      # let monsters move
      level_state.fire_player_took_action_if_alive(position)
      level_state.update_los_cache()
    else:
      # monster attacks player, or monster
      action_attack(level_state, entity, target_entity)
    return True

  if level_state.get_can_move(entity, position):
    del level_state.entity_by_position[entity.position]
    entity.position = position
    level_state.entity_by_position[position] = entity
    level_state.fire(EnumEventNames.entity_moved, data=entity, entity=entity)
    if entity.is_player:
      # let monsters move
      level_state.fire_player_took_action_if_alive(position)
      level_state.update_los_cache()
    return True
  elif cell.terrain == terrain_types.DOOR_CLOSED and level_state.get_can_open_door(entity):
    action_open_door(level_state, entity, position)
    if entity.is_player:
      # let monsters move
      level_state.fire_player_took_action_if_alive(position)
      level_state.update_los_cache()
    return True
  else:
    if entity.is_player:
      level_state.fire(EnumEventNames.entity_bumped, data=cell, entity=entity)


def action_attack(level_state, a, b):
  """Entity *a* attacks entity *b*"""
  level_state.fire(EnumEventNames.entity_attacking, data=b, entity=a)
  level_state.fire(EnumEventNames.entity_attacked, data=a, entity=b)
  b.state['hp'] -= a.stats['strength']
  level_state.fire(EnumEventNames.entity_took_damage, data=a, entity=b)
  if b.state['hp'] <= 0:
    level_state.fire(EnumEventNames.entity_died, data=None, entity=b)
    p = b.position
    level_state.remove_entity(b)

    # It might be a better design to have remove_entity() handle the inventory
    # drop, but for this tiny game it doesn't really matter.
    for i in b.inventory:
      level_state.drop_item(i, p)

    if b.is_player:
      level_state.dispatcher.stop_propagation()


def action_pickup_item(level_state, entity):
  items = level_state.get_items_at(entity.position)
  if not items:
    return False

  # handle scoring
  golds = [item for item in items if item.item_type.id == 'GOLD']
  if entity == level_state.player and golds:
    level_state.game_state.score += len(golds)
    level_state.fire(EnumEventNames.score_increased, data=None, entity=None)

  # pick things up
  items = [item for item in items if item.item_type.id != 'GOLD']
  entity.inventory.extend(items)

  if entity == level_state.player:
    # if player, pick up everything
    del level_state.items_by_position[entity.position]
  else:
    # if an enemy, put the golds back!
    level_state.items_by_position[entity.position] = golds

  # the items are now positionless. fire the pickup events.
  for item in items:
    item.position = None
    level_state.fire(EnumEventNames.entity_picked_up_item, data=item, entity=entity)

  if entity.is_player:
    # let monsters move
    level_state.fire_player_took_action_if_alive(entity.position)


def action_open_door(level_state, entity, position):
  """Open the door at the given position."""
  cell = level_state.tilemap.cell(position)
  cell.terrain = terrain_types.DOOR_OPEN
  level_state.fire(EnumEventNames.door_open, data=cell, entity=entity)
