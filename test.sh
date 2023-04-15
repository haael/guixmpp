#!/bin/bash

set -e

PYTHONPATH=. model/plain.py # plain document model
PYTHONPATH=. model/xml.py   # xml tree document model
PYTHONPATH=. model/image.py # image surface document model
PYTHONPATH=. model/css.py   # css syntax tree document model

PYTHONPATH=. format/css.py   # css 3 parser (css model)
PYTHONPATH=. format/svg.py   # svg parser (xml model)
PYTHONPATH=. format/png.py   # png reader (cairo, image model)
PYTHONPATH=. format/image.py # image reader (gdk, image model)

PYTHONPATH=. download/data.py # inline (data:) link support
PYTHONPATH=. download/file.py # filesystem (file:) link support (dangerous)
PYTHONPATH=. download/http.py # http & https link support
PYTHONPATH=. download/xmpp.py # xmpp cid link support

PYTHONPATH=. render/svg.py    # svg render over cairo
PYTHONPATH=. render/image.py  # image surface render over cairo

document_model.py
dom_events.py

