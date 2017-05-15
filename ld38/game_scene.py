# This file has a lot going on in it because really ties the game together,
# just like The Dude's rug. You can probably read it start to finish, but
# by all means start jumping around from here.

# Dependencies for rendering the UI
from clubsandwich.ui import (
  LabelView,
  LayoutOptions,
  UIScene,
)
# including some ones written specifically for this game
from .views import ProgressBarView, GameView, StatsView

# Whenever you go to another "screen," you're visiting a scene. These are the
# scenes you can get to from the game scene.
from .scenes import PauseScene, WinScene, LoseScene

# This object stores the state of the whole game, so we're definitely gonna
# need that.
from .game_state import GameState

# When keys are pressed, we'll call these functions to have the player do
# things.
from .actions import (
  action_throw,
  action_close,
  action_move,
  action_pickup_item,
)

# When things happen, we need to show status messages at the bottom of the
# screen. Since more than one thing can happen in a frame, there's some
# subtle logic encapsulated in this Logger object.
from .logger import Logger

# Constructing arbitrary English sentences from component parts is not always
# simple. This function makes it read nicer in code.
from .sentences import simple_declarative_sentence

# There are four tracks that can play at any given time. Pyglet (the library
# used for audio) doesn't have easy "fade" support, so this object tracks and
# modifies volumes for each track per frame.
from .music import NTrackPlayer

# const.py does some interesting things that you should look at when you're
# interested. For now, here are some hints:
from .const import (
  # Enums are collections of unique identifiers. In roguelikes it's usually
  # better to keep everything in data files, but for a small game like this
  # it's not a big deal to have a few small ones.
  EnumEventNames,
  EnumFeature,
  EnumMonsterMode,
  # These are collections of values from data files:
  verbs,        # from verbs.csv
  key_bindings, # from key_bindings.csv
  # This is a reverse mapping of key_bindings.csv so we can turn
  # a raw key value into a usable command.
  BINDINGS_BY_KEY,
  # Map of key binding ID to a clubsandwich.geom.Point object representing a
  # direction.
  KEYS_TO_DIRECTIONS,
)

# At some point this game was slow. This flag enables profiling. You can
# ignore it.
DEBUG_PROFILE = False
if DEBUG_PROFILE:
  import cProfile
  pr = cProfile.Profile()

# All game scenes share an instance of the player because the audio should be
# continuous. It's a bit of a hack that it's a global variable, but this was a
# 48-hour game, so deal with it.
N_TRACK_PLAYER = NTrackPlayer(['Q1.mp3', 'Q2.mp3', 'Q3.mp3', 'Q4.mp3'])

# This is the text that appears at the bottom left of the screen.
TEXT_HELP = """
======= Keys =======
Move: arrows, numpad
      hjklyubn

Get rock: g
Throw rock: t
Close: c
""".strip()


# While you're playing the game, there are actually 3 modes of input:
#
#    * Normal: move, wait, get, close, throw
#    * Prompting for throw direction
#    * Prompting for close direction
#
# These states were originally handled with a "mode" property, but it turns out
# to be MUCH simpler if there are just 3 completely different scenes for these
# things that happen to draw the screen the same way. That way you never have
# any "if mode == PROMPT_THROW_DIRECTION" blocks or anything.
#
# So those 3 scenes all inherit from this base class.
class GameAppearanceScene(UIScene):
  def __init__(self, game_state, *args, **kwargs):
    # All the game scenes share a GameState object.
    self.game_state = game_state

    # They also use the global player, but access it via a property just in
    # case I change my mind later.
    self.n_track_player = N_TRACK_PLAYER

    # Make some views. Read the clubsandwich docs for details on this stuff.
    # Some of them we just add as subviews and forget about, but the stats
    # view will need to be updated from time to time, so hang onto a reference
    # to it.
    sidebar_width = 21
    # The game drawing is all done by this GameView object. It happens every
    # frame, so we can mostly forget about it for now.
    game_view = GameView(
      self.game_state,
      layout_options=LayoutOptions().with_updates(left=sidebar_width, bottom=1)) 
    log_view = LabelView(
      text="", align_horz='left', color_bg='#333333', clear=True,
      layout_options=LayoutOptions.row_bottom(1)
                                  .with_updates(left=sidebar_width))
    help_view = LabelView(
      text=TEXT_HELP, align_horz='left',
      layout_options=LayoutOptions.column_left(sidebar_width)
                                  .with_updates(top=None, height='intrinsic'))
    self.stats_view = StatsView(
      self.game_state, layout_options=LayoutOptions.column_left(sidebar_width))
    views = [
      game_view,
      self.stats_view,
      help_view,
      log_view,
    ]
    super().__init__(views, *args, **kwargs)

    # Each game scene has its own log controller. It's defined after the super()
    # call because it needs log_view to exist.
    self.logger = Logger(log_view)

    # This boolean signals to DirectorLoop that it doesn't need to draw any
    # scenes behind this one. (Compare with the pause screen, which wants the
    # game scene to be drawn behind it, since it's a popup window!)
    self.covers_screen = True

  def enter(self, ctx):
    super().enter(ctx)
    # When this scene becomes active, clear everything. There is no convention
    # for who clears the screen, so just handle it on all changes.
    self.ctx.clear()

  def exit(self):
    super().exit()
    # same reason as enter()
    self.ctx.clear()

  # This function is called by DirectorLoop every frame. It does important
  # things!
  def terminal_update(self, is_active=True):
    if DEBUG_PROFILE: pr.enable()

    # Fade music in/out if necessary
    self.n_track_player.step()

    # Tell the LevelState object to deal with any events in its queue. The
    # event system is pretty sophisticated, more on that later.
    self.game_state.level.consume_events()

    # Tell the logger to display any log entries in its queue, or leave the
    # log unchanged.
    self.logger.update_log()

    # The superclass draws all the views
    super().terminal_update(is_active)

    if DEBUG_PROFILE: pr.disable()


