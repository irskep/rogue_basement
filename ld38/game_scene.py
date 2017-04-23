#!/usr/bin/env python
import os
os.environ["PYGLET_SHADOW_WINDOW"] = "false"
from enum import Enum
from math import floor
from pathlib import Path

import pyglet

from clubsandwich.draw import draw_line_vert
from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.geom import Size, Point, Rect
from clubsandwich.ui import (
  LabelView,
  ButtonView,
  LayoutOptions,
  UIScene,
  View,
  WindowView,
)

from .draw_game import draw_game
from .gamestate import GameState
from .const import (
  EnumEventNames,
  EnumMode,
  EnumFeature,
  ENTITY_NAME_BY_KIND,
  KEYS_U, KEYS_D, KEYS_L, KEYS_R, KEYS_UL, KEYS_UR, KEYS_DL, KEYS_DR,
  KEYS_WAIT,
  KEYS_CLOSE,
  KEYS_CANCEL
)

DEBUG_PROFILE = False


pyglet.resource.path = [str(Path(__name__).parent.parent / 'assets')]
tracks = [
  pyglet.resource.media('Q1.mp3'),
  pyglet.resource.media('Q2.mp3'),
  pyglet.resource.media('Q3.mp3'),
  pyglet.resource.media('Q4.mp3'),
]


KEYS_AND_EVENTS = [
  (KEYS_U, EnumEventNames.key_u),
  (KEYS_D, EnumEventNames.key_d),
  (KEYS_L, EnumEventNames.key_l),
  (KEYS_R, EnumEventNames.key_r),
  (KEYS_UL, EnumEventNames.key_ul),
  (KEYS_UR, EnumEventNames.key_ur),
  (KEYS_DL, EnumEventNames.key_dl),
  (KEYS_DR, EnumEventNames.key_dr),
  (KEYS_WAIT, EnumEventNames.player_took_action),
]
KEYS_AND_DIRECTIONS = [
  (KEYS_U, Point(0, -1)),
  (KEYS_D, Point(0, 1)),
  (KEYS_L, Point(-1, 0)),
  (KEYS_R, Point(1, 0)),
  (KEYS_UL, Point(-1, -1)),
  (KEYS_UR, Point(1, -1)),
  (KEYS_DL, Point(-1, 1)),
  (KEYS_DR, Point(1, 1)),
]

SIDEBAR_WIDTH = 21

TEXT_HELP = """
======= Keys =======
Move: arrows, numpad
      hjklyubn

Close: c
""".strip()


if DEBUG_PROFILE:
  import cProfile
  pr = cProfile.Profile()


class ProgressBarView(View):
  def __init__(self, fraction, color_fg='#0088ff', color_bg='#000000', *args, **kwargs):
    self.fraction = fraction
    self.color_fg = color_fg
    self.color_bg = color_bg
    super().__init__(*args, **kwargs)

  def draw(self, ctx):
    with ctx.temporary_bg(self.color_bg):
      ctx.clear_area(self.bounds)
    frac_width = floor(self.bounds.width * self.fraction)
    with ctx.temporary_bg(self.color_fg):
      ctx.clear_area(self.bounds.with_size(Size(frac_width, self.bounds.height)))


class GameView(View):
  def __init__(self, gamestate, *args, **kwargs):
    self.gamestate = gamestate
    super().__init__(*args, **kwargs)

  def draw(self, ctx):
    half_size = (self.bounds.size / 2).floored
    draw_game(
      self.gamestate,
      bounds=Rect(
        self.gamestate.active_level_state.player.position - half_size,
        self.bounds.size),
      ctx=ctx)


