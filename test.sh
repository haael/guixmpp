#!/bin/bash

set -e

PYTHONPATH=. format/plain.py   # plain document model
PYTHONPATH=. format/xml.py     # xml tree document model
PYTHONPATH=. format/css.py     # css syntax tree document model
PYTHONPATH=. format/xforms.py  # xforms
PYTHONPATH=. format/font.py    # fonts

PYTHONPATH=. image/svg.py      # svg parser
PYTHONPATH=. image/png.py      # png reader (cairo)
PYTHONPATH=. image/pixbuf.py   # image reader (gdk)

PYTHONPATH=. download/data.py  # inline (data:) link support
PYTHONPATH=. download/file.py  # filesystem (file:) link support (dangerous)
PYTHONPATH=. download/http.py  # http & https link support
#PYTHONPATH=. download/xmpp.py # xmpp cid link support

PYTHONPATH=. view/display.py   # any view that displays contents on screen
PYTHONPATH=. view/pointer.py   # a view that has a pointer (i.e. mouse)
PYTHONPATH=. view/keyboard.py  # a view that has a keyboard

PYTHONPATH=. ./domevents.py
PYTHONPATH=. ./document.py

