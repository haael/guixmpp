#!/usr/bin/python3


__all__ = 'DOMWidget', 'XMPPClient', 'ProtocolError', 'AuthenticationError', 'QueryError', 'asynchandler', 'loop_init', 'loop_main', 'loop_run', 'loop_quit', 'AllConnectionAttemptsFailedError', 'Renderer', 'render_to_surface', 'BuilderExtension'


if __name__ == '__main__':
	print("GUIXMPP library")

else:
	try:
		DOMWidget
	except NameError:
		from .domwidget import *
	
	from .renderer import *
	
	from .protocol.xmpp.client import *

	from .mainloop import *
	
	from .gtkaio import AllConnectionAttemptsFailedError
	
	from .builder_extension import *


