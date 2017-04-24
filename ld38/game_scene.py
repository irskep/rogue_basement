#!/usr/bin/env python
import os
import sys
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
  EnumMonsterMode,
  ENTITY_NAME_BY_KIND,
  KEYS_U, KEYS_D, KEYS_L, KEYS_R, KEYS_UL, KEYS_UR, KEYS_DL, KEYS_DR,
  KEYS_WAIT,
  KEYS_CLOSE,
  KEYS_CANCEL,
  KEYS_GET,
  KEYS_THROW,
)

DEBUG_PROFILE = False


root = Path(os.path.abspath(sys.argv[0])).parent
pyglet.resource.path = [str(root / 'assets')]
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
  (KEYS_GET, EnumEventNames.key_get)
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

Get rock: g
Throw rock: t
Close: c

""".strip()


TEXT_GAME_OVER = """
      __.      
    _/ / \\
   /   \\  *      ______________________________________
──/─────\\──     / Ah, well... another body to feed the \\
  \\ - - /    ──/  mutated skunks...                    |
&  \\ - /  &    \\_______________________________________/ 
 \\───+───/
     |
\\────|────/
_\\       /_
"""[1:].rstrip()


TEXT_YOU_WIN = """
      __.      
    _/ / \\
   /   \\  *      _______________________________________
──/─────\\──     / Oh, thank you so much! You might want \\
  \\ - - /    ──/  to talk to my neighbor, he's also in  |
&  \\ - /  &    |  the Netherwizard Club...             / 
 \\───+───/     \\______________________________________/ 
     |
