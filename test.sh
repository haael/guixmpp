#!/bin/bash

set -e

export PYTHONPATH=.

./gtkaio.py
protocol/dns/client.py
protocol/http/client.py

format/plain.py   # plain document model
format/xml.py     # xml tree document model
format/css.py     # css syntax tree document model
format/font.py    # fonts

render/svg.py     # svg parser
render/png.py     # png reader (cairo)
render/pixbuf.py  # image reader (gdk)
#render/html.py   # html
#render/xforms.py # xforms

download/data.py  # inline (data:) link support
download/file.py  # filesystem (file:) link support (dangerous)
download/http.py  # http & https link support
#download/xmpp.py # xmpp cid link support

view/display.py   # any view that displays contents on screen
view/pointer.py   # a view that has a pointer (i.e. mouse)
view/keyboard.py  # a view that has a keyboard

./domevents.py
./document.py

