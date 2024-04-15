#!/usr/bin/python3


__all__ = 'DOMWidget', 'XMPPClient', 'XMPPError', 'ProtocolError', 'StreamError', 'AuthenticationError', 'QueryError', 'asynchandler', 'loop_init', 'loop_run', 'loop_quit'


if __name__ == '__main__':
	print("GUIXMPP library")

else:
	try:
		DOMWidget
	except NameError:
		from .domwidget import *

	from .protocol.xmpp.client import *

	from .mainloop import *

