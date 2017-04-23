from enum import Enum


class EventDispatcher:
  def __init__(self):
    self.handlers = {}

  def register_event_type(self, name):
    if isinstance(name, Enum):
      name = name.value
    self.handlers[name] = []

  def add_subscriber(self, obj, name, entity):
    if isinstance(name, Enum):
      name = name.value
    self.handlers[name].append((obj, entity))

  def remove_subscriber(self, obj, name, entity):
    if isinstance(name, Enum):
      name = name.value
    self.handlers[name].remove((obj, entity))

  def fire(self, name, data, entity):
    if isinstance(name, Enum):
      name = name.value
    method_name = "on_" + name.lower()
    for (obj, inner_entity) in self.handlers[name]:
      if entity is None or inner_entity is None or entity is inner_entity:
        method = getattr(obj, method_name)
        method(entity, data)
