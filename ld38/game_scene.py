from clubsandwich.ui import (
  LabelView,
  LayoutOptions,
  UIScene,
)

from .actions import (
  action_throw,
  action_close,
  action_move,
  action_pickup_item,
)
from .draw_game import draw_game
from .game_state import GameState
from .logger import Logger
from .music import NTrackPlayer
from .scenes import PauseScene, WinScene, LoseScene
from .sentences import simple_declarative_sentence
from .views import ProgressBarView, GameView, StatsView
from .const import (
  EnumEventNames,
  EnumFeature,
  EnumMonsterMode,
  verbs,
  key_bindings,
  BINDINGS_BY_KEY,
  KEYS_TO_DIRECTIONS,
)

DEBUG_PROFILE = False

N_TRACK_PLAYER = NTrackPlayer(['Q1.mp3', 'Q2.mp3', 'Q3.mp3', 'Q4.mp3'])

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


class GameAppearanceScene(UIScene):
  """
  Scene with the main game appearance
  """
  def __init__(self, game_state, *args, **kwargs):
    self.game_state = game_state
    self.n_track_player = N_TRACK_PLAYER

    log_view = LabelView(
      text="", align_horz='left', color_bg='#333333', clear=True,
      layout_options=LayoutOptions.row_bottom(1).with_updates(left=SIDEBAR_WIDTH))
    self.stats_view = StatsView(self.game_state, layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH))
    help_view = LabelView(
      text=TEXT_HELP, align_horz='left',
      layout_options=LayoutOptions.column_left(SIDEBAR_WIDTH).with_updates(top=None, height='intrinsic'))
    views = [
      GameView(self.game_state, layout_options=LayoutOptions().with_updates(left=SIDEBAR_WIDTH, bottom=1)),
      self.stats_view,
      help_view,
      log_view,
    ]
    super().__init__(views, *args, **kwargs)

    self.logger = Logger(log_view)
    self.covers_screen = True

  def enter(self, ctx):
    super().enter(ctx)
    self.ctx.clear()

  def exit(self):
    super().exit()
    self.ctx.clear()

  def terminal_update(self, is_active=True):
    if DEBUG_PROFILE: pr.enable()

    super().terminal_update(is_active)
    self.n_track_player.step()
    self.game_state.active_level_state.consume_events()
    self.logger.update_log()

    if DEBUG_PROFILE: pr.disable()


class GameModalInputScene(GameAppearanceScene):
  """Scene that looks like the main game but is waiting for specific input"""
  def terminal_read(self, val):
    level_state = self.game_state.active_level_state

    if val not in BINDINGS_BY_KEY:
      return

    self.handle_key(BINDINGS_BY_KEY[val])
    self.director.pop_scene()

  def handle_key(self, k):
    raise NotImplementedError()