# This is another abstract base class, subclassing the one above. Two of the
# three game scenes are just waiting for a single keystroke for input. This
# class abstracts that behavior.
class GameModalInputScene(GameAppearanceScene):
  # DirectorLoop calls terminal_read() on the active scene when input is
  # available. You might want to read the BearLibTerminal docs for
  # terminal_read(). `val` is the return value of that function.
  def terminal_read(self, val):
    # Ignore input from unbound keys
    if val not in BINDINGS_BY_KEY:
      return

    # Read one keystroke and pop back to the previous scene.      
    # (DirectorLoop stores scenes as a stack.)
    level_state = self.game_state.level
    self.handle_key(BINDINGS_BY_KEY[val])
    self.director.pop_scene()

  # `k` in this function is one of the values in the left column from
  # key_bindings.csv.
  def handle_key(self, k):
    raise NotImplementedError()


# Finally, some real action! This is the main game scene, as the name says.
# This object has a lot of responsibilities:
#
#    * Reset things for a new game
#    * Display world events to the user
#    * Act on main game input
#    * Assorted hacks
#
# Let's dive in!
class GameMainScene(GameAppearanceScene):
  def __init__(self, *args, **kwargs):
    # Create a fresh GameState object
    super().__init__(GameState(), *args, **kwargs)
    # Reset the music player in case this isn't the first game since the
    # process launched
    self.n_track_player.reset()

    # Subscribe to a bunch of events. This probably looks a little weird, so
    # you might want to read the docs for clubsandwich.event_dispatcher.
    level_state = self.game_state.level
    # But basically, this means "when the 'door_open' event is fired on the
    # player entity, call self.on_door_open(event)."
    level_state.dispatcher.add_subscriber(self, EnumEventNames.door_open, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_bumped, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_moved, level_state.player)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_took_damage, level_state.player)
    # These event handlers respond to all events with matching names,
    # regardless of which entity they are attached to.
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_picked_up_item, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_died, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.entity_attacking, None)
    level_state.dispatcher.add_subscriber(self, EnumEventNames.score_increased, None)

  def exit(self):
    super().exit()
    # Stop the music and write profiler data to disk when the game ends.
    self.n_track_player.stop()
    if DEBUG_PROFILE: pr.dump_stats('profile')

  ### event handlers ###
  # (things that happen in response to world events)

  ## player events ##
  # (only called when these events are attached to the player)

  def on_entity_moved(self, event):
    level_state = self.game_state.level

    # Here is the first appearance of the tilemap API. This just gets us a
    # RogueBasementCell object (see level_generator.py) for a given position.
    cell = level_state.tilemap.cell(event.entity.position)

    # This game only has one level, so exit stairs means game win! Yay!
    # And "winning" means "show a cute dialog." And the dialog looks almost
    # exactly like the losing dialog, except it says "you win" instead of
    # "you lose." How satisfying!
    if cell.feature == EnumFeature.STAIRS_DOWN:
      self.director.push_scene(WinScene(self.game_state.score))

    # "Annotations" are just little notes left to us by the level generator.
    # These annotations in particular mean "this cell is part of a corridor
    # leading between two areas of different difficulty."
    if cell.annotations & {'transition-1-2', 'transition-2-3', 'transition-3-4'}:
      # Fade the music out. DRAMA!!!
      self.n_track_player.set_active_track(None)

      ### HACK HACK HACK HACK ###
      # For "balance", replenish health between rooms.
      # This was added in the last hour or so of the compo. It might be better
      # to implement this as a cell Feature instead of this annotation, but eh,
      # at this point it's not worth fixing.
      level_state.player.state['hp'] = level_state.player.stats['hp_max']
      self.logger.log("The glowing corridor restores you to health.")
      # Whenever we update player state, we have to manually update the stats
      # view. Not really the best workflow; the stats view ought to update
      # itself every frame! But again, eh, whatever, it works.
      self.stats_view.update()
    
    # The level generator creates Room objects which know what area they are
    # in. We can look them up by position. If this cell has a Room, then tell
    # the music player to play the relevant track.
    room = level_state.tilemap.get_room(event.entity.position)
    if room and room.difficulty is not None:
      self.n_track_player.set_active_track(room.difficulty)

  def on_entity_bumped(self, event):
    self.logger.log("Oof!")

  def on_entity_took_damage(self, event):
    self.stats_view.update()

  def on_door_open(self, event):
    self.logger.log("You opened the door.")

  ## global events ##
  # (called no matter what the entity is)

  def on_entity_attacking(self, event):
    # "You hit the verp. The verp hits you."
    self.logger.log(simple_declarative_sentence(
      event.entity.monster_type.id, verbs.HIT, event.data.monster_type.id))

    if event.data.mode == EnumMonsterMode.STUNNED:
      # This only happens to monsters, otherwise we'd have to
      # account for it in our text generator. How fortunate!
      self.logger.log("It is stunned.")

  def on_entity_died(self, event):
    # "You die." "The wibble dies."
    self.logger.log(simple_declarative_sentence(
      event.entity.monster_type.id, verb=verbs.DIE))

    if event.entity == self.game_state.level.player:
      # Funny how losing looks just like winning...
      self.director.push_scene(LoseScene(self.game_state.score))

  def on_entity_picked_up_item(self, event):
    if self.game_state.level.get_can_player_see(event.entity.position):
      self.logger.log(simple_declarative_sentence(
        event.entity.monster_type.id,
        verbs.PICKUP,
        event.data.item_type.id,
        'a'
      ))
    self.stats_view.update()  # inventory count may have changed!

  def on_score_increased(self, event):
    # Coins are a special case. If you pick one up, the entity_picked_up_item
    # event is not fired. Instead, you get this score_increased event.
    #
    # The reason is that the inventory system is very stupid, and keeping coins
    # in it would be useless.
    self.stats_view.update()  # score changed
    self.logger.log(simple_declarative_sentence(
      'PLAYER', verbs.PICKUP, 'GOLD', 'a'))

  # ooh, we got a keystroke!
  def terminal_read(self, val):
    # Ignore unbound keys
    if val not in BINDINGS_BY_KEY:
      return

    key = BINDINGS_BY_KEY[val]

    self.logger.clear()

    self.handle_key(key)

  def handle_key(self, k):
    level_state = self.game_state.level
    # Remember that `k` is one of the left column values in key_bindings.csv.
    if k in KEYS_TO_DIRECTIONS:
      # If the key represents a direction, try to move in that direction.
      point = level_state.player.position + KEYS_TO_DIRECTIONS[k]
      action_move(level_state, level_state.player, point)
    elif k == 'GET':
      action_pickup_item(level_state, level_state.player)
    elif k == 'WAIT':
      # The easiest implementation of "wait" is to just fire the event that
      # says "the player did something, you can move now" without the player
      # having actually done anything.
      level_state.fire_player_took_action_if_alive()
    elif k == 'CLOSE':
      # Now it's time to push one of those fancy modal-input scenes I've talked
      # so much about!
      self.director.push_scene(GameCloseScene(self.game_state))
    elif k == 'THROW':
      if level_state.player.inventory:
        # Ooh, another one!
        self.director.push_scene(GameThrowScene(self.game_state))
      else:
        # HAHA LOL PLAYER U SUX
        self.logger.log("You don't have anything to throw.")
    elif k == 'CANCEL':
      self.director.push_scene(PauseScene())


# At this point, you should be able to read the last two classes yourself
# without my help. From here, you should jump around to whatever interests you!
# I would suggest a reading order of something like:
#    * const.py
#    * entity.py
#    * game_state.py
#    * level_state.py
#    * behavior.py
#    * actions.py
#    * level_generator.py
#    * views.py
#    * draw_game.py


class GameThrowScene(GameModalInputScene):
  def enter(self, ctx):
    super().enter(ctx)
    self.logger.log("Throw in what direction?")

  def handle_key(self, k):
    level_state = self.game_state.level
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
    level_state = self.game_state.level
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

