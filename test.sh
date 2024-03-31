#!/bin/bash

set -e

export PYTHONPATH=.

find guixmpp -iname '*.py' | while read script; do
 $script
done
