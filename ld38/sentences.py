from .const import entity_names


def get_safe_name(mt_id):
  try:
    return entity_names[mt_id]
  except KeyError:
    return entity_names.row_class(mt.id, "UNNAMED " + mt_id, False)


def get_name_with_article(name, article='the'):
  if name.is_second_person:
    return name.name
  else:
    return article + ' ' + name.name


def simple_declarative_sentence(subject_mt, verb, object_mt=None, object_article='the'):
  name1 = get_safe_name(subject_mt)
  parts = [
    get_name_with_article(name1),
    ' ',
    verb.present_2p if name1.is_second_person else verb.present_3p,
  ]
  if object_mt:
    parts.extend([
      ' ',
      get_name_with_article(get_safe_name(object_mt), object_article),
    ])
  s = ''.join(parts + ['.'])
  return s[0].upper() + s[1:]
