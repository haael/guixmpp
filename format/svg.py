#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'SVGFormat',


import re
import math
from math import pi, radians
from enum import Enum
import cairo
from collections import defaultdict, namedtuple
from itertools import chain, starmap
from urllib.parse import quote as url_quote
import PIL.Image, PIL.ImageFilter


try:
	distance = math.dist
except AttributeError:
	def distance(a, b):
		return math.sqrt(sum((_a - _b)**2 for (_a, _b) in zip(a, b)))


class NotANumber(BaseException):
	def __init__(self, original):
		self.original = original


class OverlayElement:
	def __init__(self, one, two, parent, tag=None):
		self.__one = one
		self.__two = two
		self.__parent = parent
		self.__tag = tag
	
	def __repr__(self):
		return f"<OverlayElement {self.tag}>"
	
	def __eq__(self, other):
		try:
			return self.tag == other.tag and self.attrib == other.attrib
		except AttributeError:
			return NotImplemented
	
	def __hash__(self):
		return hash((self.tag, tuple(sorted(self.attrib.items()))))
	
	def getparent(self):
		return self.__parent
	
	@property
	def tag(self):
		if self.__tag is not None:
			return self.__tag
		else:
			return self.__two.tag
	
	@property
	def attrib(self):
		if self.__one is not None:
			a = dict()
			a.update(self.__two.attrib)
			a.update(self.__one.attrib)
			
			try:
				a[f'{{{SVGFormat.xmlns_xlink}}}href'] = self.__two.attrib[f'{{{SVGFormat.xmlns_xlink}}}href']
			except KeyError:
				pass
			
			try:
				a['href'] = self.__two.attrib['href']
			except KeyError:
				pass
			
			if 'transform' in self.__one.attrib:
				a['transform'] = self.__one.attrib['transform'] + self.__two.attrib.get('transform', '')
			
			if 'gradientTransform' in self.__one.attrib:
				a['gradientTransform'] = self.__one.attrib['gradientTransform'] + self.__two.attrib.get('gradientTransform', '')
			
			return a
		else:
			return self.__two.attrib
	
	def __getattr__(self, attr):
		if attr[0] != '_':
			return getattr(self.__two, attr)
		else:
			raise AttributeError(f"No attibute found in OverlayElement: {attr}")
	
	def __len__(self):
		return len(self.__two)
	
	def __getitem__(self, index):
		original = self.__two[index]
		return self.__class__(None, original, self)


