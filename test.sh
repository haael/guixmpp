#!/bin/bash

set -e

export PYTHONPATH=.

format/plain.py   # plain document model
format/xml.py     # xml tree document model
format/css.py     # css syntax tree document model
format/xforms.py  # xforms
format/font.py    # fonts

image/svg.py      # svg parser
image/png.py      # png reader (cairo)
image/pixbuf.py   # image reader (gdk)

download/data.py  # inline (data:) link support
download/file.py  # filesystem (file:) link support (dangerous)
download/http.py  # http & https link support
#download/xmpp.py # xmpp cid link support

view/display.py   # any view that displays contents on screen
view/pointer.py   # a view that has a pointer (i.e. mouse)
view/keyboard.py  # a view that has a keyboard

./domevents.py
./document.py

