#!/usr/bin/python3


__all__ = 'DOMWidget', 'XMPPClient', 'asynchandler', 'loop_init', 'loop_run', 'loop_quit'

try:
	DOMWidget
except NameError:
	from .domwidget import DOMWidget

from .protocol.xmpp.client import XMPPClient

from .mainloop import asynchandler, loop_init, loop_run, loop_quit

