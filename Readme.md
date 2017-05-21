# Rogue Basement

A simple Python 3 roguelike

[Ludum Dare 38 page](https://ldjam.com/events/ludum-dare/38/rogue-basement)
[itch.io](https://irskep.itch.io/roguebasement)
[Article with design notes](http://steveasleep.com/the-design-and-implementation-of-rogue-basement.html)

## Setup

Requires Python 3.4+.

```sh
pip install -r requirements.txt
python run.py
```

## Annotated source code

There are a TON of comments! Start with `run.py`. You might want to keep
this page handy while you do: http://steveasleep.com/clubsandwich/

## Packaging

Rogue Basement can be packaged as an OS X or Windows app using PyInstaller.
Unfortunately, I never figured out how to get it to find the `.dylib` and
`.dll` files without explicitly specifying my machine-local path to them, so
fixing that is an exercise for the reader.
