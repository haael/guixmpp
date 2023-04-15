#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'SVGRender',


import cairo
from math import ceil


class SVGRender:
	"Supports creating and rendering SVG images, also supports CSS."
	
	dpi = 96 # FIXME
	
	def document_width(self, document, viewport_width, viewport_height):
		if self.is_svg_document(document):
			try:
				w = document.getroot().attrib['width']
			except KeyError:
				return viewport_width
			
			try:
				return float(w)
			except ValueError:
				if w[-1] == '%':
					return float(w[:-1]) * viewport_width / 100
				elif w[-2:] == 'px':
					return int(w[:-2])
				elif w[-2:] == 'mm':
					return float(w[:-2]) * self.dpi * 2.41 # FIXME
				else:
					raise
		else:
			return NotImplemented
	
	def document_height(self, document, viewport_width, viewport_height):
		if self.is_svg_document(document):
			try:
				h = document.getroot().attrib['height']
			except KeyError:
				return viewport_height
			
			try:
				return float(h)
			except ValueError:
				if h[-1] == '%':
					return float(h[:-1]) * viewport_height / 100
				elif h[-2:] == 'px':
					return int(h[:-2])
				elif h[-2:] == 'mm':
					return float(h[:-2]) * self.dpi * 2.41 # FIXME
				else:
					raise
		else:
			return NotImplemented


