#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DocumentModel',


from collections import defaultdict
from asyncio import gather, Lock, Event, TaskGroup, CancelledError
from inspect import isawaitable

if __name__ == '__main__':
	from guixmpp.domevents import UIEvent, CustomEvent
else:
	from .domevents import UIEvent, CustomEvent


class DocumentNotFound(Exception):
	pass


class Model:
	"A structure holding a collection of documents, capable of loading and unloading."
		
	@staticmethod
	def features(name, *classes):
		return type(name, (Model,) + classes, {})
	
	def __init__(self, *args, **kwargs):
		self.documents = {}
		self.emitted_warnings = set()
		self.__downloading = {}
		self.__start_downloading = Lock()
		self.__chain_impl('__init__', args, kwargs)
	
	async def open_document(self, view, url):
		if hasattr(view, '_Model__document'):
			raise ValueError("Close previous document first.")
		
		view.__document = None
		view.__referenced = defaultdict(set)
		view.__location = url
		
		event = CustomEvent('opening', target=None, view=view, detail=url)
		result = view.emit('dom_event', event)
		if isawaitable(result):
			result = await result
		if result == False:
			del view.__document, view.__referenced, view.__location
			return None
		
		await self.begin_downloads()
		try:
			view.__document = await self.__load_document(view, url)
		except CancelledError:
			event = CustomEvent('cancelled', target=view.__document, view=view, detail=url)
			view.emit('dom_event', event)
			raise
		finally:
			await self.end_downloads()
		
		event = CustomEvent('open', target=view.__document, view=view, detail=url)
		result = view.emit('dom_event', event)
		if isawaitable(result):
			result = await result
		if result == False:
			del view.__document, view.__referenced, view.__location
			return None
		
		return view.__document
	
	async def close_document(self, view):
		if not (hasattr(view, '_Model__document')):
			raise ValueError("No document is open.")
		
		url = view.__location
		
		event = CustomEvent('closing', target=view.__document, view=view, detail=url)
		result = view.emit('dom_event', event)
		if isawaitable(result):
			result = await result
		if result == False:
			del view.__document, view.__referenced, view.__location
			return
		
		await self.__unload_document(view, url)
		
		event = CustomEvent('close', target=None, view=view, detail=url)
		result = view.emit('dom_event', event)
		if isawaitable(result):
			result = await result
		if result == False:
			del view.__document, view.__referenced, view.__location
			return
		
		del view.__document, view.__referenced, view.__location
		self.documents.clear() # TODO
	
	def current_location(self, view):
		try:
			return view.__location
		except AttributeError:
			return None
	
	def current_document(self, view):
		try:
			return view.__document
		except AttributeError:
			return None
	
	@staticmethod
	def resolve_url(rel_url, base_url):
		"Provided the relative url and the base url, return an absolute url."
		
		if rel_url.startswith('data:'):
			return rel_url
		elif ('/' in rel_url) and (':' in rel_url) and (':' in rel_url.split('/')[0]):
			return rel_url
		elif base_url and base_url[-1] == '/':
			return base_url + rel_url
		elif rel_url[0] == '#' and '#' in base_url:
			return '#'.join(base_url.split('#')[:-1]) + rel_url
		elif rel_url[0] == '#':
			return base_url + rel_url
		elif base_url:
			return '/'.join(base_url.split('/')[:-1]) + '/' + rel_url
		else:
			return rel_url
	
	def __find_impl(self, method_name, args, kwargs={}):
		"Call the first method from any of subclasses, in order of their appearance."
		
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, method_name)
			except AttributeError:
				continue
			
			result = method(self, *args, **kwargs)
			if result != NotImplemented:
				return result
		else:
			raise NotImplementedError(f"Could not find implementation for method {method_name}. Arguments: {args}")
	
	async def __find_impl_async(self, method_name, args, kwargs={}):
		"Call the first async method from any of subclasses, in order of their appearance."
		
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, method_name)
			except AttributeError:
				continue
			
			result = await method(self, *args, **kwargs)
			if result != NotImplemented:
				return result
		else:
			raise NotImplementedError(f"Could not find implementation for method {method_name}. Arguments: {args}")
	
	def __chain_impl(self, method_name, args, kwargs={}):
		"Call all method from all of subclasses, in order of their appearance."
		
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, method_name)
			except AttributeError:
				continue
			
			method(self, *args, **kwargs)
	
	async def __chain_impl_async(self, method_name, args, kwargs={}):
		"Call all async method from all of subclasses, in parallel."
		
		gens = []
		
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, method_name)
			except AttributeError:
				continue
			
			result = method(self, *args, **kwargs)
			gens.append(result)
		
		await gather(*gens)
	
	@staticmethod
	def __url_root(url):
		if url.startswith('data:'):
			return url
		
		u = url.split('#')
		if len(u) > 1:
			return '#'.join(u[:-1])
		else:
			return url
	
	async def __load_document(self, view, url, redirected=False):
		try:
			return self.get_document(url)
		except DocumentNotFound:
			pass
		
		async with self.__start_downloading:
			if url not in self.__downloading:
				me_downloading = True
				self.__downloading[url] = Event()
			else:
				me_downloading = False
		
		try:
			if not me_downloading:
				await self.__downloading[url].wait()
				try:
					return self.get_document(url)
				except DocumentNotFound as error:
					view.emit_warning(view, f"Download not attempted: {type(error).__name__} {str(error)}", url)
					return
			
			if not redirected:
				result = view.emit('dom_event', CustomEvent('download', target=url, view=view))
				if isawaitable(result):
					result = await result
				if result == False:
					self.documents[url] = None
					return
				if result not in [None, True, False]:
					new_url = self.__url_root(result)
					if new_url != url:
						result = view.emit('dom_event', CustomEvent('redirect', target=url, view=view, detail=new_url))
						if isawaitable(result):
							result = await result
						if result != False:
							document = self.documents[url] = await self.__load_document(view, new_url, True)
							return document
			
			try:
				data, mime_type = await self.download_document(url)
			except Exception as error: # Ignore all other errors, issue a warning.
				self.emit_warning(view, f"Error downloading document: {type(error).__name__}: {str(error)}", url)
				data, mime_type = None, 'application/x-null'
			
			#print("download result", data)
			if data is None:
				result = view.emit('dom_event', UIEvent('error', target=None, view=view, detail=url))
				if isawaitable(result):
					result = await result
				if result == False:
					self.documents[url] = None
					return
				if result not in [None, True, False]:
					if isinstance(result, type) and len(result) == 2 and isinstance(result[0], bytes) and isinstance(result[1], str):
						data, mime_type = result
					elif isinstance(result, bytes):
						data = result
						mime_type = 'application/octet-stream'
					else:
						self.emit_warning(view, "Expected (data:bytes, mime:str) tuple or data:bytes blob.", result)
			
			try:
				self.documents[url] = self.create_document(data, mime_type)
			except Exception as error:
				self.emit_warning(view, f"Error creating document: {type(error).__name__}: {str(error)}", url)
				self.documents[url] = self.create_document(None, 'application/x-null')
				result = view.emit('dom_event', CustomEvent('parseerror', target=data, view=view, detail=url))
				if isawaitable(result):
					await result
				return
			
			document = self.get_document(url)
			if document is None:
				return
			
			result = view.emit('dom_event', CustomEvent('beforeload', target=document, view=view, detail=url))
			if isawaitable(result):
				result = await result
			if result == False:
				return
			if result not in [None, True, False]:
				self.documents[url] = document = result
		
		finally:
			async with self.__start_downloading:
				self.__downloading[url].set()
				del self.__downloading[url]
		
		if url.startswith('data:'):
			return document
		
		async with TaskGroup() as group:
			tasks = []
			visited = set()
			for link in self.scan_document_links(document):
				absurl = self.resolve_url(link, self.__url_root(url))
				if absurl in self.documents or absurl in visited:
					continue
				
				view.__referenced[absurl].add(url)
				
				task = group.create_task(self.__load_document(view, absurl))
				if absurl.startswith('data:'):
					await task
				tasks.append(task)
				
				visited.add(absurl)
		
		result = view.emit('dom_event', UIEvent('load', target=document, view=view, detail=url))
		if isawaitable(result):
			result = await result
		if result == False:
			return
		if result not in [None, True, False]:
			self.documents[url] = document = result
		
		return document
	
	async def __unload_document(self, view, url):
		try:
			document = self.get_document(url)
		except DocumentNotFound:
			return
		
		result = view.emit('dom_event', CustomEvent('beforeunload', target=document, view=view, detail=url))
		if isawaitable(result):
			result = await result
		if result == False:
			return
		
		async with TaskGroup() as group:
			tasks = []
			for link in self.scan_document_links(document):
				if link.startswith('data:'):
					continue
				absurl = self.resolve_url(link, url)
				if url in view.__referenced[absurl]:
					view.__referenced[absurl].remove(url)
					if not view.__referenced[absurl]:
						tasks.append(group.create_task(self.__unload_document(view, absurl)))
		
		result = view.emit('dom_event', UIEvent('unload', target=document, view=view, detail=url))
		if isawaitable(result):
			await result
	
	def get_document_url(self, document):
		try:
			return [_url for (_url, _document) in self.documents.items() if _document == document][0] # TODO: raise proper error
		except IndexError:
			raise DocumentNotFound("Could not find url for nonexistent document.")
	
	def get_document_fragment(self, document, href):
		return self.__find_impl('get_document_fragment', [document, href])
	
	def get_base_document(self, url):
		try:
			return self.documents[url]
		except KeyError:
			pass
		
		raise DocumentNotFound(f"No document found for the provided url: `{url}`. Perhaps you forgot to list a download link?")
	
	def get_document(self, url):
		if url.startswith('data:'):
			return self.get_base_document(url)
		
		u = url.split('#')
		if len(u) > 1:
			return self.get_document_fragment(self.get_base_document('#'.join(u[:-1])), u[-1])
		else:
			return self.get_base_document(url)
	
	def are_nodes_ordered(self, ancestor, descendant):
		return self.__find_impl('are_nodes_ordered', [ancestor, descendant])
	
	async def begin_downloads(self):
		await self.__chain_impl_async('begin_downloads', ())
	
	async def end_downloads(self):
		await self.__chain_impl_async('end_downloads', ())
	
	def set_view(self, widget):
		self.__chain_impl('set_view', (widget,))
	
	def handle_event(self, widget, event, name):
		self.__chain_impl('handle_event', (widget, event, name))
	
	def set_image(self, widget, image):
		self.__chain_impl('set_image', (widget, image))
	
	def set_location(self, widget, url):
		self.__chain_impl('set_location', (widget, url))
	
	async def download_document(self, url) -> (bytes, str):
		return await self.__find_impl_async('download_document', [url])
	
	def create_document(self, data:bytes, mime_type:str):
		return self.__find_impl('create_document', [data, mime_type])
	
	def save_document(self, document, fileobj=None):
		return self.__find_impl('save_document', [document, fileobj])
	
	def scan_document_links(self, document):
		return self.__find_impl('scan_document_links', [document])
	
	def image_dimensions(self, view, document):
		"Return image natural width and height, that may depend on viewport size."
		return self.__find_impl('image_dimensions', [view, document])
	
	def image_width_for_height(self, view, document, height):
		"Return image optimal width as calculated for the provided height."
		return self.__find_impl('image_width_for_height', [view, document, height])
	
	def image_height_for_width(self, view, document, width):
		"Return image optimal height as calculated for the provided width."
		return self.__find_impl('image_height_for_width', [view, document, width])
	
	def draw_image(self, view, document, ctx, box):
		return self.__find_impl('draw_image', [view, document, ctx, box])
	
	def poke_image(self, view, document, ctx, box, px, py):
		return self.__find_impl('poke_image', [view, document, ctx, box, px, py])
	
	def element_tabindex(self, document, element):
		return self.__find_impl('element_tabindex', [document, element])
	
	def emit_warning(self, view, message, target):
		if message not in self.emitted_warnings:
			view.emit('dom_event', CustomEvent('warning', view=view, detail=message, target=target))
			self.emitted_warnings.add(message)


