#!/usr/bin/env bash

pyver="$(python3 --version | cut -c8-10)"
(
 cd submodules/pycairo
 rm -rf build
 mkdir build
 python3 ./setup.py build
)
ln -sf ./submodules/pycairo/build/lib.linux-x86_64-${pyver}/cairo
ln -sf ./submodules/CairoSVG/cairosvg
ln -sf ./submodules/slixmpp/build/lib/slixmpp