'''



class DataEvent:
	def __init__(self, data, mime_type):
		self.data = data
		self.mime_type = mime_type


class DocumentEvent:
	def __init__(self, document):
		self.document = document



class DocumentModel:
	"Document model. Can fetch only 'data:' links and supports only text and raw data. No rendering functions."
	
	def open(self, url):
		self.document = self.load(url)
		self.update()
	
	def close(self):
		del self.document
		self.update()
	
	def __find_impl(self, method_name, *args, **kwargs):
		for cls in self.__class__.mro():
			if cls == self.__class__:
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
	
	def document_width(self, document, viewport_width):
		return self.__find_impl('document_width', [document, viewport_width])
	
	def document_height(self, document, viewport_height):
		return self.__find_impl('document_height', [document, viewport_height])
	
	def send_event(self, handler, event):
		raise NotImplementedError
	
	def load(self, url):
		data, mime_type = self.download(url)
		self.send_event('download', DataEvent(data, mime_type))
		
		initial_document = self.create(data, mime_type)
		self.send_event('create', DocumentEvent(initial_document))
		
		subdocument = {}
		for link in self.scan_links(initial_document):
			subdocument[link] = self.load(link)
		final_document = self.transform(initial_document, subdocument)
		
		self.send_event('load', DocumentEvent(final_document))
		return final_document
	
	def download(self, url) -> bytes:
		if url.startswith('data:')
			headers = url[url.index(':') + 1 : url.index(',')].split(';')
			
			try:
				mime_type = headers[0]
			except KeyError:
				mime_type = 'text/plain'
			
			try:
				encoding = headers[1]
			except KeyError:
				encoding = ''
			
			raw_data = url[url.index(',') + 1 :]
			if encoding == 'base64':
				from base64 import b64decode
				data = b64decode(raw_data)
			elif encoding == '':
				from urllib.parse import unquote
				data = unquote(raw_data).encode('utf-8')
			
			return data, mime_type
		
		else:
			return self.__find_impl('download', [url])
	
	def create(self, data:bytes, mime_type):
		if mime_type == 'text/plain':
			return data.decode('utf-8')
		
		elif mime_type == 'application/octet-stream':
			return data
		
		else:
			return self.__find_impl('create', [data, mime_type])
	
	def scan_links(self, document):
		if isinstance(document, (str, bytes)):
			return []
		else:
			return self.__find_impl('scan_links', [document])
	
	def transform(self, initial_document, subdocument):
		if isinstance(document, (str, bytes)):
			return initial_document
		else:
			return self.__find_impl('transform', [initial_document, subdocument])
	
	def draw(self, document, ctx, box, vw, vh):
		return self.__find_impl('draw', [document, ctx, box, vw, vh])






from defusedxml.ElementTree import ElementTree, XMLParser
from tinycss2 import parse_stylesheet_bytes, parse_declaration_list


class Parser(XMLParser): # overcome the limitation of XMLParser that doesn't parse processing instructions
	def feed(self, data):
		try:
			start = data.index(b'<?xml-stylesheet')
			stop = data.index(b'?>', start) + 2
			stylesheet_instruction = data[start:stop]
			
			start = stylesheet_instruction.find(b'href')
			start = stylesheet_instruction.find(b'=', start)
			try:
				start = stylesheet_instruction.index(b'"', start) + 1
				stop = stylesheet_instruction.index(b'"', start)
			except ValueError:
				start = stylesheet_instruction.index(b'\'', start) + 1
				stop = stylesheet_instruction.index(b'\'', start)
			
			self.stylesheet = stylesheet_instruction[start:stop].decode('utf-8')
		except ValueError:
			self.stylesheet = None
		
		return super().feed(data)


class XMLModel:
	"XML model. Can create XML document."
	
	xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	xmlns_xlink = 'http://www.w3.org/1999/xlink'
	
	def create(self, data:bytes, mime_type):
		if mime_type == 'application/xml' or mime_type == 'text/xml':
			parser = Parser()
			document = ElementTree()
			document.XML(data, parser)
			document.stylesheet = parser.stylesheet
			return document

		elif mime_type == 'application/xslt+xml':
			document = self.create(data, 'application/xml')
			if document.getroot().tag == f'{{{self.xmlns_xslt}}}stylesheet':
				return document
			else:
				raise ValueError("Not an XSLT document.")
		
		elif mime_type == 'text/css':
			return parse_stylesheet_bytes(data, skip_comments=True, skip_whitespace=True)
		
		else:
			return NotImplemented
	
	def traverse_xml(self, node, param, pre_function, post_function):
		if pre_function != None:
			node, param = pre_function(node, param)
		
		children = []
		for child in node:
			child = self.traverse_xml(child, param, pre_function, post_function)
		children.append(child)
		
		if post_function != None:
			node = post_function(node, children)
		return node
	
	def parse_css_style_tags(self, document, tagnames=frozenset(['style'])):
		def pre_function(node, param):
			for tagname in tagnames:
				try:
					style = parse_declaration_list(node.attrib[tagname], skip_comments=True, skip_whitespace=True)
				except KeyError:
					pass
				
				if not hasattr(node, 'style'):
					node.style = dict()
				node.style.update(style)
			return node, param
		
		return self.traverse_xml(document.getroot(), None, pre_function, None)
	
	def parse_css_stylesheet(self, document, stylesheet):
		def pre_function(node, ancestors):
			ancestors = ancestors + [node]
			for selector, declaration_list in stylesheet:
				if self.css_selector_match(selector, ancestors):
					if not hasattr(node, 'style'):
						node.style = dict()
					node.style.update(declaration_list)
			return node, ancestors
		
		return self.traverse_xml(document.getroot(), [], pre_function, None)
	
	def transform(self, document, subdocuments):
		if isinstance(document, ElementTree):
			for url, subdocument in subdocuments.values():
				if isinstance(subdocument, tuple[])
			document = self.parse_css_stylesheet(document, )








from io import BytesIO
import cairo


class ImageRender:
	"Supports creating and rendering PNG images."
	
	def create(self, data, mime_type):
		if mime_type == 'image/png':
			return cairo.ImageSurface.create_from_png(BytesIO(data))
		else:
			return NotImplemented

	def document_width(self, document, viewport_width):
		if isinstance(document, cairo.ImageSurface):
			return document.get_width()
		else:
			return NotImplemented
	
	def document_height(self, document, viewport_height):
		if isinstance(document, cairo.ImageSurface):
			return document.get_height()
		else:
			return NotImplemented
	
	def draw(self, document, ctx, box, vw, wh):
		if isinstance(document, cairo.ImageSurface):
			ctx.set_source_surface(document)
			ctx.scale(box[2] / self.document_width(document, vw), box[3] / self.document_height(document, vh))
			ctx.rectangle(*box)
			ctx.fill()
		else:
			return NotImplemented





class SVGRender:
	"Supports creating and rendering SVG images, also supports CSS."
	
	xmlns_svg = 'http://www.w3.org/2000/svg'
	xmlns_sodipodi = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
	xmlns_inkscape = 'http://www.inkscape.org/namespaces/inkscape'
	
	def document_width(self, document, viewport_width):
		if isinstance(document, ElementTree) and document.getroot().tag == f'{{{self.xmlns_svg}}}svg':
			return int(document.getroot().attrib['width'])
		else:
			return NotImplemented
	
	def document_height(self, document, viewport_height):
		if isinstance(document, ElementTree) and document.getroot().tag == f'{{{self.xmlns_svg}}}svg':
			return int(document.getroot().attrib['height'])
		else:
			return NotImplemented
	
	def create(self, data, mime_type):
		if mime_type == 'image/svg+xml' or mime_type == 'image/svg':
			document = self.create(data, 'application/xml')
			if document.getroot().tag == f'{{{self.xmlns_svg}}}svg':
				return document
			else:
				raise ValueError("Not an SVG document.")
		else:
			return NotImplemented


class SMIL:
	pass


class XForms:
	pass


class FileLoader:
	pass


class HTTPLoader:
	pass


class XMPPLoader:
	pass






class XMLModel:
	def __init__(self):
		self.main_url = None
		self.__pending = set()
		self.__docs = {}
		self.__errs = {}
		self.__last_urls = frozenset()
		self.__transformed_docs = {}
	
	def clear(self):
		"Reset the object to the default state. Should be called during cleanup."
		for img in self.__transformed_docs.values():
			try:
				img.finish()
			except AttributeError:
				pass
		self.main_url = None
		self.__pending = set()
		self.__docs = {}
		self.__errs = {}
		self.__last_urls = frozenset()
		self.__transformed_docs = {}
		self.update()
	
	def open(self, url, base_url=''):
		"Open an XML document by `url`, performing all necessary initialization. `url` is an absolute or relative url, in the latter case resolved relative to `base_url`."
		
		self.main_url = self.resolve_url(url, base_url)
		try:
			self.get_doc(self.main_url)
		except KeyError:
			self.request_url(self.main_url)
		else:
			self.update()
	
	@staticmethod
	def resolve_url(rel_url, base_url):
		"Provided the relative url and the base url, return an absolute url."
		
		if rel_url.startswith('file:'):
			rel_url = rel_url[5:]
		elif rel_url.startswith('data:'):
			return rel_url
		
		if base_url and base_url[-1] == '/':
			return base_url + rel_url
		elif rel_url[0] == '#' and '#' in base_url:
			return '#'.join(base_url.split('#')[:-1]) + rel_url
		elif rel_url[0] == '#':
			return base_url + rel_url
		elif base_url:
			return '/'.join(base_url.split('/')[:-1]) + '/' + rel_url
		else:
			return rel_url
	
	def enter_pending(self, url):
		"If the url is not in 'pending' state, mark it as pending and return False. If it is in pending state, or has been already downloaded, return True."
		if (url in self.__docs) or (url in self.__errs):
			return True
		
		if url in self.__pending:
			return True
		self.__pending.add(url)
		return False
	
	def request_url(self, url):
		"""
		Called when a resource needs to be downloaded. `url` is always absolute. The implementation should call one of `register_*` methods, possibly asynchronously.
		To avoid requesting the same resource multiple times, call `self.enter_pending(url)` at the start and exit the function if it returns True.
		"""
		
		if self.enter_pending(url): return
		
		exceptions = []
		
		try:
			from defusedxml.ElementTree import ElementTree, XMLParser
			
			class Parser(XMLParser): # overcome the limitation of XMLParser that doesn't parse processing instructions
				def feed(self, data):
					try:
						start = data.index(b'<?xml-stylesheet')
						stop = data.index(b'?>', start) + 2
						stylesheet_instruction = data[start:stop]
						
						start = stylesheet_instruction.find(b'href')
						start = stylesheet_instruction.find(b'=', start)
						try:
							start = stylesheet_instruction.index(b'"', start) + 1
							stop = stylesheet_instruction.index(b'"', start)
						except ValueError:
							start = stylesheet_instruction.index(b'\'', start) + 1
							stop = stylesheet_instruction.index(b'\'', start)
						
						self.stylesheet = stylesheet_instruction[start:stop].decode('utf-8')
					except ValueError:
						self.stylesheet = None
					
					return super().feed(data)	
			
			parser = Parser()
			document = ElementTree()
			document.parse(url, parser)
			document.stylesheet = parser.stylesheet # TODO: more than 1 stylesheet
		
		except Exception as error:
			exceptions.append(error)
		else:
			self.register_doc(url, document)
			return
		
		if url.startswith('data:image/png;base64,'):
			try:
				from base64 import b64decode
				from png import Reader
				
				png_data = b64decode(url[22:])
				image = Reader(bytes=png_data)
				width, height, rows, info = image.asRGBA()
				pixel_data = bytearray([0]) * width * height * 4
				
				for y, row in enumerate(rows):
					for x in range(len(row) // 4):
						# little endian byte order assumed
						# TODO: endianess detection, big endian
						alpha = row[4 * x + 3] / 255
						pixel_data[4 * (width * y + x) + 0] = int(alpha * row[4 * x + 2]) # blue
						pixel_data[4 * (width * y + x) + 1] = int(alpha * row[4 * x + 1]) # green
						pixel_data[4 * (width * y + x) + 2] = int(alpha * row[4 * x + 0]) # red
						pixel_data[4 * (width * y + x) + 3] = row[4 * x + 3] # alpha
				
			except Exception as error:
				exceptions.append(error)
			else:
				inline_img = Record()
				inline_img.format = cairo.Format.ARGB32
				inline_img.width = width
				inline_img.height = height
				inline_img.pixel_data = pixel_data
				self.register_doc(url, inline_img)
				return
		
		try:
			from pathlib import Path
			
			document = Path(url).read_bytes()
		except Exception as error:
			exceptions.append(error)
		else:
			self.register_doc(url, document)
			return
		
		self.register_err(url, exceptions)
		self.error(f"Could not open url: {url}", (url, exceptions), None)
	
	def register_doc(self, url, doc):
		"Register document under the provided url."
		
		self.__pending.remove(url)
		
		if url in self.__docs:
			raise ValueError("Doc already registered")
		self.__docs[url] = doc
		
		try:
			self.get_doc(self.main_url)
		except KeyError:
			pass
		else:
			self.update()
	
	def register_err(self, url, error):
		"Register an error, indicating that the resource is unavailable. The error object may be anything."
		self.__pending.remove(url)
		self.__errs[url] = error
	
	def get_doc(self, url):
		try:
			error = self.__errs[url]
		except KeyError:
			pass
		else:
			raise KeyError("Document resource not available:", error)
		
		return self.__docs[url] # TODO: transform
	
	def get_transformed_doc(self, url):
		src_doc = self.get_doc(url)
		
		all_urls = frozenset(self.all_urls())
		
		if all_urls != self.__last_urls:
			self.__last_urls = all_urls
			self.__transformed_docs.clear()
		
		try:
			return self.__transformed_docs[url]
		except KeyError:
			pass
		
		dst_doc = self.transform_document(url, src_doc)
		self.__transformed_docs[url] = dst_doc
		return dst_doc
	
	def get_err(self, error):
		return self.__errs[url]
	
	def del_doc(self, url):
		try:
			self.__pending.remove(url)
		except ValueError:
			pass
		del self.__docs[url]
	
	def del_err(self, url):
		try:
			self.__pending.remove(url)
		except ValueError:
			pass
		del self.__errs[url]
	
	def all_urls(self):
		return self.__docs.keys()
	
	def update(self):
		"Called when the document structure changed in a way that a redraw is needed. Trigger a drawing operation from here."
		pass
	
	def error(self, message, param, node):
		"Called when the renderer encounters an non-fatal error. Safe to ignore."
		import sys
		print("SVG error in", self.main_url, ":", file=sys.stderr)
		print("    ", message, file=sys.stderr)
		print("    ", param, file=sys.stderr)
		if node:
			print("    ", node.tag, node.attrib, file=sys.stderr)
	
	def transform_document(self, url, src_doc):
		"Performs all transformations on the document, like XInclude. For image documents, returns a Cairo surface."
		
		dst_doc = src_doc
		errors = []
		
		try:
			root = src_doc.getroot()
		except AttributeError as error:
			errors.append(error)
		else:
			self.scan_links(url, root)
			return dst_doc
		
		try:
			width = src_doc.width
			height = src_doc.height
			pixel_data = src_doc.pixel_data
			format_ = src_doc.format
		except AttributeError as error:
			errors.append(error)
		else:
			dst_doc = cairo.ImageSurface.create_for_data(pixel_data, format_, width, height)
			return dst_doc
		
		if isinstance(src_doc, bytes) or isinstance(src_doc, bytearray):
			try:
				dst_doc = cairo.ImageSurface.create_from_png(BytesIO(src_doc))
			except (TypeError, MemoryError) as error:
				errors.append(error)
			else:
				return dst_doc
		
		self.error("no transformation found for the document", errors, None)
		
		return dst_doc
	
	def scan_link(self, base_url, node):
		"Override this method and call `self.request_url(self.resolve_url(link, base_url))` if the node contains a link."
		pass
		#try:
		#	self.__defs[base_url + '#' + node.attrib['id'].strip()] = node
		#except KeyError:
		#	pass
	
	def scan_links(self, base_url, node):
		self.scan_link(base_url, node)
		for child in node:
			self.scan_links(base_url, child)
	
	def render(self, ctx, box, pointer=None):
		if self.main_url != None:
			return self.render_url(ctx, box, self.main_url, 0, True, pointer)
		else:
			return []
	
	def hover(self, ctx, box, pointer):
		if self.main_url != None:
			return self.render_url(ctx, box, self.main_url, 0, False, pointer)
		else:
			return []
	
	def render_xml(self, ctx, box, node, ancestors, url, level, draw, pointer):
		self.error(f"unsupported XML tag to render: {node.tag}", node.tag, node)
		return []
	
	def render_text(self, ctx, box, text):
		x, y, w, h = box
		ctx.set_font_size(12)
		te = ctx.text_extents(text)
		ctx.move_to(x + w / 2 - te.width / 2, y + h / 2 + te.height / 2)
		ctx.text_path(text)
		ctx.set_source_rgb(0, 0, 0)
		ctx.fill()
	
	def render_url(self, ctx, box, url, level, draw, pointer):
		try:
			document = self.get_transformed_doc(url)
		except KeyError:
			self.error(f"no content registered for the url {url}", url, None)
			return []
		
		try:
			root = document.getroot()
		except AttributeError:
			pass
		else:
			return self.render_xml(ctx, box, root, [], url, level, draw, pointer)
		
		if isinstance(document, cairo.Surface):
			ctx.set_source_surface(document, box[0], box[1])
			ctx.rectangle(box[0], box[1], box[2], box[3])
			ctx.clip()
			if draw:
				ctx.paint()
			if pointer:
				if ctx.in_clip(*ctx.device_to_user(*pointer)):
					return [None]
			return []
		
		self.error(f"non-image document under url: {url}", url, None)
		return []


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	class PseudoContext:
		def __init__(self, name):
			self.__name = name
		
		def get_current_point(self):
			print(self.__name + '.get_current_point()')
			return 0, 0
		
		def get_line_width(self):
			print(self.__name + '.get_line_width()')
			return 1
		
		def copy_path(self):
			print(self.__name + '.copy_path()')
			return [(cairo.PATH_MOVE_TO, (0, 0))]
		
		def path_extents(self):
			print(self.__name + '.path_extents()')
			return 0, 0, 1, 1
		
		def set_dash(self, dashes, offset):
			print(self.__name + '.set_dash(', repr(dashes), ',', repr(offset), ')')
		
		def __getattr__(self, attr):
			return lambda *args: print(self.__name + '.' + attr + str(args))
	
	class ExtXMLModel(XMLModel):
		def update(self):
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			rnd.render(ctx, (0, 0, 1024, 768))
	
	rnd = ExtXMLModel()
	for filepath in Path('gfx').iterdir():
		print()
		print(filepath)
		rnd.open(str(filepath))

'''


