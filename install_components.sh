#!/usr/bin/env bash

apt-get install python3-cairo* libcairo2-dev libjpeg-dev libgif-dev
apt-get install -y --no-install-recommends python3-dev python3-cffi libcairo2 libpangocairo-1.0.0 libffi-dev

pip install cssselect2
pip install defusedxml
ln -s ./submodules/pycairo/build/lib.linux-x86_64-3.5/cairo/ ./cairo