class SVGFormat:
	xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	xmlns_svg = 'http://www.w3.org/2000/svg'
	xmlns_xlink = 'http://www.w3.org/1999/xlink'
	xmlns_sodipodi = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
	xmlns_inkscape = 'http://www.inkscape.org/namespaces/inkscape'
	
	supported_svg_features = frozenset(['http://www.w3.org/TR/SVG11/feature#Shape'])
	supported_svg_extensions = frozenset()
	
	web_colors = {
		'aliceblue': '#F0F8FF',
		'antiquewhite': '#FAEBD7',
		'aqua': '#00FFFF',
		'aquamarine': '#7FFFD4',
		'azure': '#F0FFFF',
		'beige': '#F5F5DC',
		'bisque': '#FFE4C4',
		'black': '#000000',
		'blanchedalmond': '#FFEBCD',
		'blue': '#0000FF',
		'blueviolet': '#8A2BE2',
		'brown': '#A52A2A',
		'burlywood': '#DEB887',
		'cadetblue': '#5F9EA0',
		'chartreuse': '#7FFF00',
		'chocolate': '#D2691E',
		'coral': '#FF7F50',
		'cornflowerblue': '#6495ED',
		'cornsilk': '#FFF8DC',
		'crimson': '#DC143C',
		'cyan': '#00FFFF',
		'darkblue': '#00008B',
		'darkcyan': '#008B8B',
		'darkgoldenrod': '#B8860B',
		'darkgray': '#A9A9A9',
		'darkgreen': '#006400',
		'darkgrey': '#A9A9A9',
		'darkkhaki': '#BDB76B',
		'darkmagenta': '#8B008B',
		'darkolivegreen': '#556B2F',
		'darkorange': '#FF8C00',
		'darkorchid': '#9932CC',
		'darkred': '#8B0000',
		'darksalmon': '#E9967A',
		'darkseagreen': '#8FBC8F',
		'darkslateblue': '#483D8B',
		'darkslategray': '#2F4F4F',
		'darkslategrey': '#2F4F4F',
		'darkturquoise': '#00CED1',
		'darkviolet': '#9400D3',
		'deeppink': '#FF1493',
		'deepskyblue': '#00BFFF',
		'dimgray': '#696969',
		'dimgrey': '#696969',
		'dodgerblue': '#1E90FF',
		'firebrick': '#B22222',
		'floralwhite': '#FFFAF0',
		'forestgreen': '#228B22',
		'fuchsia': '#FF00FF',
		'gainsboro': '#DCDCDC',
		'ghostwhite': '#F8F8FF',
		'gold': '#FFD700',
		'goldenrod': '#DAA520',
		'gray': '#808080',
		'green': '#008000',
		'greenyellow': '#ADFF2F',
		'grey': '#808080',
		'honeydew': '#F0FFF0',
		'hotpink': '#FF69B4',
		'indianred': '#CD5C5C',
		'indigo': '#4B0082',
		'ivory': '#FFFFF0',
		'khaki': '#F0E68C',
		'lavender': '#E6E6FA',
		'lavenderblush': '#FFF0F5',
		'lawngreen': '#7CFC00',
		'lemonchiffon': '#FFFACD',
		'lightblue': '#ADD8E6',
		'lightcoral': '#F08080',
		'lightcyan': '#E0FFFF',
		'lightgoldenrodyellow': '#FAFAD2',
		'lightgray': '#D3D3D3',
		'lightgreen': '#90EE90',
		'lightgrey': '#D3D3D3',
		'lightpink': '#FFB6C1',
		'lightsalmon': '#FFA07A',
		'lightseagreen': '#20B2AA',
		'lightskyblue': '#87CEFA',
		'lightslategray': '#778899',
		'lightslategrey': '#778899',
		'lightsteelblue': '#B0C4DE',
		'lightyellow': '#FFFFE0',
		'lime': '#00FF00',
		'limegreen': '#32CD32',
		'linen': '#FAF0E6',
		'magenta': '#FF00FF',
		'maroon': '#800000',
		'mediumaquamarine': '#66CDAA',
		'mediumblue': '#0000CD',
		'mediumorchid': '#BA55D3',
		'mediumpurple': '#9370DB',
		'mediumseagreen': '#3CB371',
		'mediumslateblue': '#7B68EE',
		'mediumspringgreen': '#00FA9A',
		'mediumturquoise': '#48D1CC',
		'mediumvioletred': '#C71585',
		'midnightblue': '#191970',
		'mintcream': '#F5FFFA',
		'mistyrose': '#FFE4E1',
		'moccasin': '#FFE4B5',
		'navajowhite': '#FFDEAD',
		'navy': '#000080',
		'oldlace': '#FDF5E6',
		'olive': '#808000',
		'olivedrab': '#6B8E23',
		'orange': '#FFA500',
		'orangered': '#FF4500',
		'orchid': '#DA70D6',
		'palegoldenrod': '#EEE8AA',
		'palegreen': '#98FB98',
		'paleturquoise': '#AFEEEE',
		'palevioletred': '#DB7093',
		'papayawhip': '#FFEFD5',
		'peachpuff': '#FFDAB9',
		'peru': '#CD853F',
		'pink': '#FFC0CB',
		'plum': '#DDA0DD',
		'powderblue': '#B0E0E6',
		'purple': '#800080',
		'red': '#FF0000',
		'rosybrown': '#BC8F8F',
		'royalblue': '#4169E1',
		'saddlebrown': '#8B4513',
		'salmon': '#FA8072',
		'sandybrown': '#F4A460',
		'seagreen': '#2E8B57',
		'seashell': '#FFF5EE',
		'sienna': '#A0522D',
		'silver': '#C0C0C0',
		'skyblue': '#87CEEB',
		'slateblue': '#6A5ACD',
		'slategray': '#708090',
		'slategrey': '#708090',
		'snow': '#FFFAFA',
		'springgreen': '#00FF7F',
		'steelblue': '#4682B4',
		'tan': '#D2B48C',
		'teal': '#008080',
		'thistle': '#D8BFD8',
		'tomato': '#FF6347',
		'turquoise': '#40E0D0',
		'violet': '#EE82EE',
		'wheat': '#F5DEB3',
		'white': '#FFFFFF',
		'whitesmoke': '#F5F5F5',
		'yellow': '#FFFF00',
		'yellowgreen': '#9ACD32',
	}
	
	def create_document(self, data, mime_type):
		if mime_type == 'image/svg+xml' or mime_type == 'image/svg':
			document = self.create_document(data, 'application/xml')
			if document.getroot().tag == f'{{{self.xmlns_svg}}}svg':
				return document
			else:
				raise ValueError("Not an SVG document.")
		else:
			return NotImplemented
	
	def is_svg_document(self, document):
		return self.is_xml_document(document) and document.getroot().tag == f'{{{self.xmlns_svg}}}svg'
	
	def scan_document_links(self, document):
		"Yield all links referenced by the SVG document, including `data:` links."
		
		if self.is_svg_document(document):
			def links():
				yield from document.scan_stylesheets()
				yield from self.__xlink_hrefs(document)
				yield from self.__data_internal_links(self.__style_attrs(document))
				yield from self.__data_internal_links(self.__style_tags(document))
			return links()
		else:
			return NotImplemented
	
	def __stylesheets(self, document):
		myurl = self.get_document_url(document)
		
		for link in document.scan_stylesheets():
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc
		
		for link in self.__data_internal_links(self.__style_tags(document)):
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc
	
	def __style_attrs(self, document):
		for styledtag in document.findall('.//*[@style]'):
			style = '* {' + styledtag.attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
	
	def __style_tags(self, document):
		for styletag in document.findall(f'.//{{{self.xmlns_svg}}}style'):
			try:
				mime = styletag.attrib['type'].lower()
			except KeyError:
				mime = 'text/css'
			style = styletag.text
			yield f'data:{mime},' + url_quote(style)
	
	def __xlink_hrefs(self, document):
		for linkedtag in document.findall(f'.//*[@{{{self.xmlns_xlink}}}href]'):
			if linkedtag.tag == f'{{{self.xmlns_svg}}}a' or linkedtag.tag.split('}')[0][1:] != self.xmlns_svg:
				continue
			href = linkedtag.attrib[f'{{{self.xmlns_xlink}}}href']
			yield href
		for linkedtag in document.findall(f'.//*[@href]'):
			if linkedtag.tag == f'{{{self.xmlns_svg}}}a' or linkedtag.tag.split('}')[0][1:] != self.xmlns_svg:
				continue
			href = linkedtag.attrib['href']
			yield href
	
	def __data_internal_links(self, urls):
		for url in urls:
			yield url
			if url.startswith('data:'):		
				yield from self.__data_internal_links(self.scan_document_links(self.get_document(url)))
	
	def element_tabindex(self, document, element):
		if self.is_svg_document(document):
			return None
		else:
			return NotImplemented
	
	def draw_image(self, view, document, ctx, box):
		"Perform SVG rendering."
		
		if not self.is_svg_document(document):
			return NotImplemented
		
		return self.__render_group(view, document, ctx, box, document.getroot())
	
	__presentation_attributes = frozenset([
		'alignment-baseline',
		'baseline-shift',
		'clip',
		'clip-path',
		'clip-rule',
		'color',
		'color-interpolation',
		'color-interpolation-filters',
		'color-profile',
		'color-rendering',
		'cursor',
		'd',
		'direction',
		'display',
		'dominant-baseline',
		'enable-background',
		'fill',
		'fill-opacity',
		'fill-rule',
		'filter',
		'flood-color',
		'flood-opacity',
		'font-family',
		'font-size',
		'font-size-adjust',
		'font-stretch',
		'font-style',
		'font-variant',
		'font-weight',
		'glyph-orientation-horizontal',
		'glyph-orientation-vertical',
		'image-rendering',
		'kerning',
		'letter-spacing',
		'lighting-color',
		'marker-end',
		'marker-mid',
		'marker-start',
		'mask',
		'opacity',
		'overflow',
		'pointer-events',
		'shape-rendering',
		'solid-color',
		'solid-opacity',
		'stop-color',
		'stop-opacity',
		'stroke',
		'stroke-dasharray',
		'stroke-dashoffset',
		'stroke-linecap',
		'stroke-linejoin',
		'stroke-miterlimit',
		'stroke-opacity',
		'stroke-width',
		'text-anchor',
		'text-decoration',
		'text-rendering',
		#'transform',
		'unicode-bidi',
		'vector-effect',
		'visibility',
		'word-spacing',
		'writing-mode'
	])
	
	__group_tags = frozenset(['svg', 'g', 'a', 'symbol'])
	__shape_tags = frozenset(['polygon', 'line', 'ellipse', 'circle', 'rect', 'path', 'text'])
	__skip_tags = frozenset(['defs', 'title', 'desc', 'metadata', 'style', 'linearGradient', 'radialGradient', 'script', 'animate', 'filter', 'switch'])
	
	def __media_test(self, view):
		return False
	
	def __pseudoclass_test(self, view, pseudoclass, node):
		#print("pseudoclass test", pseudoclass, node.tag, [_node.tag for _node in view.nodes_under_pointer])
		if pseudoclass == 'hover':
			return node in view.nodes_under_pointer
		#if pseudoclass in ['hover', 'active', 'focus', 'focus-visible', 'focus-within', 'default', 'fullscreen']:
		#	return node in view.hover_elements
		#elif pseudoclass in ['any-link', 'local-link', 'link', 'visited']:
		#	return node in view.link_elements
		#elif pseudoclass in ['current', 'buffering', 'muted', 'paused', 'picture-in-picture', 'playing', 'seeking', 'stalled', 'volume-locked']:
		#	return node in view.link_elements
		#elif pseudoclass in ['autofill', 'blank', 'checked', 'disabled', 'enabled', 'in-range', 'indeterminate', 'invalid', 'modal', 'optional', 'out-of-range', 'placeholder-shown', 'read-only', 'read-write', 'required', 'user-invalid', 'user-valid', 'valid']:
		#	return node in view.link_elements
		#elif pseudoclass in ['empty', 'first', 'first-child', 'first-of-type', 'left', 'last-child', 'last-of-type', 'right', 'root', 'target', 'target-within']:
		#	return node in view.link_elements
		return False
	
	def __get_attribute(self, view, document, ctx, box, node, attr, default):
		if attr not in self.__presentation_attributes:
			raise ValueError(f"Not a presentation attribute: {attr}")
		
		try:
			return self.__search_attribute(view, document, node, attr)
		except KeyError:
			return default
		
		#else:
		#	if attr in node.attrib:
		#		return node.attrib[attr]
		#	else:
		#		return default
	
	def __search_attribute(self, view, document, node, attr):
		"Search for effective presentation attribute. This will either be an explicit XML attribute, or attribute of one of ancestors, or CSS value."
		
		if node is not None:
			"inline style='...' attribute"
			try:
				style = node.attrib['style']
			except (KeyError, AttributeError):
				pass
			else:
				css = self.get_document('data:text/css,' + url_quote('* {' + style + '}'))
				css_attrs = css.match_element(node, (lambda *args: False), (lambda *args: False), self.xmlns_svg)
				if attr in css_attrs:
					return css_attrs[attr]
			
			"regular stylesheet (<style/> tag or external)"
			try:
				stylesheets = document.__stylesheets
			except AttributeError:
				stylesheets = list(self.__stylesheets(document))
				document.__stylesheets = stylesheets
			
			for stylesheet in stylesheets:
				css_attrs = stylesheet.match_element(node, (lambda *args: self.__media_test(view, *args)), (lambda *args: self.__pseudoclass_test(view, *args)), self.xmlns_svg)
				if attr in css_attrs:
					return css_attrs[attr]
			
			"XML attribute"
			try:
				return node.attrib[attr]
			except (KeyError, AttributeError):
				pass
		
		parent = node.getparent()
		if parent is not None:
			return self.__search_attribute(view, document, parent, attr)
		else:
			raise KeyError(f"Attribute {attr} not found in any of ancestors")
	
	def __render_group(self, view, document, ctx, box, node):
		"Render SVG group element and its subelements."
		
		display = self.__get_attribute(view, document, ctx, box, node, 'display', 'block').lower()
		visibility = self.__get_attribute(view, document, ctx, box, node, 'visibility', 'visible').lower()
		
		if visibility == 'collapse' or display == 'none':
			return []
		
		left, top, width, height = box
		
		transform = node.attrib.get('transform', None)
		
		x = self.__units(view, node.attrib.get('x', 0), percentage=width)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height)
		
		if transform or ((node.getparent() is not None) and (x or y)) or node.tag == f'{{{self.xmlns_svg}}}svg' or node.tag == f'{{{self.xmlns_svg}}}symbol':
			ctx.save()
		
		if node.tag == f'{{{self.xmlns_svg}}}svg':
			if left or top:
				ctx.translate(left, top)
			
			svg_width = self.__units(view, node.attrib.get('width', width), percentage=width)
			svg_height = self.__units(view, node.attrib.get('height', height), percentage=height)
			
			try:
				vb_x, vb_y, vb_w, vb_h = node.attrib.get('viewBox', None).split()
			except AttributeError:
				viewbox_x = viewbox_y = 0
				viewbox_w = svg_width
				viewbox_h = svg_height
			else:
				viewbox_x = self.__units(view, vb_x, percentage=width)
				viewbox_y = self.__units(view, vb_y, percentage=height)
				viewbox_w = self.__units(view, vb_w, percentage=width)
				viewbox_h = self.__units(view, vb_h, percentage=height)
			
			x_scale = width / viewbox_w
			y_scale = height / viewbox_h
			
			x_scale = y_scale = min(x_scale, y_scale)
			
			ctx.scale(x_scale, y_scale)
			ctx.translate(-viewbox_x, -viewbox_y)
			
			
			box = viewbox_x, viewbox_y, viewbox_w, viewbox_h

			ctx.rectangle(*box)
			ctx.clip()
		
		left, top, width, height = box
		
		if transform:
			self.__apply_transform(view, document, ctx, box, node, transform)
		
		if (node.getparent() is not None) and (x or y):
			ctx.translate(x, y)
		
		if node.tag == f'{{{self.xmlns_svg}}}symbol':
			ctx.rectangle(0, 0, width - left, height - top) # TODO: width and height attributes, box attribute
			ctx.clip()
			pass
		
		if node.tag == f'{{{self.xmlns_svg}}}a':
			try:
				href = node.attrib[f'{{{self.xmlns_xlink}}}href']
			except KeyError:
				href = node.attrib['href']
			if hasattr(ctx, 'tag_begin'):
				ctx.tag_begin('a', f'href=\'{href}\'')
		
		hover_nodes = []
		
		for n, child in enumerate(node):
			if not isinstance(child.tag, str) or child.tag == f'{{{self.xmlns_svg}}}symbol' or child.tag == f'{{{self.xmlns_sodipodi}}}namedview':
				continue
			
			while child.tag in [f'{{{self.xmlns_svg}}}use', f'{{{self.xmlns_svg}}}switch']:
				if child.tag == f'{{{self.xmlns_svg}}}use':
					child = self.__construct_use(document, child)
				if child.tag == f'{{{self.xmlns_svg}}}switch':
					for subchild in child:
						if not isinstance(subchild.tag, str): continue
						required_features = frozenset(subchild.attrib.get('requiredFeatures', '').strip().split())
						required_extensions = frozenset(subchild.attrib.get('requiredExtensions', '').strip().split())
						if required_features <= self.supported_svg_features and required_extensions <= self.supported_svg_extensions:
							child = subchild
							break
					else:
						self.emit_warning(view, f"Fequired features not satisfied.", child.tag, child)
			
			if any(child.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__skip_tags):
				pass
			elif any(child.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__shape_tags):
				hover_subnodes = self.__render_shape(view, document, ctx, box, child)
				hover_nodes.extend(hover_subnodes)
			elif any(child.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__group_tags):
				hover_subnodes = self.__render_group(view, document, ctx, box, child)
				hover_nodes.extend(hover_subnodes)
			elif child.tag == f'{{{self.xmlns_svg}}}image':
				hover_subnodes = self.__render_image(view, document, ctx, box, child)
				hover_nodes.extend(hover_subnodes)
			elif child.tag == f'{{{self.xmlns_svg}}}foreignObject':
				hover_subnodes = self.__render_foreign_object(view, document, ctx, box, child)
				hover_nodes.extend(hover_subnodes)
			
			else:
				self.emit_warning(view, f"Unsupported node: {child.tag}", child.tag, child)
		
		if node.tag == f'{{{self.xmlns_svg}}}a':
			if hasattr(ctx, 'tag_end'):
				ctx.tag_end('a')
		
		if transform or ((node.getparent() is not None) and (x or y)) or node.tag == f'{{{self.xmlns_svg}}}svg' or node.tag == f'{{{self.xmlns_svg}}}symbol':
			ctx.restore()
		
		if hover_nodes:
			hover_nodes.insert(0, node)
		return hover_nodes
	
	def __render_shape(self, view, document, ctx, box, node):
		left, top, width, height = box
		
		display = self.__get_attribute(view, document, ctx, box, node, 'display', 'block').lower()
		visibility = self.__get_attribute(view, document, ctx, box, node, 'visibility', 'visible').lower()
		
		if visibility == 'collapse' or display == 'none':
			return []
		
		#transform = self.__get_attribute(view, document, ctx, box, node, 'transform', None)
		transform = node.attrib.get('transform', None)
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, transform)
		
		if visibility != 'hidden':
			filter_ = self.__get_attribute(view, document, ctx, box, node, 'filter', None)
			filter_ = None # TODO
		else:
			filter_ = None
		
		if filter_:
			# TODO
			margin = 10
			image = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(box[2] + 2 * margin + 1), int(box[3] + 2 * margin + 1))
			image_ctx = cairo.Context(image)
			#image_ctx.set_matrix(ctx.get_matrix())
			image_ctx.translate(-left + margin, -top + margin)
			old_ctx = ctx
			ctx = image_ctx
		
		
		if node.tag == f'{{{self.xmlns_svg}}}rect':
			x, w, rx = [self.__units(view, node.attrib.get(_a, 0), percentage=width) for _a in ('x', 'width', 'rx')]
			y, h, ry = [self.__units(view, node.attrib.get(_a, 0), percentage=height) for _a in ('y', 'height', 'ry')]
			
			rx = max(rx, 0)
			ry = max(ry, 0)
			
			if rx or ry:
				self.__draw_rounded_rectangle(ctx, x, y, w, h, rx, ry)
			else:
				ctx.rectangle(x, y, w, h)
		
		elif node.tag == f'{{{self.xmlns_svg}}}circle':
			cx = self.__units(view, node.attrib.get('cx', 0), percentage=width)
			cy = self.__units(view, node.attrib.get('cy', 0), percentage=height)
			r = self.__units(view, node.attrib['r'], percentage=(width + height) / 2)
			ctx.arc(cx, cy, r, 0, 2*pi)
		
		elif node.tag == f'{{{self.xmlns_svg}}}ellipse':
			cx = self.__units(view, node.attrib['cx'], percentage=width)
			cy = self.__units(view, node.attrib['cy'], percentage=height)
			rx = self.__units(view, node.attrib['rx'], percentage=width)
			ry = self.__units(view, node.attrib['ry'], percentage=height)
			ctx.save()
			ctx.translate(cx, cy)
			ctx.scale(rx, ry)
			ctx.arc(0, 0, 1, 0, 2*pi)
			ctx.restore()
		
		elif node.tag == f'{{{self.xmlns_svg}}}line':
			x1 = self.__units(view, node.attrib['x1'], percentage=width)
			y1 = self.__units(view, node.attrib['y1'], percentage=height)
			x2 = self.__units(view, node.attrib['x2'], percentage=width)
			y2 = self.__units(view, node.attrib['y2'], percentage=height)
			ctx.move_to(x1, y1)
			ctx.line_to(x2, y2)
		
		elif node.tag == f'{{{self.xmlns_svg}}}polygon':
			points = node.attrib['points'].split()
			first = True
			for point in points:
				xs, ys, *_ = point.split(',')
				x = self.__units(view, xs, percentage=width)
				y = self.__units(view, ys, percentage=height)
				if first:
					ctx.move_to(x, y)
					first = False
				else:
					ctx.line_to(x, y)
			if not first:
				ctx.close_path()
		
		elif node.tag == f'{{{self.xmlns_svg}}}path':
			self.__draw_path(view, document, ctx, box, node)
		
		elif node.tag == f'{{{self.xmlns_svg}}}text':
			self.__draw_text(view, document, ctx, box, node)
		
		else:
			self.emit_warning(view, f"tag {node.tag} not supported by this method", node.tag, node)
		
		
		has_fill, has_stroke = self.__apply_paint(view, document, ctx, box, node, (visibility != 'hidden'))
		
		hover_nodes = []
		if view.pointer:
			px, py = ctx.device_to_user(*view.pointer)
			if ctx.in_clip(px, py):
				if ctx.in_fill(px, py) or ctx.in_stroke(px, py): # TODO: pointer events
					hover_nodes.append(node)
		
		ctx.new_path()
		
		if filter_:
			image.flush()
			
			#pil_filter = PIL.ImageFilter.GaussianBlur(10) # TODO: other filters
			
			#data = PIL.Image.frombytes('RGBa', (image.get_width(), image.get_height()), bytes(image.get_data())).filter(pil_filter).tobytes()
			#image = cairo.ImageSurface.create_for_data(bytearray(data), cairo.FORMAT_ARGB32, image.get_width(), image.get_height())
			
			ctx = old_ctx
			ctx.set_source_surface(image, -margin, -margin)
			ctx.rectangle(*box)
			ctx.fill_preserve()
			ctx.set_source_rgb(0, 0, 0)
			ctx.stroke()
			image.finish()
		
		if transform:
			ctx.restore()
		
		return hover_nodes
	
	def __construct_use(self, document, node):
		"Render a <use/> element, referencing another one."
		
		current_url = self.get_document_url(document)
		try:
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
		except KeyError:
			href = node.attrib['href']
		link = self.resolve_url(href, current_url)
		original = self.get_document(link)
		if original == None:
			self.emit_warning(view, f"Ref not found: {link}", link, node)
			raise KeyError
		else:
			original = original.getroot()
		
		target = OverlayElement(node, original, node.getparent())
		
		return target
	
	def image_dimensions(self, view, document):
		"Return the SVG dimensions, that might depend on the view state."
		
		if not self.is_svg_document(document):
			return NotImplemented
		
		node = document.getroot()
		
		try:
			svg_width = self.__units(view, node.attrib['width'], percentage=view.viewport_width)
		except KeyError:
			svg_width = view.viewport_width
		
		try:
			svg_height = self.__units(view, node.attrib['height'], percentage=view.viewport_height)
		except KeyError:
			svg_height = view.viewport_height
		
		return svg_width, svg_height
	
	def __units(self, view, spec, percentage=None, percentage_origin=0):
		if not isinstance(spec, str):
			return spec
		
		spec = spec.strip()
		if not spec:
			return 0
		
		shift = 0
		
		if spec[-2:] == 'px':
			scale = 1
			value = spec[:-2]
		elif spec[-2:] == 'ex':
			scale = 24 * 1.5 # TODO
			value = spec[:-2]
		elif spec[-2:] == 'mm':
			scale = view.screen_dpi / 25.4
			value = spec[:-2]
		elif spec[-2:] == 'cm':
			scale = view.screen_dpi / 2.54
			value = spec[:-2]
		elif spec[-2:] == 'in':
			scale = view.screen_dpi
			value = spec[:-2]
		elif spec[-2:] == 'pc':
			scale = view.screen_dpi / 6
			value = spec[:-2]
		elif spec[-2:] == 'pt':
			scale = view.screen_dpi / 72
			value = spec[:-2]
		elif spec[-2:] == 'em':
			scale = 1 # FIXME
			value = spec[:-2]
		elif spec[-1:] == 'Q':
			scale = view.screen_dpi / (2.54 * 40)
			value = spec[:-1]
		elif spec[-1:] == '%':
			if percentage == None:
				raise ValueError("Percentage not specified.")
			scale = percentage / 100
			shift = percentage_origin
			value = spec[:-1]
		else:
			scale = 1
			value = spec
		
		return self.__parse_float(value) * scale + shift
	
	@staticmethod
	def __parse_float(f):
		if f is None:
			return None
		elif f == 'null':
			return 0
		else:
			return float(f)
	
	__p_number = r'[+-]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][+-]?\d+)?' # regex pattern matching a floating point number
	__re_tokens = re.compile(fr'({__p_number}|[a-zA-Z])')
	__re_matrix = re.compile(fr'matrix\s*\(\s*({__p_number})\s*,?\s*({__p_number})\s*,?\s*({__p_number})\s*,?\s*({__p_number})\s*,?\s*({__p_number})\s*,?\s*({__p_number})\s*\)')
	__re_translate = re.compile(fr'translate\s*\(\s*({__p_number}[a-zA-Z%]*)\s*,?\s*({__p_number}[a-zA-Z%]*)\s*\)')
	__re_scale1 = re.compile(fr'scale\s*\(\s*({__p_number})\s*\)')
	__re_scale2 = re.compile(fr'scale\s*\(\s*({__p_number})\s*,?\s*({__p_number})\s*\)')
	__re_rotate1 = re.compile(fr'rotate\s*\(\s*({__p_number})\s*\)')
	__re_rotate3 = re.compile(fr'rotate\s*\(\s*({__p_number})\s*,?\s*({__p_number})\s*,?\s*({__p_number})\s*\)')
	__re_skewX = re.compile(fr'skewX\s*\(\s*({__p_number})\s*\)')
	__re_skewY = re.compile(fr'skewY\s*\(\s*({__p_number})\s*\)')
	
	@staticmethod
	def __transform_separators(text):
		text = text.replace(',', '')
		return not text or text.isspace()
	
	def __apply_transform(self, view, document, ctx, box, node, transform_string):
		left, top, width, height = box
		
		origin = node.attrib.get('transform-origin', '0 0').split()
		origin_x = self.__units(view, origin[0], percentage=width)
		origin_y = self.__units(view, origin[1], percentage=height)
		
		if origin_x or origin_y:
			ctx.save()
			ctx.translate(origin_x, origin_y)
		
		text = transform_string
		n = 0
		while n < len(text):
			match = self.__re_matrix.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				m0, m1, m2, m3, m4, m5 = map(self.__parse_float, list(match.groups()))
				transformation = cairo.Matrix(m0, m1, m2, m3, m4, m5)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			match = self.__re_translate.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				x, y = [self.__units(view, _spec) for _spec in match.groups()]
				ctx.translate(x, y)
				n = match.end()
				continue
			
			match = self.__re_scale1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				s, = map(self.__parse_float, list(match.groups()))
				ctx.scale(s, s)
				n = match.end()
				continue
			
			match = self.__re_scale2.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				sx, sy = map(self.__parse_float, list(match.groups()))
				ctx.scale(sx, sy)
				n = match.end()
				continue
			
			match = self.__re_rotate1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				r, = map(self.__parse_float, list(match.groups()))
				ctx.rotate(radians(r))
				n = match.end()
				continue
			
			match = self.__re_rotate3.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				r, cx, cy = map(self.__parse_float, list(match.groups()))
				ctx.translate(cx, cy)
				ctx.rotate(radians(r))
				ctx.translate(-cx, -cy)
				n = match.end()
				continue
			
			match = self.__re_skewX.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				a, = map(self.__parse_float, list(match.groups()))
				transformation = cairo.Matrix(1, 0, math.tan(radians(a)), 1, 0, 0)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			match = self.__re_skewY.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				a, = map(self.__parse_float, list(match.groups()))
				transformation = cairo.Matrix(1, math.tan(radians(a)), 0, 1, 0, 0)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			self.emit_warning(view, "Unsupported transformation: %s" % repr(text[n:]), text[n:], node)
			break
		
		if origin_x or origin_y:
			ctx.restore()
		
		return True
	
	def __apply_paint(self, view, document, ctx, box, node, draw):
		"Draw the current shape, applying fill and stroke. The path is preserved. Returns a pair of bool, indicating whether fill and stroke was non-transparent."
		
		has_fill = False
		ctx.save()
		if self.__apply_fill(view, document, ctx, box, node):
			has_fill = True
			if draw:
				ctx.fill_preserve()
		ctx.restore()
		
		has_stroke = False
		ctx.save()
		if self.__apply_stroke(view, document, ctx, box, node):
			has_stroke = True
			if draw:
				ctx.stroke_preserve()
		ctx.restore()
		
		return has_fill, has_stroke
	
	def __apply_fill(self, view, document, ctx, box, node):
		"Prepares the context to fill() operation, including setting color and fill rules."
		
		if not self.__apply_color(view, document, ctx, box, node, 'fill', 'fill-opacity', 'black'):
			return False
		
		fill_rule = self.__get_attribute(view, document, ctx, box, node, 'fill-rule', None)
		
		if fill_rule == 'evenodd':
			ctx.set_fill_rule(cairo.FillRule.EVEN_ODD)
		elif fill_rule == 'winding':
			ctx.set_fill_rule(cairo.FillRule.WINDING)
		elif fill_rule == 'nonzero':
			self.emit_warning(view, f"Unsupported fill rule: {fill_rule}", fill_rule, node) # TODO
		elif fill_rule == None:
			pass
		else:
			self.emit_warning(view, f"Unsupported fill rule: {fill_rule}", fill_rule, node)
		
		return True
	
	def __apply_stroke(self, view, document, ctx, box, node):
		"Prepares the context to stroke() operation, including setting color and line parameters."
		
		if not self.__apply_color(view, document, ctx, box, node, 'stroke', 'stroke-opacity', 'none'):
			return False
		
		try:
			stroke_width = self.__units(view, str(self.__get_attribute(view, document, ctx, box, node, 'stroke-width', 1)))
		except ValueError:
			self.emit_warning(view, f"Unsupported stroke spec: {self.__get_attribute(view, document, ctx, box, node, 'stroke-width')}", self.__get_attribute(view, document, ctx, box, node, 'stroke-width'), node)
			return False
		
		if stroke_width > 0:
			ctx.set_line_width(stroke_width)
		else:
			return False
		
		linecap = self.__get_attribute(view, document, ctx, box, node, 'stroke-linecap', 'butt')
		if linecap == 'butt':
			ctx.set_line_cap(cairo.LINE_CAP_BUTT)
		elif linecap == 'round':
			ctx.set_line_cap(cairo.LINE_CAP_ROUND)
		elif linecap == 'square':
			ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
		else:
			self.emit_warning(view, "Unsupported linecap", linecap, node)
		
		pathLength = self.__parse_float(node.attrib.get('pathLength', None))
		if pathLength is None:
			pathScale = 1
		else:
			pathScale = self.__get_current_path_length(ctx) / pathLength
		
		dasharray = self.__get_attribute(view, document, ctx, box, node, 'stroke-dasharray', 'none')
		if dasharray == 'none':
			ctx.set_dash([], 0)
		else:
			dashoffset = self.__parse_float(self.__get_attribute(view, document, ctx, box, node, 'stroke-dashoffset', 0)) * pathScale
			
			try:
				ctx.set_dash([self.__parse_float(dasharray) * pathScale + 0], dashoffset)
			except ValueError:
				try:
					dashes = [_x * pathScale for _x in map(self.__parse_float, dasharray.split())]
				except ValueError:
					dashes = [_x * pathScale for _x in map(self.__parse_float, dasharray.split(','))]
				ctx.set_dash(dashes, dashoffset)
		
		'''
		try:
			linejoin = self.__search_attrib(view, node, 'stroke-linejoin')
		except KeyError:
			pass
		else:
			pass # TODO
		
		try:
			mitterlimit = self.__search_attrib(view, node, 'stroke-mitterlimit')
		except KeyError:
			pass
		else:
			pass # TODO
		'''
		
		return True
	
	def __apply_color(self, view, document, ctx, box, node, color_attr, opacity_attr, default_color):
		"Set painting source to the color identified by provided parameters."
		
		color = self.__get_attribute(view, document, ctx, box, node, color_attr, default_color).strip()
		target = node.getparent()
		while color in ('currentColor', 'inherit') and (target is not None):			
			if color == 'currentColor':
				color = self.__get_attribute(view, document, ctx, box, target, 'color', default_color).strip()
			elif color == 'inherit':
				color = self.__get_attribute(view, document, ctx, box, target, color_attr, default_color).strip()
			target = target.getparent()
		
		assert color != 'currentColor' and color != 'inherit'
		
		try:
			color = self.web_colors[color.lower()]
		except KeyError:
			pass
		
		try:
			if not color or color.lower() in ('none', 'transparent'):
				return False
		except AttributeError:
			pass
		
		a = self.__parse_float(self.__get_attribute(view, document, ctx, box, node, opacity_attr, None))
		if a == 0: # None means 1, not 0
			return False
		
		if color[0] == '#' and len(color) == 4:
			r, g, b = [int(_c, 16) / 15 for _c in color[1:]]
		elif color[0] == '#' and len(color) == 7:
			r, g, b = [int(_c, 16) / 255 for _c in (color[1:3], color[3:5], color[5:7])]
		elif color[:4] == 'url(' and color[-1] == ')':
			href = color.strip()[4:-1]
			if href[0] == '"' and href[-1] == '"': href = href[1:-1]
			return self.__apply_pattern(view, document, ctx, box, node, href)
			# TODO: transparency
		elif color[:4] == 'rgb(' and color[-1] == ')':
			r, g, b = [max(0, min(1, (self.__parse_float(_c) / 255 if _c.strip()[-1] != '%' else self.__parse_float(_c.strip()[:-1]) / 100))) for _c in color[4:-1].split(',')]
		else:
			self.emit_warning(view, f"Unsupported color specification in {color_attr}: {color}", color, node)
			return False
		
		try:
			if a == None:
				ctx.set_source_rgb(r, g, b)
			else:
				ctx.set_source_rgba(r, g, b, a)
		except UnboundLocalError:
			pass
		
		return True
	
	def __apply_pattern(self, view, document, ctx, box, node, url):
		"Set painting source to a pattern, i.e. a gradient, identified by url."
		
		current_url = self.get_document_url(document)
		href = self.resolve_url(url, current_url)
		target_doc = self.get_document(href)
		if target_doc == None:
			self.emit_warning(view, f"Color pattern ref not found: {href}", href, node)
			return []
		else:
			target = target_doc.getroot()
		
		left, top, width, height = box
		
		if target.tag == f'{{{self.xmlns_svg}}}linearGradient' or target.tag == f'{{{self.xmlns_svg}}}radialGradient':
			gradient_units = target.attrib.get('gradientUnits', 'objectBoundingBox')
			if gradient_units == 'userSpaceOnUse':
				gleft = 0
				gtop = 0
				gwidth = width
				gheight = height
				gscalex = 1
				gscaley = 1
			elif gradient_units == 'objectBoundingBox':
				gleft, gtop, gright, gbottom = ctx.path_extents()
				gwidth = gright - gleft
				gheight = gbottom - gtop
				gscalex = gwidth
				gscaley = gheight
			else:
				self.emit_warning(vie, "Unknown gradient units.", gradient_units, target)
			
			try:
				try:
					href = target.attrib[f'{{{self.xmlns_xlink}}}href']
				except KeyError:
					href = target.attrib['href']
			except KeyError:
				pass
			else:
				href = self.resolve_url(href, current_url)
				orig_target = target
				next_gradient_doc = self.get_document(href)
				if next_gradient_doc == None:
					self.emit_warning(view, f"Ref not found: {href}", href, node)
					return False
				else:
					next_gradient = next_gradient_doc.getroot()
					target = OverlayElement(orig_target, next_gradient, orig_target.getparent(), orig_target.tag)
			
			if target.tag == f'{{{self.xmlns_svg}}}linearGradient':					
				try:
					spec = target.attrib['x1']
					if spec[-1] == '%':
						x1 = self.__parse_float(spec[:-1]) / 100 * gwidth
					else:
						x1 = self.__parse_float(spec) * gscalex
				except KeyError:
					x1 = 0
				except ValueError:
					self.emit_warning(view, "Invalid x1 specification in linear gradient.", target.attrib['x1'], target)
					x1 = 0
				
				try:
					spec = target.attrib['y1']
					if spec[-1] == '%':
						y1 = self.__parse_float(spec[:-1]) / 100 * gheight
					else:
						y1 = self.__parse_float(spec) * gscaley
				except KeyError:
					y1 = 0
				except ValueError:
					self.emit_warning(view, "Invalid y1 specification in linear gradient.", target.attrib['y1'], target)
					y1 = 0
				
				try:
					spec = target.attrib['x2']
					if spec[-1] == '%':
						x2 = self.__parse_float(spec[:-1]) / 100 * gwidth
					else:
						x2 = self.__parse_float(spec) * gscalex
				except KeyError:
					x2 = gwidth
				except ValueError:
					self.emit_warning(view, "Invalid x2 specification in linear gradient.", target.attrib['x2'], target)
					x2 = gwidth
				
				try:
					spec = target.attrib['y2']
					if spec[-1] == '%':
						y2 = self.__parse_float(spec[:-1]) / 100 * gheight
					else:
						y2 = self.__parse_float(spec) * gscaley
				except KeyError:
					y2 = 0
				except ValueError:
					self.emit_warning(view, "Invalid y2 specification in linear gradient.", target.attrib['y2'], target)
					y2 = 0
				
				gradient = cairo.LinearGradient(x1 + gleft, y1 + gtop, x2 + gleft, y2 + gtop)
			
			elif target.tag == f'{{{self.xmlns_svg}}}radialGradient':
				try:
					spec = target.attrib['r']
					if spec[-1] == '%':
						r = self.__parse_float(spec[:-1]) / 100 * (gwidth + gheight) / 2
					else:
						r = self.__parse_float(spec) * (gscalex + gscaley) / 2
				except KeyError:
					r = (gwidth + gheight) / 2
				except ValueError:
					self.emit_warning(view, "Invalid r specification in radial gradient.", target.attrib['r'], target)
					r = (gwidth + gheight) / 2
				
				try:
					spec = target.attrib['cx']
					if spec[-1] == '%':
						cx = self.__parse_float(spec[:-1]) / 100 * gwidth
					else:
						cx = self.__parse_float(spec) * gscalex
				except KeyError:
					cx = gwidth / 2
				except ValueError:
					self.emit_warning(view, "Invalid cx specification in linear gradient.", target.attrib['cx'], target)
					cx = gwidth / 2
				
				try:
					spec = target.attrib['cy']
					if spec[-1] == '%':
						cy = self.__parse_float(spec[:-1]) / 100 * gheight
					else:
						cy = self.__parse_float(spec) * gscaley
				except KeyError:
					cy = gheight / 2
				except ValueError:
					self.emit_warning(view, "Invalid cy specification in linear gradient.", target.attrib['cy'], target)
					cy = gheight / 2
				
				try:
					spec = target.attrib['fr']
					if spec[-1] == '%':
						fr = self.__parse_float(spec[:-1]) / 100 * (gwidth + gheight) / 2
					else:
						fr = self.__parse_float(spec) * (gscalex + gscaley) / 2
				except KeyError:
					fr = 0
				except ValueError:
					self.emit_warning(view, "Invalid r specification in radial gradient.", target.attrib['fr'], target)
					fr = 0
				
				try:
					spec = target.attrib['fx']
					if spec[-1] == '%':
						fx = self.__parse_float(spec[:-1]) / 100 * gwidth
					else:
						fx = self.__parse_float(spec) * gscalex
				except KeyError:
					fx = cx
				except ValueError:
					self.emit_warning(view, "Invalid fx specification in linear gradient.", target.attrib['fx'], target)
					fx = cx
				
				try:
					spec = target.attrib['fy']
					if spec[-1] == '%':
						fy = self.__parse_float(spec[:-1]) / 100 * gheight
					else:
						fy = self.__parse_float(spec) * gscaley
				except KeyError:
					fy = cy
				except ValueError:
					self.emit_warning(view, "Invalid cy specification in linear gradient.", target.attrib['fy'], target)
					fy = cy
				
				gradient = cairo.RadialGradient(fx + gleft, fy + gtop, fr, cx + gleft, cy + gtop, r)
			
			last_offset = 0
			for cn, colorstop in enumerate(target):
				try:
					offset_spec = colorstop.attrib['offset']
					if offset_spec[-1] == '%':
						offset = self.__parse_float(offset_spec[:-1]) / 100
					else:
						offset = self.__parse_float(offset_spec)
				except KeyError:
					offset = last_offset
				except ValueError:
					self.emit_warning(view, "Error in offset spec of a linear gradient.", colorstop.attrib['offset'], colorstop)
					offset = last_offset
				
				last_offset = offset
				stop_color = None
				stop_opacity = None
				
				stop_color = self.__get_attribute(view, document, ctx, box, colorstop, 'stop-color', None)
				if stop_color == None:
					self.emit_warning(view, "Stop color of linear gradient not found.", None, colorstop)
					continue
				
				stop_opacity = self.__parse_float(self.__get_attribute(view, document, ctx, box, colorstop, 'stop-opacity', None))
				
				if not stop_color or stop_color.lower() in ('none', 'transparent'):
					continue
				
				try:
					stop_color = self.web_colors[stop_color.lower()]
				except KeyError:
					pass
				
				if len(stop_color) not in (4, 7) or stop_color[0] != '#':
					self.emit_warning(view, "Unsupported color specification in gradient: %s" % stop_color, stop_color, colorstop)
					continue
				elif len(stop_color) == 7:
					r = int(stop_color[1:3], 16) / 255
					g = int(stop_color[3:5], 16) / 255
					b = int(stop_color[5:7], 16) / 255
				elif len(stop_color) == 4:
					r = int(stop_color[1:2], 16) / 15
					g = int(stop_color[2:3], 16) / 15
					b = int(stop_color[3:4], 16) / 15
				
				if stop_opacity == None:
					gradient.add_color_stop_rgb(offset, r, g, b)
				else:
					gradient.add_color_stop_rgba(offset, r, g, b, stop_opacity)
			
			gradient_transform = target.attrib.get('gradientTransform', None)
			if gradient_transform is not None:
				self.__apply_transform(view, document, ctx, box, target, gradient_transform)
			
			ctx.set_source(gradient)
		else:
			self.emit_warning(view, "Unsupported fill element: %s" % target.tag, target.tag, node)
			return False
		
		return True
	
	@staticmethod
	def __get_current_path_length(ctx):
		l = 0
		cx, cy = None, None
		sx, sy = None, None
		first = True
		for type_, points in ctx.copy_path():
			if type_ == cairo.PATH_MOVE_TO:
				if first:
					sx, sy = points
					first = False
				cx, cy = points
			elif type_ == cairo.PATH_LINE_TO:
				x, y = points
				l += distance((cx, cy), (x, y))
				cx, cy = x, y
			elif type_ == cairo.PATH_CURVE_TO:
				x1, y1, x2, y2, x3, y3 = points
				ctrl_poly_len = distance((cx, cy), (x1, y1)) + distance((x1, y1), (x2, y2)) + distance((x2, y2), (x3, y3))
				steps = 2 + int(3 * ctrl_poly_len) # number of steps from the length of the control polygon
				sl = 0
				for i in range(steps): # integrate
					t = i / steps
					x = cx * (1.0 - t)**3 + 3.0 * x1 * (1.0 - t)**2 * t + 3.0 * x2 * (1.0 - t) * t**2 + x3 * t**3
					y = cy * (1.0 - t)**3 + 3.0 * y1 * (1.0 - t)**2 * t + 3.0 * y2 * (1.0 - t) * t**2 + y3 * t**3
					if i > 0:
						sl += distance((x, y), (px, py))
					px, py = x, y
				
				l += sl * 1.005 # TODO: correction (the calculated length is always smaller than actual)
				
				cx, cy = x3, y3
			elif type_ == cairo.PATH_CLOSE_PATH:
				l += distance((cx, cy), (sx, sy))
				cx, cy = sx, sy
		
		return l
	
	def __draw_text(self, view, document, ctx, box, node):
		left, top, width, height = box
		
		x = self.__units(view, node.attrib.get('x', 0), percentage=width)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height)
		
		ctx.move_to(x, y)
		
		strip = node.attrib.get(f'{{{self.xmlns_xml}}}space', '') != 'preserve'
		
		text_anchor = self.__apply_font(view, document, ctx, box, node)
		
		#total_text = self.__total_text(node, strip)
		
		if node.text:
			txt = node.text
			if strip: txt = txt.strip()
			
			extents = ctx.text_extents(txt)
			if text_anchor == 'end':
				anchor_shift = -extents.width
			elif text_anchor == 'middle':
				anchor_shift = -extents.width / 2
			else:
				anchor_shift = 0
			#ctx.rel_move_to(anchor_shift, 0)
			
			ctx.save()
			ctx.rel_move_to(anchor_shift, 0)
			ctx.text_path(txt)
			ctx.restore()
		
		for child in node:
			if child.tag != f'{{{self.xmlns_svg}}}tspan':
				self.emit_warning(view, "Unsupported tag %s" % child.tag, child.tag, child)
				continue
			self.__draw_tspan(view, document, ctx, box, child, strip)
			
			if child.tail:
				txt = child.tail
				if strip: txt = txt.strip()
				
				extents = ctx.text_extents(txt)
				if text_anchor == 'end':
					anchor_shift = -extents.width
				elif text_anchor == 'middle':
					anchor_shift = -extents.width / 2
				else:
					anchor_shift = 0
				
				ctx.save()
				ctx.rel_move_to(anchor_shift, 0)
				ctx.text_path(txt)
				ctx.restore()
	
	def __apply_font(self, view, document, ctx, box, node):
		left, top, width, height = box
		
		font_family = self.__get_attribute(view, document, ctx, box, node, 'font-family', '')
		font_style_attrib = self.__get_attribute(view, document, ctx, box, node, 'font-style', 'normal')
		font_weight_attrib = self.__get_attribute(view, document, ctx, box, node, 'font-weight', 'normal')
		
		if font_style_attrib == 'normal':
			font_style = cairo.FontSlant.NORMAL
		elif font_style_attrib == 'italic':
			font_style = cairo.FontSlant.ITALIC
		elif font_style_attrib == 'oblique':
			font_style = cairo.FontSlant.OBLIQUE
		else:
			self.emit_warning(view, f"Unsupported font style '{font_style_attrib}'", font_style_attrib, node)
			font_style = cairo.FontSlant.NORMAL
		
		if font_weight_attrib == 'normal':
			font_weight = cairo.FontWeight.NORMAL
		elif font_weight_attrib == 'bold':
			font_weight = cairo.FontWeight.BOLD
		else:
			try:
				font_weight_number = int(font_weight_attrib)
			except ValueError:
				self.emit_warning(view, f"Unsupported font weight '{font_weight_attrib}'", font_weight_attrib, node)
				font_weight = cairo.FontWeight.NORMAL
			else:
				if font_weight_number > 500:
					font_weight = cairo.FontWeight.BOLD
				else:
					font_weight = cairo.FontWeight.NORMAL
		
		for family in font_family.split(','):
			ctx.select_font_face(family, font_style, font_weight)
		
		font_size_attrib = self.__get_attribute(view, document, ctx, box, node, 'font-size', '12') # FIXME: default font size 12?
		font_size = self.__units(view, font_size_attrib, percentage=(width + height) / 2)
		ctx.set_font_size(font_size)
		
		text_anchor = self.__get_attribute(view, document, ctx, box, node, 'text-anchor', '').strip()
		return text_anchor

	def __draw_tspan(self, view, document, ctx, box, node, strip):
		left, top, width, height = box
		ctx.save()
		
		x = self.__units(view, node.attrib.get('x', 0), percentage=width)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height)		
		if x or y:
			ctx.move_to(x, y)
		
		dx = self.__units(view, node.attrib.get('dx', 0), percentage=width)
		dy = self.__units(view, node.attrib.get('dy', 0), percentage=height)
		if dx or dy:
			ctx.rel_move_to(dx, dy)
		
		text_anchor = self.__get_attribute(view, document, ctx, box, node, 'text-anchor', '').strip()
		
		if node.text:
			txt = node.text
			if strip: txt = txt.strip()
			
			extents = ctx.text_extents(txt)
			if text_anchor == 'end':
				anchor_shift = -extents.width
			elif text_anchor == 'middle':
				anchor_shift = -extents.width / 2
			else:
				anchor_shift = 0
			
			ctx.save()
			ctx.rel_move_to(anchor_shift, 0)
			ctx.text_path(txt)
			ctx.restore()
		
		for child in node:
			if child.tag != f'{{{self.xmlns_svg}}}tspan':
				self.emit_warning(view, "Unsupported tag %s" % child.tag, child.tag, child)
				continue
			self.__draw_tspan(view, document, ctx, box, child, strip)
			
			if child.tail:
				txt = child.tail
				if strip: txt = txt.strip()

				extents = ctx.text_extents(txt)
				if text_anchor == 'end':
					anchor_shift = -extents.width
				elif text_anchor == 'middle':
					anchor_shift = -extents.width / 2
				else:
					anchor_shift = 0

				ctx.save()
				ctx.rel_move_to(anchor_shift, 0)
				ctx.text_path(txt)
				ctx.restore()
		
		ctx.restore()
	
	def __draw_path(self, view, document, ctx, box, node):
		"Create path in the context, with parameters taken from the `d` attribute of the provided node."
		
		left, top, width, height = box
		
		text = node.attrib['d']
		
		tokens = (_t for _t in (_t.strip() for _t in self.__re_tokens.split(text)) if (_t and _t != ','))
		
		token = None
		first = True
		
		def next_token():
			nonlocal token, first
			token = next(tokens)
			first = False
			return token
		
		def next_coord(percentage=None):
			try:
				return self.__units(view, next_token(), percentage)
			except (ValueError, AttributeError, TypeError) as error:
				raise NotANumber(error)
		
		next_token()
		
		first = True
		
		while True:
			try:
				command = token
				
				if command not in 'CcQqSsTt':
					lx, ly = 0, 0
				
				if command in 'M':
					x = next_coord(width)
					y = next_coord(height)
					ctx.move_to(x, y)
					
					while True:
						x = next_coord(width)
						y = next_coord(height)
						ctx.line_to(x, y)
				
				elif command in 'm':
					lfirst = first
					x = next_coord(width)
					y = next_coord(height)
					
					if lfirst:
						ctx.move_to(x, y)
					else:
						ctx.rel_move_to(x, y)
					
					while True:
						x = next_coord(width)
						y = next_coord(height)
						ctx.rel_line_to(x, y)
				
				elif command in 'L':
					while True:
						x = next_coord(width)
						y = next_coord(height)
						ctx.line_to(x, y)
				
				elif command in 'l':
					while True:
						x = next_coord(width)
						y = next_coord(height)
						ctx.rel_line_to(x, y)
				
				elif command in 'H':
					while True:
						x, y = ctx.get_current_point()
						x = next_coord(width)
						ctx.line_to(x, y)
				
				elif command in 'h':
					while True:
						x = next_coord(width)
						ctx.rel_line_to(x, 0)
				
				elif command in 'V':
					while True:
						x, y = ctx.get_current_point()
						y = next_coord(height)
						ctx.line_to(x, y)
				
				elif command in 'v':
					while True:
						y = next_coord(height)
						ctx.rel_line_to(0, y)
				
				elif command in 'C':
					while True:
						x1, y1 = next_coord(width), next_coord(height)
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x2 - x3, y2 - y3
				
				elif command in 'c':
					while True:
						x1, y1 = next_coord(width), next_coord(height)
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x2 - x3, y2 - y3
				
				elif command in 'S':
					x0, y0 = ctx.get_current_point()
					while True:
						x1, y1 = x0 - lx, y0 - ly
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						#ctx.line_to(x3, y3)
						lx, ly = x2 - x3, y2 - y3
						x0, y0 = x3, y3
				
				elif command in 's':
					while True:
						x1, y1 = -lx, -ly
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						#ctx.rel_line_to(x3, y3)
						lx, ly = x2 - x3, y2 - y3
				
				elif command in 'Q':
					x0, y0 = ctx.get_current_point()
					while True:
						xm, ym = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (2 / 3 * xm + 1 / 3 * x0), (2 / 3 * ym + 1 / 3 * y0)
						x2, y2 = (2 / 3 * xm + 1 / 3 * x3), (2 / 3 * ym + 1 / 3 * y3)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						#ctx.line_to(x3, y3)
						lx, ly = x2 - x3, y2 - y3
						x0, y0 = x3, y3
				
				elif command in 'q':
					while True:
						xm, ym = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (2 / 3 * xm), (2 / 3 * ym)
						x2, y2 = (2 / 3 * xm + 1 / 3 * x3), (2 / 3 * ym + 1 / 3 * y3)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						#ctx.rel_line_to(x3, y3)
						lx, ly = x2 - x3, y2 - y3
				
				elif command in 'T':
					x0, y0 = ctx.get_current_point()
					while True:
						xm, ym = x0 - lx, y0 - ly
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (2 / 3 * xm + 1 / 3 * x0), (2 / 3 * ym + 1 / 3 * y0)
						x2, y2 = (2 / 3 * xm + 1 / 3 * x3), (2 / 3 * ym + 1 / 3 * y3)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						#ctx.line_to(x3, y3)
						lx, ly = x2 - x3, y2 - y3
						x0, y0 = x3, y3
				
				elif command in 't':
					while True:
						xm, ym = -lx, -ly
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (2 / 3 * xm), (2 / 3 * ym)
						x2, y2 = (2 / 3 * xm + 1 / 3 * x3), (2 / 3 * ym + 1 / 3 * y3)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						#ctx.rel_line_to(x3, y3)
						lx, ly = x2 - x3, y2 - y3
				
				elif command in 'Aa':
					while True:
						try:
							x_start, y_start = ctx.get_current_point()
						except TypeError:
							x_start, y_start = 0, 0
						
						rx, ry = next_coord(width), next_coord(height)
						angle, large_arc_flag, sweep_flag = [next_coord() for _i in range(3)]
						x_stop, y_stop = next_coord(width), next_coord(height)
						
						if command == 'a':
							x_stop += x_start
							y_stop += y_start
						
						angle = radians(angle)
						rx, ry = abs(rx), abs(ry)
						large_arc_flag = bool(large_arc_flag)
						sweep_flag = bool(sweep_flag)
						
						self.__draw_arc(ctx, x_start, y_start, x_stop, y_stop, rx, ry, angle, large_arc_flag, sweep_flag)
				
				elif command in 'Zz':
					ctx.close_path()
					first = True
				
				else:
					self.emit_warning(view, 'Unsupported path syntax: %s' % command, tokens, node)
					#raise ValueError("Unsupported path syntax")
				
				next_token()
			
			except NotANumber:
				continue
			except StopIteration:
				break
			except ValueError as error:
				self.emit_warning(view, "Error in path rendering", str(error), node)
				raise
				return
	
	@staticmethod
	def __draw_rounded_rectangle(ctx, x, y, w, h, rx, ry):
		r = (rx + ry) / 2 # TODO: non-symmetric rounded corners
		ctx.new_sub_path()
		ctx.arc(x + r, y + r, r, radians(180), radians(270))
		ctx.line_to(x + w - r, y)
		ctx.arc(x + w - r, y + r, r, radians(-90), radians(0))
		ctx.line_to(x + w, y + h - r)
		ctx.arc(x + w - r, y + h - r, r, radians(0), radians(90))
		ctx.line_to(x + r, y + h)
		ctx.arc(x + r, y + h - r, r, radians(90), radians(180))
		ctx.line_to(x, y + r)
		ctx.close_path()
	
	@staticmethod
	def __draw_arc(ctx, start_x, start_y, end_x, end_y, radius_x, radius_y, alpha_angle, large_arc_flag, sweep_flag):
		chord_x = math.cos(alpha_angle) * (start_x - end_x) + math.sin(alpha_angle) * (start_y - end_y)
		chord_y = -math.sin(alpha_angle) * (start_x - end_x) + math.cos(alpha_angle) * (start_y - end_y)
		
		mid_x = chord_x / radius_x
		mid_y = chord_y / radius_y
		mid_z = math.hypot(mid_x, mid_y)
		
		sin_mid_angle = -mid_x / mid_z
		cos_mid_angle = mid_y / mid_z
		
		sin_ext_angle_vals = []
		if abs(sin_mid_angle) > 0.001:
			sin_ext_angle_vals.append(mid_x / (-2* sin_mid_angle))
		if abs(cos_mid_angle) > 0.001:
			sin_ext_angle_vals.append(mid_y / (2 * cos_mid_angle))
		sin_ext_angle = sum(sin_ext_angle_vals) / len(sin_ext_angle_vals)
		
		mid_angle = math.atan2(-mid_x, mid_y)
		sin_ext_angle = math.copysign(min(abs(sin_ext_angle), 1), sin_ext_angle)
		ext_angle = math.asin(sin_ext_angle)
		if sweep_flag != large_arc_flag: ext_angle = math.copysign(pi, ext_angle) - ext_angle
		
		start_angle = mid_angle + ext_angle
		end_angle = mid_angle - ext_angle
		
		try:
			less_x = chord_x / (radius_x * (math.cos(start_angle) -  math.cos(end_angle)))
		except ZeroDivisionError:
			less_x = 0
		
		try:
			less_y = chord_y / (radius_y * (math.sin(start_angle) -  math.sin(end_angle)))
		except ZeroDivisionError:
			less_y = 0
		less = max(less_x, less_y)
		
		if less > 1:
			radius_x *= less
			radius_y *= less
		
		center_x = (start_x + end_x - radius_x * (math.cos(start_angle + alpha_angle) + math.cos(end_angle + alpha_angle))) / 2
		center_y = (start_y + end_y - radius_y * (math.sin(start_angle + alpha_angle) + math.sin(end_angle + alpha_angle))) / 2
		
		#start_angle_scaled = math.tan((radius_y / radius_x) * math.atan(start_angle - alpha_angle))
		#end_angle_scaled = math.tan((radius_y / radius_x) * math.atan(end_angle - alpha_angle))
		
		ctx.save()
		ctx.translate(center_x, center_y)
		ctx.rotate(alpha_angle)
		ctx.scale(radius_x, radius_y)
		ctx.translate(-center_x, -center_y)
		if sweep_flag:
			ctx.arc(center_x, center_y, 1, start_angle, end_angle)
		else:
			ctx.arc_negative(center_x, center_y, 1, start_angle, end_angle)
		ctx.restore()
	
	def __render_image(self, view, document, ctx, box, node):
		"Render external image."
		
		try:
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
		except AttributeError:
			href = node.attrib.get('href', None)
		
		if not href:
			self.emit_warning(view, "Image without href.", node.tag, node)
			return []
		
		url = self.resolve_url(href, self.get_document_url(document))
		
		left, top, width, height = box
		x = self.__units(view, node.attrib.get('x', 0), percentage=width)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height)
		w = self.__units(view, node.attrib.get('width', width), percentage=width)
		h = self.__units(view, node.attrib.get('height', height), percentage=height)
		box = x, y, w, h
		
		transform = node.attrib.get('transform', None)
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, transform)
		
		try:
			image = self.get_document(url)
			nop = self.draw_image(view, image, ctx, box)
		except (IndexError, KeyError):
			self.emit_warning(view, f"Could not fetch url.", url, node)
			nop = []
		except NotImplementedError:
			self.emit_warning(view, f"Unsupported image format.", type(image), node)
			nop = []
		finally:
			if transform:
				ctx.restore()
		
		if nop and view.pointer:
			if ctx.in_clip(*ctx.device_to_user(*view.pointer)):
				nop.insert(0, node)
		return nop
	
	def __render_foreign_object(self, view, document, ctx, box, node):
		"Render <foreignObject/>. Rendering of the child node must be implemented separately."
		
		left, top, width, height = box
		x = self.__units(view, node.attrib.get('x', 0), percentage=width)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height)
		w = self.__units(view, node.attrib.get('width', width), percentage=width)
		h = self.__units(view, node.attrib.get('height', height), percentage=height)
		box = x, y, w, h
		
		transform = node.attrib.get('transform', None)
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, transform)
		
		hover_nodes = []

		ctx.rectangle(x, y, w, h)
		ctx.set_source_rgb(0, 0, 1)
		ctx.set_line_width(1)
		ctx.stroke()		
		
		try:
			for child in node:
				try:
					ctx.save()
					hover_subnodes = self.draw_image(view, child, ctx, box)
					hover_nodes.extend(hover_subnodes)
				except NotImplementedError:
					self.emit_warning(view, f"Unsupported foreign object.", child.tag, child)
				finally:
					ctx.save()
		finally:
			if transform:
				ctx.restore()
		
		if hover_nodes and view.pointer:
			if ctx.in_clip(*ctx.device_to_user(*view.pointer)):
				hover_nodes.insert(0, node)
		
		return hover_nodes



