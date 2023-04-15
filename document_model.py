#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DocumentModel',


from dom_events import UIEvent


class Model:
	@staticmethod
	def features(name, *classes):
		return type(name, (Model,) + classes, {})
	
	def open_document(self, url):
		self.document = self.load_document(url)
		self.send_document_event('load', UIEvent('load', target=self.document))
	
	def close_document(self):
		self.send_document_event('unload', UIEvent('unload', target=self.document))
		del self.document
	
	@staticmethod
	def resolve_url(rel_url, base_url):
		"Provided the relative url and the base url, return an absolute url."
		
		if any(rel_url.startswith(_proto) for _proto in ['file:', 'http:', 'https:', 'file:']):
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
			raise NotImplementedError(f"Could not find implementation for method {method_name}. Arguments: {args} {kwargs}")
	
	def send_document_event(self, handler, event):
		print(handler, event)
	
	def load_document(self, url):
		data, mime_type = self.download_document(url)
		
		document = self.create_document(data, mime_type)
		
		subdocuments = {}
		for link in self.scan_document_links(document):
			subdocuments[link] = self.load_document(self.resolve_url(link, url))
		document = self.transform_document(document, subdocuments)
		
		return document
	
	def download_document(self, url) -> bytes:
		"download"
		return self.__find_impl('download_document', [url])
	
	def create_document(self, data:bytes, mime_type:str):
		"model/format"
		return self.__find_impl('create_document', [data, mime_type])
	
	def save_document(self, document, fileobj=None):
		"model/format"
		return self.__find_impl('save_document', [document, fileobj])
	
	def scan_document_links(self, document):
		"format"
		return self.__find_impl('scan_document_links', [document])
	
	def transform_document(self, document, subdocuments):
		"format"
		return self.__find_impl('transform_document', [document, subdocuments])
	
	def document_width(self, document, vw, vh):
		"render"
		return self.__find_impl('document_width', [document, vw, vh])
	
	def document_height(self, document, vw, vh):
		"render"
		return self.__find_impl('document_height', [document, vw, vh])
	
	def draw_document(self, document, ctx, box, vw, vh):
		"render"
		return self.__find_impl('draw_document', [document, ctx, box, vw, vh])


if __debug__ and __name__ == '__main__':
	import gi
	gi.require_version('Gdk', '3.0')
	gi.require_version('GdkPixbuf', '2.0')
	
	from mimetypes import init as init_mimetypes
	init_mimetypes()
	
	from pathlib import Path
	
	from model.plain import PlainModel
	from model.xml import XMLModel
	from model.image import ImageModel
	from model.css import CSSModel
	
	from format.svg import SVGFormat
	from format.png import PNGFormat
	from format.image import ImageFormat
	
	from download.inline import InlineDownload
	from download.file import FileDownload
	#from download.http import HTTPDownload
	#from download.file import XMPPDownload
	
	from render.image import ImageRender
	from render.svg import SVGRender
	
	TestModel = Model.features('TestModel', SVGFormat, CSSFormat, PNGFormat, ImageFormat, InlineDownload, FileDownload, ImageRender, SVGRender, XMLModel, PlainModel, ImageModel, CSSModel)
	model = TestModel()
	for filepath in Path('gfx').iterdir():
		#if filepath.suffix in ['.css']: continue
		print(filepath)
		document = model.load_document('file:' + str(filepath))
		print("   ", type(document))
		try:
			print("   ", model.document_width(document, 300, 200), model.document_height(document, 300, 200))
		except NotImplementedError:
			pass