class StatsView(View):
  def __init__(self, gamestate, *args, **kwargs):
    self.gamestate = gamestate
    self.progress_bar = ProgressBarView(
      fraction=1,
      layout_options=LayoutOptions.row_top(1).with_updates(top=3, right=1))
    super().__init__(*args, **kwargs)
    self.add_subview(LabelView(
      text="Stats",
      color_fg='#ffffff',
      color_bg='#660000',
      clear=True,
      layout_options=LayoutOptions.row_top(1).with_updates(right=1)))
    self.add_subview(LabelView(
      text="Health",
      color_fg='#ffffff',
      color_bg='#000000',
      layout_options=LayoutOptions.row_top(1).with_updates(right=1, top=2)))
    self.add_subview(self.progress_bar)

  def update(self):
    self.progress_bar.fraction = (
      self.gamestate.active_level_state.player.state['hp'] /
      self.gamestate.active_level_state.player.stats['hp_max'])

  def draw(self, ctx):
    with ctx.temporary_fg('#ffffff'):
      draw_line_vert(Point(self.bounds.x2, self.bounds.y), self.bounds.height)


class PauseScene(UIScene):
  def __init__(self, *args, **kwargs):
    view = WindowView(
      'Pause',
      layout_options=LayoutOptions.centered(40, 10),
      subviews=[
          ButtonView(
              text='Resume', callback=self.resume,
              layout_options=LayoutOptions.row_top(5)),
          ButtonView(
              text='Quit', callback=self.quit,
              layout_options=LayoutOptions.row_bottom(5)),
      ])
    super().__init__(view, *args, **kwargs)
    self.covers_screen = False

  def resume(self):
    self.director.pop_scene()

  def quit(self):
    self.director.pop_to_first_scene()


class LoseScene(UIScene):
  def __init__(self, *args, **kwargs):
    view = WindowView(
      'Game Over',
      layout_options=LayoutOptions.centered(80, 30),
      subviews=[
          LabelView('You have died.', layout_options=LayoutOptions(height=1, top=1, bottom=None)),
          ButtonView(
              text='Darn.', callback=self.done,
              layout_options=LayoutOptions.row_bottom(3)),
      ])
    super().__init__(view, *args, **kwargs)

  def done(self):
    self.director.pop_to_first_scene()


class WinScene(UIScene):
  def __init__(self, *args, **kwargs):
    view = WindowView(
      'You win!',
      layout_options=LayoutOptions.centered(80, 30),
      subviews=[
          LabelView(
            'You close the portal. Good job.',
            layout_options=LayoutOptions(height=1, top=1, bottom=None)),
          ButtonView(
              text='Thanks!', callback=self.done,
              layout_options=LayoutOptions.row_bottom(3)),
      ])
    super().__init__(view, *args, **kwargs)

  def done(self):
    self.director.pop_to_first_scene()