'''
		if debug_ctx:
			debug_ctx.save()
			debug_ctx.translate(center_x, center_y)
			debug_ctx.rotate(alpha_angle)
			debug_ctx.scale(radius_x, radius_y)
			debug_ctx.move_to(-1, 0)
			debug_ctx.line_to(1, 0)
			debug_ctx.save()
			debug_ctx.identity_matrix()
			debug_ctx.set_line_width(3)
			debug_ctx.set_source_rgb(1, 1, 0)
			debug_ctx.stroke()
			debug_ctx.restore()
			debug_ctx.move_to(0, -1)
			debug_ctx.line_to(0, 1)
			debug_ctx.save()
			debug_ctx.identity_matrix()
			debug_ctx.set_line_width(3)
			debug_ctx.set_source_rgb(0, 1, 1)
			debug_ctx.stroke()
			debug_ctx.restore()
			debug_ctx.restore()
			
			debug_ctx.arc(start_x, start_y, 2, 0, 2 * pi)
			debug_ctx.set_source_rgb(1, 0, 0)
			debug_ctx.fill()
			
			debug_ctx.arc(end_x, end_y, 2, 0, 2 * pi)
			debug_ctx.set_source_rgb(0, 0, 1)
			debug_ctx.fill()
			
			debug_ctx.arc(center_x, center_y, 4, 0, 2 * pi)
			debug_ctx.set_source_rgb(0, 1, 0)
			debug_ctx.fill()
			
			debug_ctx.save()
			debug_ctx.move_to(center_x - radius_x * math.cos(alpha_angle), center_y - radius_x * math.sin(alpha_angle))
			debug_ctx.line_to(center_x + radius_x * math.cos(alpha_angle), center_y + radius_x * math.sin(alpha_angle))
			debug_ctx.identity_matrix()
			debug_ctx.set_line_width(0.5)
			debug_ctx.set_source_rgb(1, 0, 0)
			debug_ctx.stroke()
			debug_ctx.restore()
			
			debug_ctx.save()
			debug_ctx.move_to(center_x - radius_y * math.cos(alpha_angle + pi / 2), center_y - radius_y * math.sin(alpha_angle + pi / 2))
			debug_ctx.line_to(center_x + radius_y * math.cos(alpha_angle + pi / 2), center_y + radius_y * math.sin(alpha_angle + pi / 2))
			debug_ctx.identity_matrix()
			debug_ctx.set_line_width(0.5)
			debug_ctx.set_source_rgb(0, 0, 1)
			debug_ctx.stroke()
			debug_ctx.restore()
		
		#try:
		#	assert mid_x / (-2* sin_mid_angle) == mid_y / (2 * cos_mid_angle) + epsilon, "identity 1"
		#	assert mid_x / mid_y == -math.tan((start_angle + end_angle) / 2) + epsilon, "identity 2"
		#	#assert start_x == center_x + radius_x * math.cos(start_angle) + epsilon, "identity 5"
		#	#assert start_y == center_y + radius_y * math.sin(start_angle) + epsilon, "identity 6"
		#	#assert end_x == center_x + radius_x * math.cos(end_angle) + epsilon, "identity 7"
		#	#assert end_y == center_y + radius_y * math.sin(end_angle) + epsilon, "identity 8"
		#except ZeroDivisionError:
		#	pass


class _legacy:
	def __render_xml(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Generic dispatcher for rendering an XML node."
		
		if not isinstance(node.tag, str):
			pass
		elif node.tag in [f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in ('defs', 'title', 'desc', 'metadata', 'style', 'linearGradient', 'radialGradient', 'script', 'symbol', 'animate', 'filter')]:
			pass
		elif node.tag == f'{{{self.xmlns_sodipodi}}}namedview': # a very common nonstandard tag in svg documents created by inkscape
			pass
		elif node.tag == f'{{{self.xmlns_svg}}}use':
			return self.__render_use(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag == f'{{{self.xmlns_svg}}}svg':
			return self.__render_svg(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag == f'{{{self.xmlns_svg}}}g':
			return self.__render_group(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag == f'{{{self.xmlns_svg}}}switch':
			return self.__render_switch(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag == f'{{{self.xmlns_svg}}}a':
			return self.__render_anchor(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag == f'{{{self.xmlns_svg}}}image':
			return self.__render_image(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag == f'{{{self.xmlns_svg}}}foreignObject':
			return self.__render_foreign_object(view, ctx, box, node, ancestors, current_url, level, draw)
		elif node.tag in [f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in ('polygon', 'line', 'ellipse', 'circle', 'rect', 'path', 'text')]:
			return self.__render_shape(view, ctx, box, node, ancestors, current_url, level, draw)
		else:
			self.emit_warning(view, f"unsupported tag: {node.tag}", node.tag, node)
		
		return []
	
	def __render_use(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render a <use/> element, referencing another one."
		
		href = self.resolve_url(node.attrib[f'{{{self.xmlns_xlink}}}href'], current_url)
		original = self.get_document(href)
		if original == None:
			self.emit_warning(view, f"Ref not found: {href}", href, node)
			return []
		else:
			original = original.getroot()
		
		target = OverlayElement()
		target.original = original
		if original.tag == f'{{{self.xmlns_svg}}}symbol':
			target.tag = f'{{{self.xmlns_svg}}}g'
			target.fromsymbol = True
		else:
			target.tag = original.tag
		target.attrib = dict(original.attrib)
		target.attrib.update(dict((_k, _v) for (_k, _v) in node.attrib.items() if _k not in [f'{{{self.xmlns_xlink}}}href', 'transform']))
		target.extend(original)
		target.text = original.text
		target.tail = original.tail
		target.parent = node
		
		if 'transform' in node.attrib:
			target.attrib['transform'] = node.attrib['transform'] + target.attrib.get('transform', '')
		
		return self.__render_xml(view, ctx, box, target, ancestors, current_url, level, draw)
	
	def __render_switch(self, view, ctx, box, node, ancestors, current_url, level, draw):
		for child in node:
			if not isinstance(child.tag, str): continue
			required_features = frozenset(child.attrib.get('requiredFeatures', '').strip().split())
			required_extensions = frozenset(child.attrib.get('requiredExtensions', '').strip().split())
			if required_features <= self.supported_features and required_extensions <= self.supported_extensions:
				return self.__render_xml(view, ctx, box, child, ancestors + [node], current_url, level, draw)
		return []
	
	def __render_anchor(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render a link. Emits tag_begin()/tag_end() calls on the context."
		
		try:
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
			ctx.tag_begin('a', f'href=\'{href}\'')
		except AttributeError:
			pass
		
		nodes_under_pointer = self.__render_group(view, ctx, box, node, ancestors, current_url, level, draw)
		
		try:
			ctx.tag_end('a')
		except AttributeError:
			pass
		
		return nodes_under_pointer
	
	def __render_image(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render external image."
		
		href = node.attrib[f'{{{self.xmlns_xlink}}}href']
		url = self.resolve_url(href, current_url)
		
		left, top, width, height = box
		x = self.__units(view, node.attrib['x'], percentage=width)
		y = self.__units(view, node.attrib['y'], percentage=height)
		w = self.__units(view, node.attrib['width'], percentage=width)
		h = self.__units(view, node.attrib['height'], percentage=height)
		box = x, y, w, h
		
		#if pointer: pointer = pointer[0] - x, pointer[1] - y # TODO: user coordinates
		
		if 'transform' in node.attrib:
			ctx.save()
			self.__apply_transform(view, ctx, box, node, ancestors)
		
		try:
			image = self.get_document(self.resolve_url(url, current_url))
		except KeyError:
			nodes_under_pointer = [] # TODO: placeholder image
		else:
			nop = self.draw_image(view, image, ctx, box)
			if nop:
				nodes_under_pointer = [node]
			else:
				nodes_under_pointer = []
				
		if 'transform' in node.attrib:
			ctx.restore()
		
		#if nop:
		#	nodes_under_pointer.insert(0, node)
		#	if nodes_under_pointer[-1] == None:
		#		del nodes_under_pointer[-1]
		return nodes_under_pointer
	
	def __render_foreign_object(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render <foreignObject/>. Rendering of the child node must be implemented separately."
		
		nodes_under_pointer = []
		
		left, top, width, height = box
		
		pointer = draw
		if pointer:
			px, py = pointer
			if left <= px < left + width and top <= py < top + height:
				nodes_under_pointer.append(node)
		
		x = left + self.__units(view, node.get('x', 0), percentage=width)
		y = top + self.__units(view, node.get('y', 0), percentage=height)
		w = self.__units(view, node.get('width', width), percentage=width)
		h = self.__units(view, node.get('height', height), percentage=height)
		
		ancestors = ancestors + [node]
		ctx.save()
		for child in node:
			nodes_under_pointer += self.__render_xml(view, ctx, (x, y, w, h), child, ancestors, current_url, level+1, draw)		
		ctx.restore()
		
		return nodes_under_pointer
	
	def __render_svg(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render <svg/> element and its subelements, toplevel or nested."
		
		print("render svg", draw)
		
		assert not any(isinstance(_element, list) for _element in ancestors)
		
		if node.tag != f'{{{self.xmlns_svg}}}svg':
			self.emit_warning(view, "root element not 'svg'", node.tag, node)
			return []
		
		left, top, width, height = box
		
		ctx.save()
		
		if left or top:
			ctx.translate(left, top)
		
		try:
			svg_width = self.__units(view, node.attrib['width'], percentage=width)
		except KeyError:
			svg_width = width
		
		try:
			svg_height = self.__units(view, node.attrib['height'], percentage=height)
		except KeyError:
			svg_height = height
		
		try:
			vb_x, vb_y, vb_w, vb_h = node.attrib['viewBox'].split()
		except KeyError:
			viewbox_x = viewbox_y = 0
			viewbox_w = svg_width
			viewbox_h = svg_height
		else:
			viewbox_x = self.__units(view, vb_x, percentage=width)
			viewbox_y = self.__units(view, vb_y, percentage=height)
			viewbox_w = self.__units(view, vb_w, percentage=width)
			viewbox_h = self.__units(view, vb_h, percentage=height)
			
		x_scale = width / viewbox_w
		y_scale = height / viewbox_h
			
		x_scale = y_scale = min(x_scale, y_scale)
			
		ctx.scale(x_scale, y_scale)
		ctx.translate(-viewbox_x, -viewbox_y)
		
		ctx.rectangle(viewbox_x, viewbox_y, viewbox_w, viewbox_h)
		ctx.clip()
		
		nodes_under_pointer = self.__render_group(view, ctx, (viewbox_x, viewbox_y, viewbox_w, viewbox_h), node, ancestors, current_url, level, draw)
		
		ctx.restore()
		
		return nodes_under_pointer
	
	def __render_group(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render SVG <g/> element and its subelements."
		
		left, top, width, height = box
		
		if 'transform' in node.attrib:
			ctx.save()
			self.__apply_transform(view, ctx, box, node, ancestors)
		
		if level:
			try:
				x = self.__units(view, node.attrib['x'], percentage=width)
			except KeyError:
				x = 0
			
			try:
				y = self.__units(view, node.attrib['y'], percentage=height)
			except KeyError:
				y = 0
			
			if x or y:
				ctx.save()
				ctx.translate(x, y)
		
		if hasattr(node, 'fromsymbol') and node.fromsymbol:
			ctx.rectangle(0, 0, width - left, height - top) # TODO: width and height attributes, box attribute
			pointer = draw
			if pointer:
				px, py = ctx.device_to_user(*pointer)
				pointer_yes = ctx.in_fill(px, py)
			else:
				pointer_yes = False
			ctx.clip()
		else:
			pointer_yes = True
		
		nodes_under_pointer = []
		ancestors = ancestors + [node]
		for child in node:
			nodes_under_pointer += self.__render_xml(view, ctx, box, child, ancestors, current_url, level+1, draw)
		
		if not pointer_yes:
			nodes_under_pointer = []
		
		if 'transform' in node.attrib:
			ctx.restore()
		
		if level and (x or y):
			ctx.restore()
		
		if nodes_under_pointer:
			nodes_under_pointer.insert(0, node)
		
		return nodes_under_pointer
	
	def __render_shape(self, view, ctx, box, node, ancestors, current_url, level, draw):
		"Render one of SVG shape elements: polygon, line, ellipse, circle, rect, path, text."
		
		left, top, width, height = box
		
		document = ancestors[0]
		
		params_found = False
		is_visible, has_stroke, has_fill, pointer_events = None, None, None, None
		if (draw is not None):
			try:
				is_visible, has_stroke, has_fill, pointer_events = document.__rendering_params_cache[node]
			except AttributeError:
				document.__rendering_params_cache = dict()
			except KeyError:
				pass
			else:
				params_found = True
			
			all_params_found = not any(_p is None for _p in [is_visible, has_stroke, has_fill, pointer_events])
		else:
			all_params_found = False
		
		try:
			filter_ = node.attrib['filter']
		except KeyError:
			filter_ = None
		
		if not params_found or is_visible is None:
			try:
				visibility = self.__search_attrib(view, node, ancestors, 'visibility')
			except KeyError:
				visibility = 'visible'
			
			is_visible = visibility not in ('hidden', 'collapse')
		
		# TODO: filters
		
		if filter_ and (draw is None) and is_visible:
			print("filter", filter_)
			margin = 10
			image = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(box[2] + 2 * margin + 1), int(box[3] + 2 * margin + 1))
			image_ctx = cairo.Context(image)
			#image_ctx.set_matrix(ctx.get_matrix())
			image_ctx.translate(-box[0] + margin, -box[1] + margin)
			old_ctx = ctx
			ctx = image_ctx
		
		
		if 'transform' in node.attrib:
			ctx.save()
			self.__apply_transform(view, ctx, box, node, ancestors)
		
		if node.tag == f'{{{self.xmlns_svg}}}rect':
			x, w, rx = [self.__units(view, node.attrib.get(_a, 0), percentage=width) for _a in ('x', 'width', 'rx')]
			y, h, ry = [self.__units(view, node.attrib.get(_a, 0), percentage=height) for _a in ('y', 'height', 'ry')]
			
			rx = max(rx, 0)
			ry = max(ry, 0)
			
			if rx or ry:
				self.__draw_rounded_rectangle(ctx, x, y, w, h, rx, ry)
			else:
				ctx.rectangle(x, y, w, h)
		
		elif node.tag == f'{{{self.xmlns_svg}}}circle':
			try:
				cx = self.__units(view, node.attrib['cx'], percentage=width)
			except KeyError:
				cx = 0
			
			try:
				cy = self.__units(view, node.attrib['cy'], percentage=height)
			except KeyError:
				cy = 0
			
			r = self.__units(view, node.attrib['r'], percentage=(width + height) / 2)
			ctx.arc(cx, cy, r, 0, 2*pi)
		
		elif node.tag == f'{{{self.xmlns_svg}}}ellipse':
			cx = self.__units(view, node.attrib['cx'], percentage=width)
			cy = self.__units(view, node.attrib['cy'], percentage=height)
			rx = self.__units(view, node.attrib['rx'], percentage=width)
			ry = self.__units(view, node.attrib['ry'], percentage=height)
			ctx.save()
			ctx.translate(cx, cy)
			ctx.scale(rx, ry)
			ctx.arc(0, 0, 1, 0, 2*pi)
			ctx.restore()
		
		elif node.tag == f'{{{self.xmlns_svg}}}line':
			x1 = self.__units(view, node.attrib['x1'], percentage=width)
			y1 = self.__units(view, node.attrib['y1'], percentage=height)
			x2 = self.__units(view, node.attrib['x2'], percentage=width)
			y2 = self.__units(view, node.attrib['y2'], percentage=height)
			ctx.move_to(x1, y1)
			ctx.line_to(x2, y2)
		
		elif node.tag == f'{{{self.xmlns_svg}}}polygon':
			points = node.attrib['points'].split()
			first = True
			for point in points:
				xs, ys, *_ = point.split(',')
				x = self.__units(view, xs, percentage=width)
				y = self.__units(view, ys, percentage=height)
				if first:
					ctx.move_to(x, y)
					first = False
				else:
					ctx.line_to(x, y)
			if not first:
				ctx.close_path()
		
		elif node.tag == f'{{{self.xmlns_svg}}}path':
			self.__draw_path(view, ctx, box, node, ancestors, level)
		
		elif node.tag == f'{{{self.xmlns_svg}}}text':
			self.__draw_text(view, ctx, box, node, ancestors, level, draw)
		
		else:
			self.emit_warning(view, f"tag {node.tag} not supported by this method", node.tag, node)
		
		if (not params_found or has_fill is None or has_stroke is None) or draw:
			has_fill, has_stroke = self.__apply_paint(view, ctx, box, node, ancestors, current_url, None if ((draw is None) and is_visible) else True)
		
		nodes_under_pointer = []
		pointer = draw
		if pointer:
			if not params_found or pointer_events is None:
				try:
					pointer_events = self.__search_attrib(view, node, ancestors, 'pointer-events')
				except KeyError:
					pointer_events = 'visiblePainted'
				else:
					if pointer_events in ('auto', 'inherit', 'initial', 'unset'):
						pointer_events = 'visiblePainted'
			
			if pointer_events == 'visiblePainted':
				check_fill = is_visible and has_fill
				check_stroke = is_visible and has_stroke
			elif pointer_events == 'visibleFill':
				check_fill = is_visible
				check_stroke = False
			elif pointer_events == 'visibleStroke':
				check_fill = False
				check_stroke = is_visible
			elif pointer_events == 'visible':
				check_fill = is_visible
				check_stroke = is_visible
			elif pointer_events == 'painted':
				check_fill = has_fill
				check_stroke = has_stroke
			elif pointer_events == 'fill':
				check_fill = True
				check_stroke = False
			elif pointer_events == 'stroke':
				check_fill = False
				check_stroke = True
			elif pointer_events == 'all':
				check_fill = True
				check_stroke = True
			elif pointer_events == 'none':
				check_fill = False
				check_stroke = False
			else: # same as 'visiblePainted'
				self.emit_warning(view, f"Unsupported value of attribute `visibility`: '{visibility}'", visibility, node)
				check_fill = is_visible and has_fill
				check_stroke = is_visible and has_stroke
			
			if (check_fill or check_stroke) and pointer:
				x, y = ctx.device_to_user(*pointer)
				if (check_stroke and ctx.in_stroke(x, y)) or (check_fill and ctx.in_fill(x, y)):
					nodes_under_pointer.append(node)
		
		ctx.new_path()
		
		if 'transform' in node.attrib:
			ctx.restore()
		
		
		if filter_ and (draw is None) and is_visible:
			image.flush()
			
			pil_filter = PIL.ImageFilter.GaussianBlur(10) # TODO: other filters
			
			data = PIL.Image.frombytes('RGBa', (image.get_width(), image.get_height()), bytes(image.get_data())).filter(pil_filter).tobytes()
			image = cairo.ImageSurface.create_for_data(bytearray(data), cairo.FORMAT_ARGB32, image.get_width(), image.get_height())
			
			ctx = old_ctx
			ctx.set_source_surface(image, -margin, -margin)
			ctx.rectangle(*box)
			ctx.fill()
			image.finish()
		
		if (draw is None) and not all_params_found:
			try:
				document.__rendering_params_cache[node] = is_visible, has_stroke, has_fill, pointer_events
			except AttributeError:
				document.__rendering_params_cache = dict()
				document.__rendering_params_cache[node] = is_visible, has_stroke, has_fill, pointer_events
		
		return nodes_under_pointer
	
	
	def __media_test(self, view):
		return False
	
	def __pseudoclass_test(self, view, pseudoclass, node):
		if pseudoclass == 'hover':
			return any((node is _under) or (hasattr(node, 'original') and hasattr(_under, 'original') and node.original is _under.original) for _under in view.nodes_under_pointer)
		return False
	
	def __search_attrib(self, view, node, ancestors, attrib):
		"Search for effective presentation attribute. This will either be an explicit XML attribute, or attribute of one of ancestors, or CSS value."
		
		#print("search_attrib", attrib)
		assert len(ancestors) >= 1
		assert self.is_xml_document(ancestors[0])
		document = ancestors[0]
		path = None
		
		if node is not None:
			path = '/'.join(_tag.tag for _tag in ancestors[1:] + [node])
			
			# inline style="..." attribute
			try:
				style = node.attrib['style']
			except (KeyError, AttributeError):
				pass
			else:
				css = self.get_document('data:text/css,' + url_quote('* {' + style + '}'))
				if css is not None:
					css_attrib = css.match_element([node], (lambda *args: False), (lambda *args: False), self.xmlns_svg)
					if attrib in css_attrib:
						return css_attrib[attrib]
			
			# regular stylesheet (<style/> tag or external)
			try:
				stylesheets = document.__stylesheets
			except AttributeError:
				stylesheets = list(self.__stylesheets(document))
				document.__stylesheets = stylesheets
			
			for stylesheet in stylesheets:
				css_attrs = stylesheet.match_element(ancestors[1:] + [node], (lambda *args: self.__media_test(view, *args)), (lambda *args: self.__pseudoclass_test(view, *args)), self.xmlns_svg)
				if attrib in css_attrs:
					return css_attrs[attrib]
			
			# XML attribute
			try:
				return node.attrib[attrib]
			except (KeyError, AttributeError):
				pass
		
		if len(ancestors) > 1:
			return self.__search_attrib(view, ancestors[-1], ancestors[:-1], attrib)
		else:
			raise KeyError(f"Attribute {attrib} not found in any of ancestors")
	
	@staticmethod
	def __warp_current_path(view, ctx, function):
		first = True
		for type_, points in ctx.copy_path():
			if type_ == cairo.PATH_MOVE_TO:
				if first:
					ctx.new_path()
					first = False
				x, y = function(*points)
				ctx.move_to(x, y)
			elif type_ == cairo.PATH_LINE_TO:
				x, y = function(*points)
				ctx.line_to(x, y)
			elif type_ == cairo.PATH_CURVE_TO:
				x1, y1, x2, y2, x3, y3 = points
				x1, y1 = function(x1, y1)
				x2, y2 = function(x2, y2)
				x3, y3 = function(x3, y3)
				ctx.curve_to(x1, y1, x2, y2, x3, y3)
			elif type_ == cairo.PATH_CLOSE_PATH:
				ctx.close_path()
	
	
	
	
	@classmethod
	def __total_text(cls, node, strip):
		total_text = []
		
		if node.text:
			txt = node.text
			if strip: txt = txt.strip()
			total_text.append(txt)
		
		for child in node:
			if child.tag != f'{{{cls.xmlns_svg}}}tspan': continue
			
			txt = cls.__total_text(child, strip)
			if strip: txt = txt.strip()
			total_text.append(txt)
			
			if child.tail:
				txt = child.tail
				if strip: txt = txt.strip()
				total_text.append(txt)
		
		return ' '.join(total_text)


'''



