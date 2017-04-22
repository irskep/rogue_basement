#!/usr/bin/env python
from enum import Enum

from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.draw import draw_line_vert
from clubsandwich.geom import Size, Point, Rect
from clubsandwich.ui import (
  LabelView,
  ButtonView,
  LayoutOptions,
  UIScene,
  View,
)

from .draw_game import draw_game
from .gamestate import GameState
from .const import EnumEventNames


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
      layout_options=LayoutOptions.row_top(1).with_updates(right=1)))


  def draw(self, ctx):
    ctx.color('#ffffff')
    draw_line_vert(Point(self.bounds.x2, self.bounds.y), self.bounds.height)


class GameScene(UIScene):
  def __init__(self, *args, **kwargs):
    self.gamestate = GameState()
    self.log_view = LabelView(
      text="", align_horz='left', color_bg='#333333',
      layout_options=LayoutOptions.row_bottom(1).with_updates(left=20))
    views = [
      GameView(self.gamestate, layout_options=LayoutOptions().with_updates(left=20, bottom=1)),
      StatsView(self.gamestate, layout_options=LayoutOptions.column_left(20)),
      self.log_view,
    ]
    super().__init__(views, *args, **kwargs)

    level_state = self.gamestate.active_level_state
    level_state.dispatcher.add_subscriber(self, EnumEventNames.door_open, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_bumped, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_moved, level_state.player)

  def on_entity_moved(self, data):
    self.log_view.text = ""

  def on_entity_bumped(self, data):
    self.log_view.text = "Oof!"

  def on_door_open(self, data):
    self.log_view.text = "You open the door."

  def terminal_read(self, val):
    if val in (terminal.TK_UP, terminal.TK_K, terminal.TK_KP_8):
      self.gamestate.active_level_state.fire(EnumEventNames.key_u)
    if val in (terminal.TK_DOWN, terminal.TK_J, terminal.TK_KP_2):
      self.gamestate.active_level_state.fire(EnumEventNames.key_d)
    if val in (terminal.TK_LEFT, terminal.TK_H, terminal.TK_KP_4):
      self.gamestate.active_level_state.fire(EnumEventNames.key_l)
    if val in (terminal.TK_RIGHT, terminal.TK_L, terminal.TK_KP_6):
      self.gamestate.active_level_state.fire(EnumEventNames.key_r)
    if val in (terminal.TK_Y, terminal.TK_KP_7):
      self.gamestate.active_level_state.fire(EnumEventNames.key_ul)
    if val in (terminal.TK_U, terminal.TK_KP_9):
      self.gamestate.active_level_state.fire(EnumEventNames.key_ur)
    if val in (terminal.TK_B, terminal.TK_KP_1):
      self.gamestate.active_level_state.fire(EnumEventNames.key_dl)
    if val in (terminal.TK_N, terminal.TK_KP_3):
      self.gamestate.active_level_state.fire(EnumEventNames.key_dr)

  def terminal_update(self, is_active=True):
    super().terminal_update(is_active)
    self.gamestate.active_level_state.consume_events()