class GameMainScene(GameAppearanceScene):
  def __init__(self, *args, **kwargs):
    super().__init__(GameState(), *args, **kwargs)
    self.n_track_player.reset()

    level_state = self.game_state.active_level_state
    level_state.dispatcher.add_subscriber(self, EnumEventNames.door_open, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_bumped, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_moved, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_took_damage, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_picked_up_item, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_died, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_attacking, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.score_increased, None)

  def exit(self):
    super().exit()
    self.n_track_player.stop()
    if DEBUG_PROFILE: pr.dump_stats('profile')

  def on_entity_moved(self, event):
    level_state = self.game_state.active_level_state
    cell = level_state.tilemap.cell(event.entity.position)
    if cell.feature == EnumFeature.STAIRS_DOWN:
      self.director.push_scene(WinScene(level_state.score))

    if cell.annotations & {'transition-1-2', 'transition-2-3', 'transition-3-4'}:
      self.n_track_player.set_active_track(None)

      ### HACK HACK HACK HACK ###
      # for "balance", replenish health between rooms
      level_state.player.state['hp'] = level_state.player.stats['hp_max']
      self.stats_view.update()
    
    room = level_state.tilemap.get_room(event.entity.position)
    if room and room.difficulty is not None:
      self.n_track_player.set_active_track(room.difficulty)

  def on_entity_bumped(self, event):
    self.logger.log("Oof!")

  def on_entity_took_damage(self, event):
    self.stats_view.update()

  def on_score_increased(self, event):
    self.stats_view.update()
    self.logger.log(simple_declarative_sentence('PLAYER', verbs.PICKUP, 'GOLD', 'a'))

  def on_door_open(self, event):
    self.logger.log("You opened the door.")

  def on_entity_attacking(self, event):
    self.logger.log(simple_declarative_sentence(
      event.entity.monster_type.id, verbs.HIT, event.data.monster_type.id))

    if event.data.mode == EnumMonsterMode.STUNNED:
      # fortunately this only happens to monsters, otherwise we'd have to
      # account for it.
      self.logger.log("It is stunned.")

  def on_entity_died(self, event):
    self.logger.log(simple_declarative_sentence(
      event.entity.monster_type.id, verb=verbs.DIE))

    if event.entity == self.game_state.active_level_state.player:
      if DEBUG_PROFILE: pr.dump_stats('profile')
      self.director.push_scene(LoseScene(self.game_state.active_level_state.score))

  def on_entity_picked_up_item(self, event):
    if self.game_state.active_level_state.get_can_player_see(event.entity.position):
      self.logger.log(simple_declarative_sentence(
        event.entity.monster_type.id,
        verbs.PICKUP,
        event.data.item_type.id,
        'a'
      ))
    self.stats_view.update()

  def terminal_read(self, val):
    if val not in BINDINGS_BY_KEY:
      return

    key = BINDINGS_BY_KEY[val]

    # blank out the log
    self.logger.log(' ')
    self.logger.update_log()

    self.handle_key(key)

  def handle_key(self, k):
    level_state = self.game_state.active_level_state
    if k in KEYS_TO_DIRECTIONS:
      point = level_state.player.position + KEYS_TO_DIRECTIONS[k]
      action_move(level_state, level_state.player, point)
    elif k == 'GET':
      action_pickup_item(level_state, level_state.player)
    elif k == 'WAIT':
      level_state.fire(EnumEventNames.player_took_action)
    elif k == 'CLOSE':
      self.director.push_scene(GameCloseScene(self.game_state))
    elif k == 'THROW':
      if level_state.player.inventory:
        self.director.push_scene(GameThrowScene(self.game_state))
      else:
        self.logger.log("You don't have anything to throw.")
    elif k == 'CANCEL':
      self.director.push_scene(PauseScene())


class GameThrowScene(GameModalInputScene):
  def enter(self, ctx):
    super().enter(ctx)
    self.logger.log("Throw in what direction?")

  def handle_key(self, k):
    level_state = self.game_state.active_level_state
    if k == 'CANCEL':
      return

    if k not in KEYS_TO_DIRECTIONS:
      self.logger.log("Invalid direction")
      return

    delta = KEYS_TO_DIRECTIONS[k]

    item = level_state.player.inventory[0]
    did_throw = action_throw(
      level_state,
      level_state.player, item, level_state.player.position + delta * 1000, 2)
    if did_throw:
      self.logger.log(simple_declarative_sentence('PLAYER', verbs.THROW, 'ROCK'))
    else:
      self.logger.log("You can't throw that in that direction.")


class GameCloseScene(GameModalInputScene):
  def enter(self, ctx):
    super().enter(ctx)
    self.logger.log("Close door in what direction?")

  def handle_key(self, k):
    level_state = self.game_state.active_level_state
    if k == 'CANCEL':
      return

    if k not in KEYS_TO_DIRECTIONS:
      self.logger.log("Invalid direction")
      return

    delta = KEYS_TO_DIRECTIONS[k]
    if action_close(level_state, level_state.player, level_state.player.position + delta):
      self.logger.log("You closed the door.")
    else:
      self.logger.log("There is no door there.")

