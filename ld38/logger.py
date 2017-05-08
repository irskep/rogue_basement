class Logger:
  def __init__(self, ui_label):
    self.ui_label = ui_label
    self.log_messages = []

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
      self.ui_label.text = ' '.join(parts)
      self.log_messages = []