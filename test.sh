#!/bin/bash

set -e

PYTHONPATH=. format/plain.py # plain document model
PYTHONPATH=. format/xml.py   # xml tree document model
PYTHONPATH=. format/image.py # image surface document model
PYTHONPATH=. format/css.py   # css syntax tree document model
PYTHONPATH=. format/svg.py   # svg parser
PYTHONPATH=. format/png.py   # png reader (cairo)
PYTHONPATH=. format/image.py # image reader (gdk)

PYTHONPATH=. download/data.py # inline (data:) link support
PYTHONPATH=. download/file.py # filesystem (file:) link support (dangerous)
PYTHONPATH=. download/http.py # http & https link support
#PYTHONPATH=. download/xmpp.py # xmpp cid link support

PYTHONPATH=. ./domevents.py
PYTHONPATH=. ./document.py