if __debug__ and __name__ == '__main__':
	from collections import deque
	
	from asyncio import run, Event
	from aiopath import AsyncPath as Path
	
	from guixmpp.format.plain import PlainFormat
	from guixmpp.format.xml import XMLFormat
	from guixmpp.format.css import CSSFormat
	from guixmpp.format.null import NullFormat
	from guixmpp.format.font import FontFormat
	
	from guixmpp.render.svg import SVGRender
	from guixmpp.render.html import HTMLRender
	from guixmpp.render.png import PNGRender
	from guixmpp.render.pixbuf import PixbufRender
	
	from guixmpp.download.data import DataDownload
	from guixmpp.download.file import FileDownload
	from guixmpp.download.chrome import ChromeDownload
	
	from guixmpp.view.display import DisplayView
	
	print("document")
	
	class Rectangle:
		def __init__(self, x, y, width, height):
			self.x = x
			self.y = y
			self.width = width
			self.height = height
	
	class PseudoView:
		def __init__(self):
			self.__events = deque()
			self.__update = Event()
		
		def emit(self, handler, event):
			print(event)
			if handler == 'dom_event':
				self.__events.append(event)
				self.__update.set()
		
		async def receive(self, type_):
			while True:
				for event in self.__events:
					if event.type_ == type_:
						self.__events.remove(event)
						return event
				await self.__update.wait()
				self.__update.clear()
		
		def clear(self):
			self.__events.clear()
			self.__update.clear()
		
		def get_allocation(self):
			return Rectangle(0, 0, 1000, 700)
		
		def draw_image(self, document):
			pass
		
		def queue_draw(self):
			pass
	
	async def test_main():
		view = PseudoView()
		TestModel = Model.features('TestModel', DisplayView, SVGRender, HTMLRender, CSSFormat, PNGRender, PixbufRender, FontFormat, DataDownload, FileDownload, ChromeDownload, XMLFormat, PlainFormat, NullFormat)
		model = TestModel()
		model.set_view(view)
		async for dirpath in (Path.cwd() / 'examples').iterdir():
			async for filepath in dirpath.iterdir():
				#if filepath.name != 'litehtml.css': continue
				print()
				print(filepath)
				document = await model.open_document(view, filepath.as_uri())
				await view.receive('open')
				try:
					dimensions = model.image_dimensions(view, document)
				except NotImplementedError:
					pass
				await model.close_document(view)
				view.clear()
	
	run(test_main())

