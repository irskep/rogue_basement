#!/usr/bin/env python
from enum import Enum

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
  KEYS_U,
  KEYS_D,
  KEYS_L,
  KEYS_R,
  KEYS_UL,
  KEYS_UR,
  KEYS_DL,
  KEYS_DR,
  KEYS_WAIT,
  KEYS_CLOSE,
  KEYS_CANCEL
)

DEBUG_PROFILE = False


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
    super().__init__(*args, **kwargs)
    self.add_subview(LabelView(
      text="Stats",
      color_fg='#ffffff',
      color_bg='#660000',
      clear=True,
      layout_options=LayoutOptions.row_top(1).with_updates(right=1)))


  def draw(self, ctx):
    with ctx.temporary_fg('#ffffff'):
      draw_line_vert(Point(self.bounds.x2, self.bounds.y), self.bounds.height)


class GameOverScene(UIScene):
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


class GameScene(UIScene):
  def __init__(self, *args, **kwargs):
    self._mode = EnumMode.DEFAULT
    self.gamestate = GameState()
    self.log_view = LabelView(
      text="", align_horz='left', color_bg='#333333', clear=True,
      layout_options=LayoutOptions.row_bottom(1).with_updates(left=SIDEBAR_WIDTH))
    help_view = LabelView(
      text=TEXT_HELP, align_horz='left',
      layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH).with_updates(top=None, height=5))
    views = [
      GameView(self.gamestate, layout_options=LayoutOptions().with_updates(left=SIDEBAR_WIDTH, bottom=1)),
      StatsView(self.gamestate, layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH)),
      help_view,
      self.log_view,
    ]
    super().__init__(views, *args, **kwargs)

    level_state = self.gamestate.active_level_state
    level_state.dispatcher.add_subscriber(self, EnumEventNames.door_open, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_bumped, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_moved, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.player_died, None)

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

  def on_entity_moved(self, data):
    self.log_view.text = ""

  def on_entity_bumped(self, data):
    self.log("Oof!")

  def on_door_open(self, data):
    self.log("You open the door.")

  def on_player_died(self, data):
    if DEBUG_PROFILE: pr.dump_stats('profile')
    self.log("You have died.")
    self.director.push_scene(GameOverScene())

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
    super().terminal_update(is_active)
    self.gamestate.active_level_state.consume_events()
    if DEBUG_PROFILE: pr.disable()
