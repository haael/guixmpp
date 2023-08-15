#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DocumentModel',


from collections import defaultdict
from asyncio import gather

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
	
	async def open_document(self, view, url):
		#print("open document", url)
		if hasattr(view, '_Model__document') and view.__document is not None:
			raise ValueError("Close previous document first.")
		
		view.__referenced = defaultdict(set)
		view.__location = url
		view.emit_dom_event('content_changed', CustomEvent('opening', target=None, view=view, detail=url))
		await self.begin_downloads()
		view.__document = await self.__load_document(view, url)
		await self.end_downloads()
		view.emit_dom_event('content_changed', CustomEvent('open', target=view.__document, view=view, detail=url))
		return view.__document
	
	def close_document(self, view):
		#print("close document")
		if not (hasattr(view, '_Model__document') and view.__document is not None):
			raise ValueError("No document is open.")
		
		url = view.__location
		view.emit_dom_event('content_changed', CustomEvent('closing', target=view.__document, view=view, detail=url))
		self.__unload_document(view, url)
		view.emit_dom_event('content_changed', CustomEvent('close', target=None, view=view, detail=url))
		view.__location = None
		view.__document = None
	
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
		
		view.emit_dom_event('content_changed', CustomEvent('beforeload', target=document, view=view, detail=url))
		loads = []
		for link in self.scan_document_links(document):
			if link.startswith('data:'):
				self.documents[link] = self.create_document(*(await self.download_document(link)))
				continue
			absurl = self.resolve_url(link, url)
			view.__referenced[absurl].add(url)
			load = self.__load_document(view, absurl)
			loads.append(load)
		await gather(*loads)
		view.emit_dom_event('content_changed', UIEvent('load', target=document, view=view, detail=url))
		return document
	
	def __unload_document(self, view, url):
		document = self.get_document(url)
		view.emit_dom_event('content_changed', CustomEvent('beforeunload', target=document, view=view, detail=url))
		for link in self.scan_document_links(document):
			if link.startswith('data:'):
				#del self.documents[link]
				continue
			absurl = self.resolve_url(link, url)
			if url in view.__referenced[absurl]:
				view.__referenced[absurl].remove(url)
				if not view.__referenced[absurl]:
					self.__unload_document(view, absurl)
		view.emit_dom_event('content_changed', UIEvent('unload', target=document, view=view, detail=url))
	
	def get_document_url(self, document):
		return [_url for (_url, _document) in self.documents.items() if _document is document][0] # TODO: error
	
	def get_document_fragment(self, document, href):
		return self.__find_impl('get_document_fragment', [document, href])
	
	def get_base_document(self, url):
		try:
			return self.documents[url]
		except KeyError:
			pass
		
		#if url.startswith('data:'):
		#	#print("create document from data url", url)
		#	self.documents[url] = self.create_document(*self.download_document(url))
		#	return self.documents[url]
		
		raise URLNotFound(f"No document found for the provided url: {url}")
	
	def get_document(self, url):
		if url.startswith('data:'):
			return self.get_base_document(url)
		
		u = url.split('#')
		if len(u) > 1:
			return self.get_document_fragment(self.get_base_document('#'.join(u[:-1])), u[-1])
		else:
			return self.get_base_document(url)
	
	async def begin_downloads(self):
		gens = []
		
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, 'begin_downloads')
			except AttributeError:
				continue
			
			gens.append(method(self))
		
		await gather(*gens)
	
	async def end_downloads(self):
		gens = []
		
		for cls in self.__class__.mro():
			if issubclass(cls, Model):
				continue
			
			try:
				method = getattr(cls, 'end_downloads')
			except AttributeError:
				continue
			
			gens.append(method(self,))
		
		await gather(*gens)
	
	async def download_document(self, url) -> (bytes, str):
		"download"
		return await self.__find_impl_async('download_document', [url])
	
	def create_document(self, data:bytes, mime_type:str):
		"model/format"
		return self.__find_impl('create_document', [data, mime_type])
	
	def save_document(self, document, fileobj=None):
		"model/format"
		return self.__find_impl('save_document', [document, fileobj])
	
	def scan_document_links(self, document):
		"format"
		return self.__find_impl('scan_document_links', [document])
	
	def image_dimensions(self, view, document):
		"render"
		return self.__find_impl('image_dimensions', [view, document])
	
	def draw_image(self, view, document, ctx, box):
		"render"
		return self.__find_impl('draw_image', [view, document, ctx, box])
	
	def element_tabindex(self, document, element):
		return self.__find_impl('element_tabindex', [document, element])
	
	def emit_warning(self, view, message, url, node):
		view.emit_dom_event('warning', CustomEvent('warning', target=node, detail=message))


if __debug__ and __name__ == '__main__':
	import gi
	gi.require_version('Gdk', '3.0')
	gi.require_version('GdkPixbuf', '2.0')
		
	from asyncio import run
	from aiopath import AsyncPath as Path
	
	from format.plain import PlainFormat
	from format.xml import XMLFormat
	from format.css import CSSFormat
	from format.svg import SVGFormat
	from format.png import PNGFormat
	from format.image import ImageFormat
	from format.null import NullFormat
	
	from download.data import DataDownload
	from download.file import FileDownload
	from download.chrome import ChromeDownload
	
	class PseudoView:
		def __init__(self):
			self.pointer = 10, 10
			self.widget_width = 2000
			self.widget_height = 1500
			self.screen_dpi = 96
	
		def emit_dom_event(self, handler, event):
			#print(handler)
			pass
	
	async def test_main():
		view = PseudoView()
		TestModel = Model.features('TestModel', SVGFormat, CSSFormat, PNGFormat, ImageFormat, DataDownload, FileDownload, ChromeDownload, XMLFormat, PlainFormat, NullFormat)
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