\\────|────/
_\\       /_
"""[1:].rstrip()


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
    self.last_known_player_position = Point(0, 0)

  def draw(self, ctx):
    current_player_position = self.gamestate.active_level_state.player.position  
    if current_player_position is not None:
      self.last_known_player_position = current_player_position
    half_size = (self.bounds.size / 2).floored
    draw_game(
      self.gamestate,
      bounds=Rect(
        self.last_known_player_position - half_size,
        self.bounds.size),
      ctx=ctx)


class StatsView(View):
  def __init__(self, gamestate, *args, **kwargs):
    self.gamestate = gamestate
    self.progress_bar = ProgressBarView(
      fraction=1,
      layout_options=LayoutOptions.row_top(1).with_updates(top=3, right=1))
    self.health_label = LabelView(
      text="Health: ?",
      color_fg="#ffffff",
      color_bg='#000000',
      layout_options=LayoutOptions.row_top(1).with_updates(top=2, right=1))
    self.inventory_count = LabelView(
      text="Rocks: 0",
      color_fg="#ffffff",
      color_bg="#000000",
      layout_options=LayoutOptions.row_top(1).with_updates(top=4, right=1))
    self.score_label = LabelView(
      text="Score: 0",
      color_fg="#ffff00",
      color_bg="#000000",
      layout_options=LayoutOptions.row_top(1).with_updates(top=6, right=1))
    super().__init__(subviews=[
      LabelView(
        text="Stats",
        color_fg='#ffffff',
        color_bg='#660000',
        clear=True,
        layout_options=LayoutOptions.row_top(1).with_updates(right=1)),
      self.health_label,
      self.progress_bar,
      self.inventory_count,
      self.score_label,
    ], *args, **kwargs)
    self.update()

  def update(self):
    self.progress_bar.fraction = (
      self.gamestate.active_level_state.player.state['hp'] /
      self.gamestate.active_level_state.player.stats['hp_max'])
    self.inventory_count.text = "Rocks: {}".format(
      len(self.gamestate.active_level_state.player.inventory))
    self.health_label.text = "Health: {}".format(
      self.gamestate.active_level_state.player.state['hp'])
    self.score_label.text = "Score: {}".format(
      self.gamestate.active_level_state.score)

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
  def __init__(self, score, *args, **kwargs):
    view = WindowView(
      'Game Over',
      layout_options=LayoutOptions.centered(80, 30),
      subviews=[
          LabelView(TEXT_GAME_OVER, layout_options=LayoutOptions.centered('intrinsic', 'intrinsic')),
          LabelView("Your score: {}".format(score),
            layout_options=LayoutOptions.row_bottom(1).with_updates(bottom=6)),
          ButtonView(
              text='Aaauuuuggghhhhhh...', callback=self.done,
              layout_options=LayoutOptions.row_bottom(3)),
      ])
    super().__init__(view, *args, **kwargs)
    self.covers_screen = False

  def done(self):
    self.director.pop_to_first_scene()


class WinScene(UIScene):
  def __init__(self, score, *args, **kwargs):
    view = WindowView(
      'You win!',
      layout_options=LayoutOptions.centered(80, 30),
      subviews=[
          LabelView(TEXT_YOU_WIN, layout_options=LayoutOptions.centered('intrinsic', 'intrinsic')),
          LabelView("Your score: {}".format(score),
            layout_options=LayoutOptions.row_bottom(1).with_updates(bottom=6)),
          ButtonView(
              text='Thanks!', callback=self.done,
              layout_options=LayoutOptions.row_bottom(3)),
      ])
    super().__init__(view, *args, **kwargs)
    self.covers_screen = False

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
      layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH).with_updates(top=None, height='intrinsic'))
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
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_picked_up_item, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_died, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_attacking, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.score_increased, None)

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
    elif mode == EnumMode.CLOSE:
      self.log_view.text = "Close what? (Pick a direction)"
    elif mode == EnumMode.THROW:
      self.log_view.text = "Throw where? (Pick a direction)"

  def log(self, text):
    self.log_view.text = text
    print(text)

  def on_entity_moved(self, entity, data):
    level_state = self.gamestate.active_level_state
    cell = level_state.tilemap.cell(entity.position)
    self.log_view.text = ""
    if cell.feature == EnumFeature.STAIRS_DOWN:
      self.director.push_scene(WinScene(level_state.score))

    if cell.annotations & {'transition-1-2', 'transition-2-3', 'transition-3-4'}:
      self.player_volume_directions = ['down', 'down', 'down', 'down']

      ### HACK HACK HACK HACK ###
      # for "balance", replenish health between rooms
      level_state.player.state['hp'] = level_state.player.stats['hp_max']
    
    room = level_state.tilemap.get_room(entity.position)
    if room and room.difficulty is not None:
      self.player_volume_directions = ['down', 'down', 'down', 'down']
      self.player_volume_directions[room.difficulty] = 'up'

  def on_entity_bumped(self, entity, data):
    self.log("Oof!")

  def on_entity_took_damage(self, entity, data):
    self.stats_view.update()

  def on_score_increased(self, entity, data):
    self.stats_view.update()
    self.log("You pick up some loose change.")

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

    if data.mode == EnumMonsterMode.STUNNED:
      self.log("{} hits {}. It is stunned.".format(name1, name2))
    else:
      self.log("{} hits {}.".format(name1, name2))

  def on_entity_died(self, entity, data):
    try:
      name = ENTITY_NAME_BY_KIND[entity.monster_type.id].subject
    except KeyError:
      print("Missing log message for", entity.monster_type.id)
    if entity == self.gamestate.active_level_state.player:
      if DEBUG_PROFILE: pr.dump_stats('profile')
      self.director.push_scene(LoseScene(self.gamestate.active_level_state.score))

  def on_entity_picked_up_item(self, entity, data):
    if entity.is_player:
      self.log("You picked up a {}".format(data.item_type.id))
    else:
      name = ENTITY_NAME_BY_KIND[entity.monster_type.id].subject
      self.log("{} picks up a {}".format(name, data.item_type.id))
    self.stats_view.update()

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
      if val in KEYS_THROW:
        if level_state.player.inventory:
          self.mode = EnumMode.THROW
        else:
          self.log("You don't have anything to throw.")
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
    elif self.mode == EnumMode.THROW:
      if val in KEYS_CANCEL:
        self.mode = EnumMode.DEFAULT
      for keys, delta in KEYS_AND_DIRECTIONS:
        if val in keys:
          item = level_state.player.inventory[0]
          did_throw = level_state.action_throw(
            level_state.player, item, level_state.player.position + delta * 1000, 2)
          if did_throw:
            self.log("You throw the {}".format(item.item_type.id))
          else:
            self.log("You can't throw that in that direction.")
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
