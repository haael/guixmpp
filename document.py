#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DocumentModel',


from collections import defaultdict
from asyncio import gather, create_task

from domevents import UIEvent, CustomEvent


class URLNotFound(Exception):
	pass


class Model:
	"A structure holding a collection of documents, capable of loading and unloading."
	
	@staticmethod
	def features(name, *classes):
		return type(name, (Model,) + classes, {})
	
	def __init__(self):
		self.documents = {}
		self.emitted_warnings = set()
	
	async def open_document(self, view, url):
		#print("open document", url)
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
		#print("close document")
		if not (hasattr(view, '_Model__document') and view.__document is not None):
			raise ValueError("No document is open.")
		
		url = view.__location
		view.emit('dom_event', CustomEvent('closing', target=view.__document, view=view, detail=url))
		self.__unload_document(view, url)
		view.emit('dom_event', CustomEvent('close', target=None, view=view, detail=url))
		view.__location = None
		view.__document = None
	
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
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, method_name)
			except AttributeError:
				continue
			
			method(self, *args, **kwargs)
	
	async def __chain_impl_async(self, method_name, args, kwargs={}):
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
		except URLNotFound:
			pass
		
		u = url.split('#')
		if len(u) > 1:
			shurl = '#'.join(url.split('#')[:-1])
		else:
			shurl = url
		data, mime_type = await self.download_document(shurl)
		self.documents[shurl] = self.create_document(data, mime_type)
		document = self.get_document(url)
		
		view.emit('dom_event', CustomEvent('beforeload', target=document, view=view, detail=url))
		loads = []
		for link in self.scan_document_links(document):
			if link.startswith('data:'):
				self.documents[link] = self.create_document(*(await self.download_document(link)))
				continue
			absurl = self.resolve_url(link, url)
			view.__referenced[absurl].add(url)
			load = create_task(self.__load_document(view, absurl))
			loads.append(load)
		await gather(*loads)
		view.emit('dom_event', UIEvent('load', target=document, view=view, detail=url))
		return document
	
	def __unload_document(self, view, url):
		document = self.get_document(url)
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
		
		raise URLNotFound(f"No document found for the provided url: {url}")
	
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
	
	def emit_warning(self, view, message, url, node):
		if message not in self.emitted_warnings:
			view.emit('dom_event', CustomEvent('warning', target=node, detail=message))
			self.emitted_warnings.add(message)


if __debug__ and __name__ == '__main__':
	from asyncio import run
	from aiopath import AsyncPath as Path
	
	from format.plain import PlainFormat
	from format.xml import XMLFormat
	from format.css import CSSFormat
	from format.null import NullFormat
	
	from font.woff import WOFFFont
	
	from image.svg import SVGImage
	from image.png import PNGImage
	from image.pixbuf import PixbufImage
	
	from download.data import DataDownload
	from download.file import FileDownload
	from download.chrome import ChromeDownload
	
	class PseudoView:
		def emit(self, handler, event):
			#print(handler)
			pass
		
		def get_viewport_width(self, widget):
			return 2500
		
		def get_viewport_height(self, widget):
			return 1000
		
		def get_dpi(self, widget):
			return 96
	
	async def test_main():
		view = PseudoView()
		TestModel = Model.features('TestModel', SVGImage, CSSFormat, PNGImage, PixbufImage, WOFFFont, DataDownload, FileDownload, ChromeDownload, XMLFormat, PlainFormat, NullFormat)
		model = TestModel()
		async for filepath in (Path.cwd() / 'gfx').iterdir():
			#if filepath.suffix in ['.css']: continue
			#print(filepath.as_uri())
			document = await model.open_document(view, filepath.as_uri())
			#print(" type:", type(document))
			try:
				dimensions = model.image_dimensions(view, document)
				#print(" dimensions:", dimensions)
			except NotImplementedError:
				pass
			model.close_document(view)
	
	run(test_main())