if __debug__ and __name__ == '__main__':
	from pathlib import Path
	from format.xml import XMLFormat, XMLDocument
	from format.css import CSSFormat, CSSDocument
	from format.null import NullFormat
	from download.data import DataDownload
	from urllib.parse import unquote as url_unquote
	
	class PseudoContext:
		def __init__(self, name):
			self.__name = name
			self.print_out = False
			self.balance = 0
		
		def save(self):
			if self.print_out: print(self.__name + '.save()')
			self.balance += 1
		
		def restore(self):
			if self.print_out: print(self.__name + '.restore()')
			self.balance -= 1
		
		def get_current_point(self):
			if self.print_out: print(self.__name + '.get_current_point()')
			return 0, 0
		
		def get_line_width(self):
			if self.print_out: print(self.__name + '.get_line_width()')
			return 1
		
		def copy_path(self):
			if self.print_out: print(self.__name + '.copy_path()')
			return [(cairo.PATH_MOVE_TO, (0, 0))]
		
		def path_extents(self):
			if self.print_out: print(self.__name + '.path_extents()')
			return 0, 0, 1, 1
		
		def text_extents(self, txt):
			if self.print_out: print(self.__name + f'.text_extents("{txt}")')
			return cairo.Rectangle(0, 0, len(txt), 1)
		
		def set_dash(self, dashes, offset):
			if self.print_out: print(self.__name + '.set_dash(', repr(dashes), ',', repr(offset), ')')
			pass
		
		def device_to_user(self, x, y):
			if self.print_out: print(self.__name + f'.device_to_user("{x}, {y}")')
			return x, y
		
		def __getattr__(self, attr):
			if self.print_out: return lambda *args: print(self.__name + '.' + attr + str(args))
			return lambda *args: None
	
	class SVGRenderModel(SVGFormat, CSSFormat, XMLFormat, DataDownload, NullFormat):
		def scan_document_links(self, document):
			if SVGFormat.is_svg_document(self, document):
				return SVGFormat.scan_document_links(self, document)
			elif CSSFormat.is_css_document(self, document):
				return CSSFormat.scan_document_links(self, document)
			elif XMLFormat.is_xml_document(self, document):
				return XMLFormat.scan_document_links(self, document)
			elif NullFormat.is_null_document(self, document):
				return NullFormat.scan_document_links(self, document)
			else:
				raise NotImplementedError(f"Could not scan links in unsupported document type: {type(document)}")
		
		def create_document(self, data, mime_type):
			if mime_type == 'application/xml':
				return XMLFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/css':
				return CSSFormat.create_document(self, data, mime_type)
			elif mime_type == 'image/svg':
				return SVGFormat.create_document(self, data, mime_type)
			else:
				raise NotImplementedError("Could not create unsupported document type.")
		
		def resolve_url(self, rel_url, base_url):
			return rel_url
		
		def emit_warning(self, view, message, url, node):
			print(message, node.attrib)
		
		def is_svg_document(self, document):
			return hasattr(document, 'getroot')
		
		def get_document_url(self, document):
			return ''
		
		def get_document(self, url):
			if url.startswith('#'):
				return XMLDocument(self.tree.findall(f".//*[@id='{url[1:]}']")[0])
			elif url.startswith('data:text/css'):
				return CSSDocument(url_unquote(url[14:]).encode('utf-8'))
			return None
			#raise NotImplementedError("Could not fetch unsupported url scheme: " + url)
		
		def draw_image(self, view, document, ctx, box):
			r = super().draw_image(view, document, ctx, box)
			if r is NotImplemented:
				return []
			return r
	
	class PseudoView:
		def __init__(self):
			self.pointer = 10, 10
			self.viewport_width = 2000
			self.viewport_height = 1500
			self.screen_dpi = 96
			self.nodes_under_pointer = []
	
	
	for filepath in Path('gfx').iterdir():
		if filepath.suffix != '.svg': continue
		#print()
		#print(filepath)
		ctx = PseudoContext(f'Context("{str(filepath)}")')
		rnd = SVGRenderModel()
		view = PseudoView()
		
		document = rnd.create_document(filepath.read_bytes(), 'image/svg')
		l = list(rnd.scan_document_links(document))
		
		rnd.tree = document
		rnd.draw_image(view, document, ctx, (0, 0, 1024, 768))
		
		assert ctx.balance == 0

