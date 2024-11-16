#!/usr/bin/python3


__all__ = 'DOMWidget', 'XMPPClient', 'ProtocolError', 'AuthenticationError', 'QueryError', \
          'asynchandler', 'loop_init', 'loop_main', 'loop_run', 'loop_quit', \
          'AllConnectionAttemptsFailedError', 'Renderer', 'render_to_surface', 'BuilderExtension', 'Path'


if __name__ == '__main__':
	print("GUIXMPP library")

else:
	def __dir__():
		return __all__
	
	def __getattr__(symbol):
		if symbol == 'DOMWidget':
			from .domwidget import DOMWidget
			return DOMWidget
		
		elif symbol == 'XMPPClient':
			from .protocol.xmpp.client import XMPPClient
			return XMPPClient
		
		elif symbol == 'ProtocolError':
			from .protocol.xmpp.client import ProtocolError
			return ProtocolError
		
		elif symbol == 'AuthenticationError':
			from .protocol.xmpp.client import AuthenticationError
			return AuthenticationError
		
		elif symbol == 'QueryError':
			from .protocol.xmpp.client import QueryError
			return QueryError
		
		elif symbol == 'asynchandler':
			from .mainloop import asynchandler
			return asynchandler
		
		elif symbol == 'loop_init':
			from .mainloop import loop_init
			return loop_init
		
		elif symbol == 'loop_main':
			from .mainloop import loop_main
			return loop_main
		
		elif symbol == 'loop_run':
			from .mainloop import loop_run
			return loop_run
		
		elif symbol == 'loop_quit':
			from .mainloop import loop_quit
			return loop_quit
		
		elif symbol == 'AllConnectionAttemptsFailedError':
			from .gtkaio import AllConnectionAttemptsFailedError
			return AllConnectionAttemptsFailedError
		
		elif symbol == 'Renderer':
			from .renderer import Renderer
			return Renderer
		
		elif symbol == 'render_to_surface':
			from .renderer import render_to_surface
			return render_to_surface
		
		elif symbol == 'BuilderExtension':
			from .builder_extension import BuilderExtension
			return BuilderExtension
		
		elif symbol == 'Path':
			from .gtkaiopath import Path
			return Path
		
		else:
			raise AttributeError

