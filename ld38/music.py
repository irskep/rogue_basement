import os
import sys
from pathlib import Path

os.environ["PYGLET_SHADOW_WINDOW"] = "false"
import pyglet


root = Path(os.path.abspath(sys.argv[0])).parent
pyglet.resource.path = [str(root / 'assets')]


class NTrackPlayer:
  """
  Fade an arbitrary number of tracks in and out in a pretty low-tech way.
  Does not unload files when stopped, so it needs to be an app-global
  singleton.

  You must call :py:meth:`step` each frame for fading to work properly.
  """
  def __init__(self, track_names):
    self.players = []
    self.tracks = []
    for name in track_names:
      track = pyglet.resource.media(name)
      self.tracks.append(track)
      player = pyglet.media.Player()
      self.players.append(player)
      player.queue(track)
      player.eos_action = player.EOS_LOOP

  def reset(self):
    self.player_volume_directions = ['down' for _ in range(len(self.tracks))]
    self.player_volume_directions[0] = 'up'
    for i, player in enumerate(self.players):
      player.seek(0)
      if i == 0:
        player.play()
      else:
        player.volume = 0

  def stop(self):
    for player in self.players:
      player.pause()
      player.seek(0)

  def step(self):
    for i, (direction, player) in enumerate(zip(self.player_volume_directions, self.players)):
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

  def set_active_track(self, i):
    self.player_volume_directions = ['down' for _ in range(len(self.tracks))]
    if i is not None:
      self.player_volume_directions[i] = 'up'