class GameScene(UIScene):
  def __init__(self, *args, **kwargs):
    self.player_volume_directions = ['up', 'down', 'down', 'down']

    self.players = [pyglet.media.Player() for _ in range(4)]
    for i, player in enumerate(self.players):
      player.queue(tracks[i])
      player.eos_action = player.EOS_LOOP
      if i == 0:
        player.play()
      else:
        player.volume = 0

    self._mode = EnumMode.DEFAULT
    self.gamestate = GameState()
    self.log_view = LabelView(
      text="", align_horz='left', color_bg='#333333', clear=True,
      layout_options=LayoutOptions.row_bottom(1).with_updates(left=SIDEBAR_WIDTH))
    self.stats_view = StatsView(self.gamestate, layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH))
    help_view = LabelView(
      text=TEXT_HELP, align_horz='left',
      layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH).with_updates(top=None, height=5))
    views = [
      GameView(self.gamestate, layout_options=LayoutOptions().with_updates(left=SIDEBAR_WIDTH, bottom=1)),
      self.stats_view,
      help_view,
      self.log_view,
    ]
    super().__init__(views, *args, **kwargs)

    level_state = self.gamestate.active_level_state
    level_state.dispatcher.add_subscriber(self, EnumEventNames.door_open, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_bumped, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_moved, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_took_damage, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_died, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_attacking, None)

  def exit(self, *args, **kwargs):
    super().exit(*args, **kwargs)
    for player in self.players:
      player.delete()

  @property
  def mode(self):
    return self._mode

  @mode.setter
  def mode(self, mode):
    self._mode = mode
    if mode == EnumMode.DEFAULT:
      pass
    else:
      self.log_view.text = "Close what? (Pick a direction)"

  def log(self, text):
    self.log_view.text = text
    print(text)

  def on_entity_moved(self, entity, data):
    level_state = self.gamestate.active_level_state
    cell = level_state.tilemap.cell(entity.position)
    self.log_view.text = ""
    if cell.feature == EnumFeature.STAIRS_DOWN:
      self.director.push_scene(WinScene())

    if cell.annotations & {'transition-1-2', 'transition-2-3', 'transition-3-4'}:
      self.player_volume_directions = ['down', 'down', 'down', 'down']
    
    room = level_state.tilemap.get_room(entity.position)
    if room and room.difficulty is not None:
      self.player_volume_directions = ['down', 'down', 'down', 'down']
      self.player_volume_directions[room.difficulty] = 'up'

  def on_entity_bumped(self, entity, data):
    self.log("Oof!")

  def on_entity_took_damage(self, entity, data):
    self.stats_view.update()

  def on_door_open(self, entity, data):
    self.log("You open the door.")

  def on_entity_attacking(self, entity, data):
    try:
      name1 = ENTITY_NAME_BY_KIND[entity.monster_type.id].subject
    except KeyError:
      print("Missing log message for", entity.monster_type.id)
      return

    try:
      name2 = ENTITY_NAME_BY_KIND[data.monster_type.id].object
    except KeyError:
      print("Missing log message for", data.monster_type.id)
      return

    self.log("{} hits {}.".format(name1, name2))

  def on_entity_died(self, entity, data):
    try:
      name = ENTITY_NAME_BY_KIND[entity.monster_type.id].subject
    except KeyError:
      print("Missing log message for", entity.monster_type.id)
    if entity == self.gamestate.active_level_state.player:
      if DEBUG_PROFILE: pr.dump_stats('profile')
      self.director.push_scene(LoseScene())

  def terminal_read(self, val):
    if DEBUG_PROFILE: pr.enable()
    level_state = self.gamestate.active_level_state
    if self.mode == EnumMode.DEFAULT:
      if val == terminal.TK_Q:
        level_state.action_die()
      for keys, event_name in KEYS_AND_EVENTS:
        if val in keys:
          level_state.fire(event_name)
      if val in KEYS_CLOSE:
        self.mode = EnumMode.CLOSE
      if val in KEYS_CANCEL:
        self.director.push_scene(PauseScene())
    elif self.mode == EnumMode.CLOSE:
      if val in KEYS_CANCEL:
        self.mode = EnumMode.DEFAULT
      for keys, delta in KEYS_AND_DIRECTIONS:
        if val in keys:
          if level_state.action_close(level_state.player, level_state.player.position + delta):
            self.log("You close the door.")
          else:
            self.log("There is no door there.")
          self.mode = EnumMode.DEFAULT
          if DEBUG_PROFILE: pr.disable()
          return
      if DEBUG_PROFILE: pr.disable()
      self.log("Invalid direction")

  def terminal_update(self, is_active=True):
    if DEBUG_PROFILE: pr.enable()
    for (i, direction, player) in zip(range(4), self.player_volume_directions, self.players):
      if direction == 'down' and player.volume > 0:
        player.volume = max(0, player.volume - 0.05)
        if player.volume == 0:
          player.pause()
          player.seek(0)
      elif direction == 'up' and player.volume < 1:
        was_zero = player.volume == 0
        player.volume = min(1, player.volume + 0.05)
        if was_zero:
          player.volume = 1
          player.play()

    super().terminal_update(is_active)
    self.gamestate.active_level_state.consume_events()
    if DEBUG_PROFILE: pr.disable()
