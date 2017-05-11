# Every frame, zero or more messages may be 'logged' by GameScene's event
# handlers. We want to make sure the player sees all of them.
#
# The basic approach here is that log() just adds a message to a list, and
# when update_log() is called, these messages are concatenated and put in
# a LabelView.
class Logger:
  def __init__(self, ui_label):
    # The label that shows the latest log message
    self.ui_label = ui_label
    self.log_messages = []

  def clear(self):
    # This is a silly hack, but it does work.
    self.log(' ')
    self.update_log()

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
            # "Picked up a rock (x3)"
            parts.append('{} (x{})'.format(last_message, dupe_count))
          else:
            parts.append(last_message)
          dupe_count = 1
          last_message = m
      if dupe_count > 1:
        # "Picked up a rock (x3)"
        parts.append('{} (x{})'.format(last_message, dupe_count))
      else:
        parts.append(last_message)
      self.ui_label.text = ' '.join(parts)
      self.log_messages = []