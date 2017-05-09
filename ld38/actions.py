from clubsandwich.tilemap import CellOutOfBoundsError

from .const import (
  EnumEventNames,
  terrain_types,
  monster_types,
)

def action_close(level_state, entity, position):
  try:
    cell = level_state.tilemap.cell(position)
  except CellOutOfBoundsError:
    return False
  if cell.terrain != terrain_types.DOOR_OPEN:
    return False
  cell.terrain = terrain_types.DOOR_CLOSED
  level_state.fire_player_took_action_if_alive(position)
  level_state.update_los_cache()
  return True

# TODO: log this event!
def action_throw(level_state, entity, item, target_position, speed):
  path = list(entity.position.points_bresenham_to(target_position))
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
    'path': [None] + path[1:],  # behavior executes immediately but rock is already placed
    'speed': speed,
  })
  ### HACK HACK HACK HACK: thrown object takes strength from thrower ###
  rock_in_flight.stats['strength'] = entity.stats['strength']
  rock_in_flight.inventory.append(item)
  
  if entity.is_player:
    level_state.fire_player_took_action_if_alive(entity.position)
  return True

def action_move(level_state, entity, position):
  cell = level_state.tilemap.cell(position)

  target_entity = level_state.get_entity_at(position)
  if target_entity:
    if entity.is_player:
      action_attack(level_state, entity, target_entity)
      level_state.fire_player_took_action_if_alive(position)
      level_state.update_los_cache()
      return True
    else:
      if target_entity == level_state.player:
        action_attack(level_state, entity, target_entity)
        return True
      else:
        return False  # it's another monster

  if level_state.get_can_move(entity, position):
    del level_state.entity_by_position[entity.position]
    entity.position = position
    level_state.entity_by_position[position] = entity
    level_state.fire(EnumEventNames.entity_moved, data=entity, entity=entity)
    if entity.is_player:
      level_state.fire_player_took_action_if_alive(position)
      level_state.update_los_cache()
    return True
  elif cell.terrain == terrain_types.DOOR_CLOSED and level_state.get_can_open_door(entity):
    action_open_door(level_state, entity, position)
    if entity.is_player:
      level_state.fire_player_took_action_if_alive(position)
      level_state.update_los_cache()
    return True
  else:
    if entity.is_player:
      level_state.fire(EnumEventNames.entity_bumped, data=cell, entity=entity)

def action_attack(level_state, a, b):
  level_state.fire(EnumEventNames.entity_attacking, data=b, entity=a)
  level_state.fire(EnumEventNames.entity_attacked, data=a, entity=b)
  b.state['hp'] -= a.stats['strength']
  level_state.fire(EnumEventNames.entity_took_damage, data=a, entity=b)
  if b.state['hp'] <= 0:
    level_state.fire(EnumEventNames.entity_died, data=None, entity=b)
    p = b.position
    level_state.remove_entity(b)
    # TODO: do this in remove_entity() maybe?
    for i in b.inventory:
      level_state.drop_item(i, p)
    if b.is_player:
      level_state.dispatcher.stop_propagation()

def action_pickup_item(level_state, entity):
  try:
    items = level_state.items_by_position[entity.position]
  except KeyError:
    return False

  golds = [item for item in items if item.item_type.id == 'GOLD']

  if entity == level_state.player and golds:
    level_state.game_state.score += len(golds)
    level_state.fire(EnumEventNames.score_increased, data=None, entity=None)

  items = [item for item in items if item.item_type.id != 'GOLD']
  entity.inventory.extend(items)

  if entity == level_state.player:
    del level_state.items_by_position[entity.position]
  else:
    level_state.items_by_position[entity.position] = golds

  for item in items:
    item.position = None
    level_state.fire(EnumEventNames.entity_picked_up_item, data=item, entity=entity)
  if entity.is_player:
    level_state.fire_player_took_action_if_alive(entity.position)

def action_open_door(level_state, entity, position):
  # this is where the logic goes for doors that are hard to open.
  cell = level_state.tilemap.cell(position)
  cell.terrain = terrain_types.DOOR_OPEN
  level_state.fire(EnumEventNames.door_open, data=cell, entity=entity)
