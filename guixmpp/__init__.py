#!/usr/bin/python3


__all__ = 'DOMWidget', 'XMPPClient', 'AuthenticationError', 'QueryError', 'asynchandler', 'loop_init', 'loop_main'


if __name__ == '__main__':
	print("GUIXMPP library")

else:
	try:
		DOMWidget
	except NameError:
		from .domwidget import *

	from .protocol.xmpp.client import *

	from .mainloop import *

