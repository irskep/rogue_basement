import os
import sys
from pathlib import Path

os.environ["PYGLET_SHADOW_WINDOW"] = "false"
import pyglet

from clubsandwich.draw import draw_line_vert
from clubsandwich.blt.nice_terminal import terminal
from clubsandwich.geom import Size, Point, Rect
from clubsandwich.ui import (
  LabelView,
  ButtonView,
  LayoutOptions,
  UIScene,
  WindowView,
)

from .scenes import PauseScene, WinScene, LoseScene
from .views import ProgressBarView, GameView, StatsView
from .draw_game import draw_game
from .gamestate import GameState
from .const import (
  EnumEventNames,
  EnumMode,
  EnumFeature,
  EnumMonsterMode,
  verbs,
  key_bindings,
)
from .sentences import simple_declarative_sentence

DEBUG_PROFILE = False


root = Path(os.path.abspath(sys.argv[0])).parent
pyglet.resource.path = [str(root / 'assets')]
tracks = [
  pyglet.resource.media('Q1.mp3'),
  pyglet.resource.media('Q2.mp3'),
  pyglet.resource.media('Q3.mp3'),
  pyglet.resource.media('Q4.mp3'),
]


BINDINGS_BY_KEY = {}
for binding in key_bindings.items:
  for key in binding.keys:
    BINDINGS_BY_KEY[key] = binding.id


KEYS_TO_EVENTS = {
  'U': EnumEventNames.key_u,
  'D': EnumEventNames.key_d,
  'L': EnumEventNames.key_l,
  'R': EnumEventNames.key_r,
  'UL': EnumEventNames.key_ul,
  'UR': EnumEventNames.key_ur,
  'DL': EnumEventNames.key_dl,
  'DR': EnumEventNames.key_dr,
  'WAIT': EnumEventNames.player_took_action,
  'GET': EnumEventNames.key_get,
}

KEYS_TO_DIRECTIONS = {
  'U': Point(0, -1),
  'D': Point(0, 1),
  'L': Point(-1, 0),
  'R': Point(1, 0),
  'UL': Point(-1, -1),
  'UR': Point(1, -1),
  'DL': Point(-1, 1),
  'DR': Point(1, 1),
}

SIDEBAR_WIDTH = 21

TEXT_HELP = """
======= Keys =======
Move: arrows, numpad
      hjklyubn

Get rock: g
Throw rock: t
Close: c

""".strip()


if DEBUG_PROFILE:
  import cProfile
  pr = cProfile.Profile()


players = [pyglet.media.Player() for _ in range(4)]
for i, player in enumerate(players):
  player.queue(tracks[i])
  player.eos_action = player.EOS_LOOP
