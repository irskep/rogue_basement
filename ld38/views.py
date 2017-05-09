from math import floor

from clubsandwich.draw import draw_line_vert
from clubsandwich.geom import Size, Point, Rect
from clubsandwich.ui import (
  LabelView,
  LayoutOptions,
  View,
)

from .draw_game import draw_game


class ProgressBarView(View):
  def __init__(self, fraction, color_fg='#0088ff', color_bg='#000000', *args, **kwargs):
    self.fraction = fraction
    self.color_fg = color_fg
    self.color_bg = color_bg
    super().__init__(*args, **kwargs)

  def draw(self, ctx):
    ctx.bkcolor(self.color_bg)
    ctx.clear_area(self.bounds)
    frac_width = floor(self.bounds.width * self.fraction)
    ctx.bkcolor(self.color_fg)
    ctx.clear_area(self.bounds.with_size(Size(frac_width, self.bounds.height)))


class GameView(View):
  def __init__(self, game_state, *args, **kwargs):
    self.game_state = game_state
    super().__init__(*args, **kwargs)
    self.last_known_player_position = Point(0, 0)

  def draw(self, ctx):
    ctx.bkcolor('#000000')
    ctx.clear_area(self.bounds)

    current_player_position = self.game_state.active_level_state.player.position  
    if current_player_position is not None:
      self.last_known_player_position = current_player_position
    half_size = (self.bounds.size / 2).floored
    draw_game(
      self.game_state,
      bounds=Rect(
        self.last_known_player_position - half_size,
        self.bounds.size),
      ctx=ctx)


class StatsView(View):
  def __init__(self, game_state, *args, **kwargs):
    self.game_state = game_state
    self.progress_bar = ProgressBarView(
      fraction=1,
      layout_options=LayoutOptions.row_top(1).with_updates(top=3, right=1))
    self.health_label = LabelView(
      text="  Health: ?  ",
      color_fg="#ffffff",
      color_bg='#000000',
      layout_options=LayoutOptions.row_top(1).with_updates(top=2, right=1))
    self.inventory_count = LabelView(
      text="  Rocks: 0  ",
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
      self.game_state.active_level_state.player.state['hp'] /
      self.game_state.active_level_state.player.stats['hp_max'])
    self.inventory_count.text = "  Rocks: {}  ".format(
      len(self.game_state.active_level_state.player.inventory))
    # HACK: extra padding so the label clears its background properly when it
    # shrinks
    self.health_label.text = "  Health: {}  ".format(
      self.game_state.active_level_state.player.state['hp'])
    self.score_label.text = "Score: {}".format(
      self.game_state.active_level_state.score)

  def draw(self, ctx):
    ctx.color('#ffffff')
    draw_line_vert(Point(self.bounds.x2, self.bounds.y), self.bounds.height)