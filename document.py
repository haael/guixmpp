#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DocumentModel',


from collections import defaultdict
from asyncio import gather, create_task, wait, FIRST_EXCEPTION, Lock, Event

from domevents import UIEvent, CustomEvent
from download.utils import DownloadError


class DocumentNotFound(Exception):
	pass


#class CreationError(Exception):
#	pass


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
		if hasattr(view, '_Model__document') and view.__document is not None:
			raise ValueError("Close previous document first.")
		
		view.__referenced = defaultdict(set)
		view.__location = url
		view.emit('dom_event', CustomEvent('opening', target=None, view=view, detail=url))
		await self.begin_downloads()
		view.__document = await self.__load_document(view, url)
		await self.end_downloads()
		view.emit('dom_event', CustomEvent('open', target=view.__document, view=view, detail=url))
		return view.__document
	
	def close_document(self, view):
		if not (hasattr(view, '_Model__document') and view.__document is not None):
			raise ValueError("No document is open.")
		
		url = view.__location
		view.emit('dom_event', CustomEvent('closing', target=view.__document, view=view, detail=url))
		self.__unload_document(view, url)
		view.emit('dom_event', CustomEvent('close', target=None, view=view, detail=url))
		view.__location = None
		view.__document = None
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
		
		if ('/' in rel_url) and (':' in rel_url) and (':' in rel_url.split('/')[0]):
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
	
	async def __load_document(self, view, url):
		try:
			return self.get_document(url)
		except DocumentNotFound:
			pass
		
		u = url.split('#')
		if len(u) > 1:
			shurl = '#'.join(url.split('#')[:-1])
		else:
			shurl = url
		
		async with self.__start_downloading:
			if shurl not in self.__downloading:
				#print("me downloading", shurl)
				me_downloading = True
				self.__downloading[shurl] = Event()
			else:
				#print("other downloading", shurl)
				me_downloading = False
		
		if not me_downloading:
			#print("wait for download", shurl)
			await self.__downloading[shurl].wait()
			#print("finished waiting for download", shurl)
			
			try:
				return self.get_document(url)
			except DocumentNotFound:
				pass
			
			self.emit_warning(view, "Document download not attempted.", url)
			
			return None
		
		else:
			try:
				try:
					data, mime_type = await self.download_document(shurl)
				except Exception as error:
					self.emit_warning(view, f"Error downloading document: {str(error)}", url)
					data, mime_type = None, 'application/x-null'
				
				try:
					self.documents[shurl] = self.create_document(data, mime_type)
				except Exception as error:
					self.emit_warning(view, f"Error creating document: {str(error)}", url)
					self.documents[shurl] = self.create_document(None, 'application/x-null')
			
			finally:
				async with self.__start_downloading:
					#print("finished downloading", shurl)
					self.__downloading[shurl].set()
					del self.__downloading[shurl]
		
		document = self.get_document(url)
		if document is None:
			view.emit('dom_event', UIEvent('error', target=document, view=view, detail=url))
			return document
		
		view.emit('dom_event', CustomEvent('beforeload', target=document, view=view, detail=url))
		loads = []
		visited = set()
		for link in self.scan_document_links(document):
			if link in self.documents or link in visited:
				continue
			
			if link.startswith('data:'):
				try:
					self.documents[link] = self.create_document(*(await self.download_document(link))) # TODO: possible exception
				except Exception as error:
					self.emit_warning(view, f"Error creating document: {str(error)}", link)
					self.documents[link] = self.create_document(None, 'application/x-null')
			else:
				absurl = self.resolve_url(link, url)
				view.__referenced[absurl].add(url)
				load = create_task(self.__load_document(view, absurl))
				loads.append(load)
			visited.add(link)
		
		if loads:
			done, pending = await wait(loads)
			errors = []
			for t in done:
				if t.exception() is not None:
					errors.append(t.exception())
			if errors:
				raise ExceptionGroup("Errors in __load_document subtasks.", errors) # should not happen
		
		view.emit('dom_event', UIEvent('load', target=document, view=view, detail=url))
		return document
	
	def __unload_document(self, view, url):
		try:
			document = self.get_document(url)
		except DocumentNotFound:
			return
		
		view.emit('dom_event', CustomEvent('beforeunload', target=document, view=view, detail=url))
		for link in self.scan_document_links(document):
			if link.startswith('data:'):
				#del self.documents[link]
				continue
			absurl = self.resolve_url(link, url)
			if url in view.__referenced[absurl]:
				view.__referenced[absurl].remove(url)
				if not view.__referenced[absurl]:
					self.__unload_document(view, absurl)
		view.emit('dom_event', UIEvent('unload', target=document, view=view, detail=url))
	
	def get_document_url(self, document):
		return [_url for (_url, _document) in self.documents.items() if _document == document][0] # TODO: raise proper error
	
	def get_document_fragment(self, document, href):
		return self.__find_impl('get_document_fragment', [document, href])
	
	def get_base_document(self, url):
		try:
			return self.documents[url]
		except KeyError:
			pass
		
		raise DocumentNotFound(f"No document found for the provided url: {url}")
	
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
	
	async def download_document(self, url) -> (bytes, str):
		return await self.__find_impl_async('download_document', [url])
	
	def create_document(self, data:bytes, mime_type:str):
		return self.__find_impl('create_document', [data, mime_type])
	
	def save_document(self, document, fileobj=None):
		return self.__find_impl('save_document', [document, fileobj])
	
	def scan_document_links(self, document):
		return self.__find_impl('scan_document_links', [document])
	
	def image_dimensions(self, view, document):
		return self.__find_impl('image_dimensions', [view, document])
	
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
	
	from format.plain import PlainFormat
	from format.xml import XMLFormat
	from format.css import CSSFormat
	from format.null import NullFormat
	from format.font import FontFormat
	
	from image.svg import SVGImage
	from image.png import PNGImage
	from image.pixbuf import PixbufImage
	
	from download.data import DataDownload
	from download.file import FileDownload
	from download.chrome import ChromeDownload
	
	from view.display import DisplayView
	
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
		TestModel = Model.features('TestModel', DisplayView, SVGImage, CSSFormat, PNGImage, PixbufImage, FontFormat, DataDownload, FileDownload, ChromeDownload, XMLFormat, PlainFormat, NullFormat)
		model = TestModel()
		model.set_view(view)
		async for filepath in (Path.cwd() / 'examples/gfx').iterdir():
			document = await model.open_document(view, filepath.as_uri())
			await view.receive('open')
			try:
				dimensions = model.image_dimensions(view, document)
			except NotImplementedError:
				pass
			model.close_document(view)
			view.clear()
	
	run(test_main())