class GameScene(UIScene):
  def __init__(self, *args, **kwargs):
    self.player_volume_directions = ['up', 'down', 'down', 'down']

    self.players = players
    for i, player in enumerate(self.players):
      player.seek(0)
      if i == 0:
        player.play()
      else:
        player.volume = 0

    self.log_messages = []

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

  def enter(self, ctx):
    super().enter(ctx)
    self.ctx.clear()

  def exit(self):
    super().exit()
    self.ctx.clear()
    for player in self.players:
      player.pause()
      player.seek(0)
    if DEBUG_PROFILE: pr.dump_stats('profile')

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
    if text.strip():
      print(text)
    self.log_messages.append(text)

  def update_log(self):
    if self.log_messages:
      parts = []
      last_message = self.log_messages[0]
      dupe_count = 1
      for m in self.log_messages[1:]:
        if m == last_message:
          dupe_count += 1
        else:
          if dupe_count > 1:
            parts.append('{} (x{})'.format(last_message, dupe_count))
          else:
            parts.append(last_message)
          dupe_count = 1
          last_message = m
      if dupe_count > 1:
        parts.append('{} (x{})'.format(last_message, dupe_count))
      else:
        parts.append(last_message)
      self.log_view.text = ' '.join(parts)
      self.log_messages = []

  def on_entity_moved(self, event):
    level_state = self.gamestate.active_level_state
    cell = level_state.tilemap.cell(event.entity.position)
    self.log_view.text = ""
    if cell.feature == EnumFeature.STAIRS_DOWN:
      self.director.push_scene(WinScene(level_state.score))

    if cell.annotations & {'transition-1-2', 'transition-2-3', 'transition-3-4'}:
      self.player_volume_directions = ['down', 'down', 'down', 'down']

      ### HACK HACK HACK HACK ###
      # for "balance", replenish health between rooms
      level_state.player.state['hp'] = level_state.player.stats['hp_max']
      self.stats_view.update()
    
    room = level_state.tilemap.get_room(event.entity.position)
    if room and room.difficulty is not None:
      self.player_volume_directions = ['down', 'down', 'down', 'down']
      self.player_volume_directions[room.difficulty] = 'up'

  def on_entity_bumped(self, event):
    self.log("Oof!")

  def on_entity_took_damage(self, event):
    self.stats_view.update()

  def on_score_increased(self, event):
    self.stats_view.update()
    self.log(simple_declarative_sentence('PLAYER', verbs.PICKUP, 'GOLD', 'a'))

  def on_door_open(self, event):
    self.log("You opened the door.")

  def on_entity_attacking(self, event):
    self.log(simple_declarative_sentence(
      event.entity.monster_type.id, verbs.HIT, event.data.monster_type.id))

    if event.data.mode == EnumMonsterMode.STUNNED:
      # fortunately this only happens to monsters, otherwise we'd have to
      # account for it.
      self.log("It is stunned.")

  def on_entity_died(self, event):
    self.log(simple_declarative_sentence(
      event.entity.monster_type.id, verb=verbs.DIE))

    if event.entity == self.gamestate.active_level_state.player:
      if DEBUG_PROFILE: pr.dump_stats('profile')
      self.director.push_scene(LoseScene(self.gamestate.active_level_state.score))

  def on_entity_picked_up_item(self, event):
    if self.gamestate.active_level_state.get_can_player_see(event.entity.position):
      self.log(simple_declarative_sentence(
        event.entity.monster_type.id,
        verbs.PICKUP,
        event.data.item_type.id,
        'a'
      ))
    self.stats_view.update()

  def terminal_read(self, val):
    level_state = self.gamestate.active_level_state

    if val not in BINDINGS_BY_KEY:
      return

    key = BINDINGS_BY_KEY[val]

    self.log(' ')
    self.update_log()
    
    if self.mode == EnumMode.DEFAULT:
      self.handle_key_default(key)
    elif self.mode == EnumMode.CLOSE:
      self.handle_key_door_close(key)
    elif self.mode == EnumMode.THROW:
      self.handle_key_throw(key)

  def handle_key_default(self, k):
    level_state = self.gamestate.active_level_state
    if k in KEYS_TO_EVENTS:
      level_state.fire(KEYS_TO_EVENTS[k])

    if k == 'CLOSE':
      self.log("Close door in what direction?")
      self.mode = EnumMode.CLOSE

    if k == 'THROW':
      if level_state.player.inventory:
        self.mode = EnumMode.THROW
        self.log("Throw in what direction?")
      else:
        self.log("You don't have anything to throw.")

    if k == 'CANCEL':
      self.director.push_scene(PauseScene())

  def handle_key_door_close(self, k):
    level_state = self.gamestate.active_level_state
    if k == 'CANCEL':
      self.mode = EnumMode.DEFAULT
      return

    if k not in KEYS_TO_DIRECTIONS:
      self.log("Invalid direction")
      self.mode = EnumMode.DEFAULT
      return

    delta = KEYS_TO_DIRECTIONS[k]
    if level_state.action_close(level_state.player, level_state.player.position + delta):
      self.log("You closed the door.")
    else:
      self.log("There is no door there.")
    self.mode = EnumMode.DEFAULT

  def handle_key_throw(self, k):
    level_state = self.gamestate.active_level_state
    if k == 'CANCEL':
      self.mode = EnumMode.DEFAULT
      return

    if k not in KEYS_TO_DIRECTIONS:
      self.log("Invalid direction")
      self.mode = EnumMode.DEFAULT
      return

    delta = KEYS_TO_DIRECTIONS[k]

    item = level_state.player.inventory[0]
    did_throw = level_state.action_throw(
      level_state.player, item, level_state.player.position + delta * 1000, 2)
    if did_throw:
      self.log("You throw the {}".format(item.item_type.id))
    else:
      self.log("You can't throw that in that direction.")
    self.mode = EnumMode.DEFAULT

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

    self.update_log()
