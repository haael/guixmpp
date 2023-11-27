#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'SVGImage',


if __name__ == '__main__':
	import sys
	del sys.path[0]


import re
import math
from enum import Enum
import cairo
from collections import defaultdict, namedtuple
from itertools import chain, starmap
from urllib.parse import quote as url_quote
from colorsys import hls_to_rgb

import PIL.Image, PIL.ImageFilter

import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

from format.xml import XMLDocument, OverlayElement


try:
	distance = math.dist
except AttributeError:
	def distance(a, b):
		return math.sqrt(sum((_a - _b)**2 for (_a, _b) in zip(a, b)))


class NotANumber(BaseException):
	def __init__(self, original):
		self.original = original


class SVGImage:
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
		'yellowgreen': '#9ACD32'
	}
	
	def create_document(self, data, mime_type):
		if mime_type == 'image/svg+xml' or mime_type == 'image/svg':
			document = self.create_document(data, 'application/xml')
			
			if document.getroot().tag == 'svg': # document without namespace
				document.getroot().attrib['xmlns'] = self.xmlns_svg
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			if self.is_svg_document(document):
				return document
			else:
				msg = []
				if self.is_xml_document(document):
					try:
						root = document.getroot()
					except:
						msg.append("root:no")
					else:
						msg.append("root:yes")
						msg.append("tag:" + repr(root.tag))
						if root.tag.startswith('{' + self.xmlns_svg + '}'):
							msg.append("SVG:yes")
						else:
							msg.append("SVG:no")
				else:
					msg.append("XML:no")
				raise ValueError("Not an SVG document. " + "; ".join(msg))
		else:
			return NotImplemented
	
	def is_svg_document(self, document):
		if self.is_xml_document(document):
			return document.getroot().tag.startswith('{' + self.xmlns_svg + '}')
		else:
			try:
				return document.tag.startswith('{' + self.xmlns_svg + '}')
			except AttributeError:
				return False
	
	def scan_document_links(self, document):
		"Yield all links referenced by the SVG document, including `data:` links."
		
		if self.is_svg_document(document):
			def links():
				yield from document.scan_stylesheets()
				yield from self.__xlink_hrefs(document)
				yield from self.__data_internal_links(self.__style_attrs(document))
				yield from self.__data_internal_links(self.__style_tags(document))
				#yield from self.__script_tags(document)
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
		if 'style' in document.getroot().attrib:
			style = '* {' + document.getroot().attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
		
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
	
	def __script_tags(self, document):
		for scripttag in document.findall(f'.//{{{self.xmlns_svg}}}script'):
			try:
				mime = styletag.attrib['type'].lower()
			except KeyError:
				mime = 'text/javascript'
			script = scripttag.text
			yield f'data:{mime},' + url_quote(script)
	
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
		
		if hasattr(document, 'getroot'):
			node = document.getroot()
		else:
			node = document
			document = XMLDocument(node.getroottree().getroot())
		
		try:
			del view.__attr_cache
		except AttributeError:
			pass
		
		em_size = 12
		
		if any(node.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__shape_tags):
			self.__render_shape(view, document, ctx, box, node, em_size, None)
		elif node.tag == f'{{{self.xmlns_svg}}}text':
			self.__render_text(view, document, ctx, box, node, em_size, None)
		elif any(node.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__group_tags):
			self.__render_group(view, document, ctx, box, node, em_size, None)
		elif node.tag == f'{{{self.xmlns_svg}}}image':
			self.__render_image(view, document, ctx, box, node, em_size, None)
		elif node.tag == f'{{{self.xmlns_svg}}}foreignObject':
			self.__render_foreign_object(view, document, ctx, box, node, em_size, None)
		else:
			self.emit_warning(view, f"Unsupported node: {node.tag}", node)	
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_svg_document(document):
			return NotImplemented
		
		if hasattr(document, 'getroot'):
			node = document.getroot()
		else:
			node = document
			document = XMLDocument(node.getroottree().getroot())
		
		em_size = 12
		
		if any(node.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__shape_tags):
			return self.__render_shape(view, document, ctx, box, node, em_size, (px, py))
		elif node.tag == f'{{{self.xmlns_svg}}}text':
			return self.__render_text(view, document, ctx, box, node, em_size, (px, py))
		elif any(node.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__group_tags):
			return self.__render_group(view, document, ctx, box, node, em_size, (px, py))
		elif node.tag == f'{{{self.xmlns_svg}}}image':
			return self.__render_image(view, document, ctx, box, node, em_size, (px, py))
		elif node.tag == f'{{{self.xmlns_svg}}}foreignObject':
			return self.__render_foreign_object(view, document, ctx, box, node, em_size, (px, py))
		else:
			self.emit_warning(view, f"Unsupported node: {node.tag}", node)
			return []
	
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
	__shape_tags = frozenset(['polygon', 'line', 'ellipse', 'circle', 'rect', 'path', 'polyline'])
	__skip_tags = frozenset(['defs', 'title', 'desc', 'metadata', 'style', 'linearGradient', 'radialGradient', 'pattern', 'script', 'animate', 'filter', 'switch'])
	
	def __media_test(self, view):
		return False
	
	def __pseudoclass_test(self, view, pseudoclass, node):
		if pseudoclass == 'hover' and hasattr(self, 'get_pointed'):
			pointed = self.get_pointed(view)
			if pointed is not None:
				#if self.are_nodes_ordered(node, pointed):
				#	a = []
				#	p = pointed
				#	if isinstance(p, OverlayElement):
				#		a.append('OOO')
				#	while p is not None:
				#		
				#		n = 0 if p.getparent() is None else p.getparent().index(p.orig_one()) if hasattr(p, 'orig_one') else p.getparent().index(p)
				#		#n = 0
				#		a.insert(0, p.tag.split('}')[-1] + ('[' + str(n) + ']') + (''.join('.' + _class for _class in p.attrib['class'].split(' ')) if 'class' in p.attrib else '') + ('#' + p.attrib['id'] if 'id' in p.attrib else '') + ('*' if (p == node) else ''))
				#		p = p.getparent()
				#	print("hover:", a)
				#print(node.tag, node.attrib, pointed.tag, pointed.attrib, self.are_nodes_ordered(node, pointed))
				return self.are_nodes_ordered(node, pointed)
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
	
	def __get_attribute(self, view, document, ctx, box, node, em_size, attr, default):
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
		
		#if node and node.tag == '{http://www.w3.org/2000/svg}tspan' and attr == 'fill':
		#	print("search attribute", node.tag, node.attrib.get('class', None), attr)
		
		if node is not None:
			try:
				#view.__attr_cache[node][attr]
				return view.__attr_cache[node][attr]
			except KeyError:
				pass
			except AttributeError:
				view.__attr_cache = defaultdict(dict)
						
			"inline style='...' attribute"
			try:
				style = node.attrib['style']
			except (KeyError, AttributeError):
				pass
			else:
				css = self.get_document('data:text/css,' + url_quote('* {' + style + '}'))
				css_attrs = css.match_element(node, (lambda *args: False), (lambda *args: False), self.xmlns_svg)
				if attr in css_attrs:
					view.__attr_cache[node][attr] = css_attrs[attr][0]
					return css_attrs[attr][0]
			
			"regular stylesheet (<style/> tag or external)"
			try:
				stylesheets = document.__stylesheets
			except AttributeError:
				stylesheets = list(self.__stylesheets(document))
				document.__stylesheets = stylesheets
			
			css_value = None
			css_priority = None
			
			for stylesheet in stylesheets:
				css_attrs = stylesheet.match_element(node, (lambda *args: self.__media_test(view, *args)), (lambda *args: self.__pseudoclass_test(view, *args)), self.xmlns_svg)
				if attr in css_attrs:
					value, priority = css_attrs[attr]
					#print(" attrs:", node.tag, node.attrib, attr, value, repr(priority), css_priority)
					if css_priority == None or priority >= css_priority:
						css_value = value
						css_priority = priority
			
			if css_value is not None:
				#print("attr:", node.tag, node.attrib.get('class', '-'), attr, css_value)
				view.__attr_cache[node][attr] = css_value
				return css_value
			
			"XML attribute"
			try:
				view.__attr_cache[node][attr] = node.attrib[attr]
				return node.attrib[attr]
			except (KeyError, AttributeError):
				pass
		
		parent = node.getparent()
		if parent is not None:
			result = self.__search_attribute(view, document, parent, attr)
			if node is not None:
				view.__attr_cache[node][attr] = result
			return result
		else:
			raise KeyError(f"Attribute {attr} not found in any of ancestors")
	
	def __render_group(self, view, document, ctx, box, node, em_size, pointer): # FIXME: improve speed for deep documents
		"Render SVG group element and its subelements."
		
		#print("render_group", node.tag)
		
		em_size = self.__font_size(view, document, ctx, box, node, em_size)
		
		display = self.__get_attribute(view, document, ctx, box, node, em_size, 'display', 'block').lower()
		visibility = self.__get_attribute(view, document, ctx, box, node, em_size, 'visibility', 'visible').lower()
		
		if visibility == 'collapse' or display == 'none':
			return defaultdict(list)
		
		left, top, width, height = box
		
		transform = node.attrib.get('transform', None)
		
		x = self.__units(view, node.attrib.get('x', 0), percentage=width, em_size=em_size)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height, em_size=em_size)
		
		if transform or ((node.getparent() is not None) and (x or y)) or node.tag == f'{{{self.xmlns_svg}}}svg' or node.tag == f'{{{self.xmlns_svg}}}symbol':
			ctx.save()
		
		if node.tag == f'{{{self.xmlns_svg}}}svg':
			if (left or top) and (node.getparent() is None):
				ctx.translate(left, top)
			
			svg_width = self.__units(view, node.attrib.get('width', width), percentage=width, em_size=em_size)
			svg_height = self.__units(view, node.attrib.get('height', height), percentage=height, em_size=em_size)
			
			try:
				vb_x, vb_y, vb_w, vb_h = node.attrib.get('viewBox', None).split()
			except AttributeError:
				viewbox_x = x
				viewbox_y = y
				viewbox_w = svg_width
				viewbox_h = svg_height
			else:
				# TODO: correct calculations
				viewbox_x = self.__units(view, vb_x, percentage=width, em_size=em_size)
				viewbox_y = self.__units(view, vb_y, percentage=height, em_size=em_size)
				viewbox_w = self.__units(view, vb_w, percentage=width, em_size=em_size)
				viewbox_h = self.__units(view, vb_h, percentage=height, em_size=em_size)
			
			if (node.getparent() is None):
				x_scale = width / viewbox_w
				y_scale = height / viewbox_h
				
				x_scale = y_scale = min(x_scale, y_scale)
				ctx.translate((width - x_scale * viewbox_w) / 2, (height - y_scale * viewbox_h) / 2)
				ctx.scale(x_scale, y_scale)
				ctx.translate(-viewbox_x, -viewbox_y)
			else:
				if 'width' not in node.attrib:
					svg_width = viewbox_w
				if 'height' not in node.attrib:
					svg_height = viewbox_h
				
				x_scale = svg_width / viewbox_w
				y_scale = svg_height / viewbox_h					
				x_scale = y_scale = min(x_scale, y_scale)
				
				ctx.scale(x_scale, y_scale)
				#ctx.translate(-viewbox_x, -viewbox_y)
			
			box = viewbox_x, viewbox_y, viewbox_w, viewbox_h
			
			ctx.rectangle(*box)
			ctx.clip()
		
		left, top, width, height = box
		
		if transform:
			self.__apply_transform(view, document, ctx, box, node, em_size, transform)
		
		if (node.getparent() is not None) and (x or y):
			ctx.translate(x, y)
		
		if node.tag == f'{{{self.xmlns_svg}}}symbol':
			ctx.rectangle(0, 0, width - left, height - top) # TODO: width and height attributes, box attribute
			ctx.clip()
		
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
						self.emit_warning(view, f"Required features not satisfied.", child)
			
			if any(child.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__skip_tags):
				pass
			
			elif any(child.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__shape_tags):
				hover_subnodes = self.__render_shape(view, document, ctx, box, child, em_size, pointer)
				hover_nodes.extend(hover_subnodes)
			
			elif child.tag == f'{{{self.xmlns_svg}}}text':
				hover_subnodes = self.__render_text(view, document, ctx, box, child, em_size, pointer)
				hover_nodes.extend(hover_subnodes)
			
			elif any(child.tag == f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in self.__group_tags):
				hover_subnodes = self.__render_group(view, document, ctx, box, child, em_size, pointer)
				hover_nodes.extend(hover_subnodes)
			
			elif child.tag == f'{{{self.xmlns_svg}}}image':
				hover_subnodes = self.__render_image(view, document, ctx, box, child, em_size, pointer)
				hover_nodes.extend(hover_subnodes)
			
			elif child.tag == f'{{{self.xmlns_svg}}}foreignObject':
				hover_subnodes = self.__render_foreign_object(view, document, ctx, box, child, em_size, pointer)
				hover_nodes.extend(hover_subnodes)
			
			elif not child.tag.startswith(f'{{{self.xmlns_svg}}}'):
				try:
					if not pointer:
						self.draw_image(view, child, ctx, box)
					else:
						hover_subnodes = self.poke_image(view, child, ctx, box, *pointer)
						hover_nodes.extend(hover_subnodes)
				except NotImplementedError:
					self.emit_warning(view, f"Unsupported non-SVG element: {child.tag}", child)
			
			else:
				self.emit_warning(view, f"Unsupported SVG element: {child.tag}", child)
		
		if node.tag == f'{{{self.xmlns_svg}}}a':
			if hasattr(ctx, 'tag_end'):
				ctx.tag_end('a')
		
		if transform or ((node.getparent() is not None) and (x or y)) or node.tag == f'{{{self.xmlns_svg}}}svg' or node.tag == f'{{{self.xmlns_svg}}}symbol':
			ctx.restore()
		
		x, y, w, h = box
		#for idx, (rx, ry) in view.pointers.items():
		if pointer:
			rx, ry = pointer
			if x <= rx <= x + w and y <= ry <= y + h and ctx.in_clip(*ctx.device_to_user(rx, ry)):
				hover_nodes.insert(0, node)
		return hover_nodes
	
	def __render_shape(self, view, document, ctx, box, node, em_size, pointer):
		left, top, width, height = box
		
		display = self.__get_attribute(view, document, ctx, box, node, em_size, 'display', 'block').lower()
		visibility = self.__get_attribute(view, document, ctx, box, node, em_size, 'visibility', 'visible').lower()
		
		if visibility == 'collapse' or display == 'none':
			return defaultdict(list)
		
		#transform = self.__get_attribute(view, document, ctx, box, node, em_size, 'transform', None)
		transform = node.attrib.get('transform', None)
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, em_size, transform)
		
		if visibility != 'hidden':
			filter_ = self.__get_attribute(view, document, ctx, box, node, em_size, 'filter', None)
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
			x, w, rx = [self.__units(view, node.attrib.get(_a, 0), percentage=width, em_size=em_size) for _a in ('x', 'width', 'rx')]
			y, h, ry = [self.__units(view, node.attrib.get(_a, 0), percentage=height, em_size=em_size) for _a in ('y', 'height', 'ry')]
			
			rx = max(rx, 0)
			ry = max(ry, 0)
			
			if rx or ry:
				self.__draw_rounded_rectangle(ctx, x, y, w, h, rx, ry)
			else:
				ctx.rectangle(x, y, w, h)
		
		elif node.tag == f'{{{self.xmlns_svg}}}circle':
			cx = self.__units(view, node.attrib.get('cx', 0), percentage=width, em_size=em_size)
			cy = self.__units(view, node.attrib.get('cy', 0), percentage=height, em_size=em_size)
			r = self.__units(view, node.attrib['r'], percentage=(width + height) / 2, em_size=em_size)
			ctx.arc(cx, cy, r, 0, 2 * math.pi)
		
		elif node.tag == f'{{{self.xmlns_svg}}}ellipse':
			cx = self.__units(view, node.attrib.get('cx', 0), percentage=width, em_size=em_size)
			cy = self.__units(view, node.attrib.get('cy', 0), percentage=height, em_size=em_size)
			rx = self.__units(view, node.attrib['rx'], percentage=width, em_size=em_size)
			ry = self.__units(view, node.attrib['ry'], percentage=height, em_size=em_size)
			ctx.save()
			ctx.translate(cx, cy)
			ctx.scale(rx, ry)
			ctx.arc(0, 0, 1, 0, 2 * math.pi)
			ctx.restore()
		
		elif node.tag == f'{{{self.xmlns_svg}}}line':
			x1 = self.__units(view, node.attrib.get('x1', 0), percentage=width, em_size=em_size)
			y1 = self.__units(view, node.attrib.get('y1', 0), percentage=height, em_size=em_size)
			x2 = self.__units(view, node.attrib.get('x2', 0), percentage=width, em_size=em_size)
			y2 = self.__units(view, node.attrib.get('y2', 0), percentage=height, em_size=em_size)
			ctx.move_to(x1, y1)
			ctx.line_to(x2, y2)
		
		elif node.tag == f'{{{self.xmlns_svg}}}polygon' or node.tag == f'{{{self.xmlns_svg}}}polyline':
			x = self.__units(view, node.attrib.get('x', 0), percentage=width, em_size=em_size)
			y = self.__units(view, node.attrib.get('y', 0), percentage=height, em_size=em_size)
			
			rpoints = node.attrib['points'].split()
			points = []
			for rp in rpoints:
				for rpp in rp.split(','):
					srpp = rpp.strip()
					if srpp:
						points.append(srpp)
			first = True
			for n in range(len(points) // 2):
			#for point in points:
				#xs, ys, *_ = point.split(',')
				xs = points[2 * n]
				ys = points[2 * n + 1]
				kx = self.__units(view, xs, percentage=width, em_size=em_size)
				ky = self.__units(view, ys, percentage=height, em_size=em_size)
				if first:
					ctx.move_to(x + kx, y + ky)
					first = False
				else:
					ctx.line_to(x + kx, y + ky)
			
			if node.tag == f'{{{self.xmlns_svg}}}polygon' and not first:
				ctx.close_path()
		
		elif node.tag == f'{{{self.xmlns_svg}}}path':
			self.__draw_path(view, document, ctx, box, node, em_size)
		
		#elif node.tag == f'{{{self.xmlns_svg}}}text':
		#	self.__draw_text(view, document, ctx, box, node, em_size)
		
		else:
			self.emit_warning(view, f"Tag {node.tag} not supported by this method.", node)
		
		
		has_fill, has_stroke = self.__apply_paint(view, document, ctx, box, node, em_size, (visibility != 'hidden'))
		
		hover_nodes = []
		if pointer:
			px, py = ctx.device_to_user(*pointer)
			if ctx.in_clip(px, py):
				if ctx.in_fill(px, py) or ctx.in_stroke(px, py): # TODO: pointer events
					hover_nodes.append(node)
		
		ctx.new_path()
		
		if filter_:
			image.flush()
			
			pil_filter = PIL.ImageFilter.GaussianBlur(10) # TODO: other filters
			
			data = PIL.Image.frombytes('RGBa', (image.get_width(), image.get_height()), bytes(image.get_data())).filter(pil_filter).tobytes()
			image = cairo.ImageSurface.create_for_data(bytearray(data), cairo.FORMAT_ARGB32, image.get_width(), image.get_height())
			
			ctx = old_ctx
			ctx.set_source_surface(image, -margin, -margin)
			ctx.rectangle(*box)
			ctx.fill()
			#ctx.set_source_rgb(0, 0, 0)
			#ctx.stroke()
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
			self.emit_warning(view, f"Ref not found: {link}.", node)
			raise KeyError
		else:
			original = original.getroot()
		
		add_attrib = {}
		del_attrib = set()
		
		try:
			add_attrib[f'{{{self.xmlns_xlink}}}href'] = original.attrib[f'{{{self.xmlns_xlink}}}href']
		except KeyError:
			del_attrib.add(f'{{{self.xmlns_xlink}}}href')
		
		try:
			add_attrib['href'] = original.attrib['href']
		except KeyError:
			del_attrib.add('href')
		
		if 'transform' in node.attrib:
			add_attrib['transform'] = node.attrib['transform'] + original.attrib.get('transform', '')
		
		if 'gradientTransform' in node.attrib:
			add_attrib['gradientTransform'] = node.attrib['gradientTransform'] + original.attrib.get('gradientTransform', '')
		
		target = OverlayElement(node.getparent(), node, original, original.tag, add_attrib, del_attrib)
		#print("construct use:", node, original, target.attrib)
		
		return target
	
	def image_dimensions(self, view, document):
		"Return the SVG dimensions, that might depend on the view state."
		
		if not self.is_svg_document(document):
			return NotImplemented
		
		node = document.getroot()
		
		try:
			svg_width = self.__units(view, node.attrib['width'], percentage=self.get_viewport_width(view)) # TODO: default em size
		except KeyError:
			svg_width = self.get_viewport_width(view)
		
		try:
			svg_height = self.__units(view, node.attrib['height'], percentage=self.get_viewport_height(view)) # TODO: default em size
		except KeyError:
			svg_height = self.get_viewport_height(view)
		
		return svg_width, svg_height
	
	def __units(self, view, spec, percentage=None, percentage_origin=0, em_size=None):
		if not isinstance(spec, str):
			return spec
		
		spec = spec.strip()
		if not spec:
			return 0
		
		dpi = self.get_dpi(view)
		shift = 0
		
		if spec[-2:] == 'px':
			scale = 1
			value = spec[:-2]
		elif spec[-2:] == 'ex':
			if em_size == None:
				raise ValueError("`em_size` not specified.")
			scale = em_size * 1.2 # TODO
			value = spec[:-2]
		elif spec[-2:] == 'mm':
			scale = dpi / 25.4
			value = spec[:-2]
		elif spec[-2:] == 'cm':
			scale = dpi / 2.54
			value = spec[:-2]
		elif spec[-2:] == 'in':
			scale = dpi
			value = spec[:-2]
		elif spec[-2:] == 'pc':
			scale = dpi / 6
			value = spec[:-2]
		elif spec[-2:] == 'pt':
			scale = dpi / 72
			value = spec[:-2]
		elif spec[-2:] == 'em':
			if em_size == None:
				raise ValueError("`em_size` not specified.")
			scale = em_size * 2
			value = spec[:-2]
		elif spec[-1:] == 'Q':
			scale = dpi / (2.54 * 40)
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
	__re_translate1 = re.compile(fr'translate\s*\(\s*({__p_number}[a-zA-Z%]*)\s*\)')
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
	
	def __apply_transform(self, view, document, ctx, box, node, em_size, transform_string):
		left, top, width, height = box
		
		origin = node.attrib.get('transform-origin', '0 0').split()
		origin_x = self.__units(view, origin[0], percentage=width, em_size=em_size)
		origin_y = self.__units(view, origin[1], percentage=height, em_size=em_size)
		
		if origin_x or origin_y:
			ctx.translate(origin_x, origin_y)
		
		text = transform_string
		n = 0
		while n < len(text):
			match = self.__re_matrix.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				m0, m1, m2, m3, m4, m5 = map(self.__parse_float, list(match.groups()))
				transformation = cairo.Matrix(m0, m1, m2, m3, m4, m5)
				if (m0 or m1 or m2) and (m3 or m4 or m5): # TODO: hide view if matrix is singular
					ctx.transform(transformation)
				n = match.end()
				continue
			
			match = self.__re_translate1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				x, = [self.__units(view, _spec, em_size=em_size) for _spec in match.groups()]
				ctx.translate(x, 0)
				n = match.end()
				continue
			
			match = self.__re_translate.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				x, y = [self.__units(view, _spec, em_size=em_size) for _spec in match.groups()]
				ctx.translate(x, y)
				n = match.end()
				continue
			
			match = self.__re_scale1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				s, = map(self.__parse_float, list(match.groups()))
				if s: # TODO: hide view if matrix is singular
					ctx.scale(s, s)
				n = match.end()
				continue
			
			match = self.__re_scale2.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				sx, sy = map(self.__parse_float, list(match.groups()))
				if sx and sy: # TODO: hide view if matrix is singular
					ctx.scale(sx, sy)
				n = match.end()
				continue
			
			match = self.__re_rotate1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				r, = map(self.__parse_float, list(match.groups()))
				ctx.rotate(math.radians(r))
				n = match.end()
				continue
			
			match = self.__re_rotate3.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				r, cx, cy = map(self.__parse_float, list(match.groups()))
				ctx.translate(cx, cy)
				ctx.rotate(math.radians(r))
				ctx.translate(-cx, -cy)
				n = match.end()
				continue
			
			match = self.__re_skewX.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				a, = map(self.__parse_float, list(match.groups()))
				transformation = cairo.Matrix(1, 0, math.tan(math.radians(a)), 1, 0, 0)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			match = self.__re_skewY.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				a, = map(self.__parse_float, list(match.groups()))
				transformation = cairo.Matrix(1, math.tan(math.radians(a)), 0, 1, 0, 0)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			self.emit_warning(view, f"Unsupported transformation: {text[n:]}.", node)
			break
		
		if origin_x or origin_y:
			ctx.translate(-origin_x, -origin_y)
		
		return True
	
	def __apply_paint(self, view, document, ctx, box, node, em_size, draw):
		"Draw the current shape, applying fill and stroke. The path is preserved. Returns a pair of bool, indicating whether fill and stroke was non-transparent."
		
		has_fill = False
		ctx.save()
		if self.__apply_fill(view, document, ctx, box, node, em_size):
			has_fill = True
			if draw:
				ctx.fill_preserve()
		ctx.restore()
		
		has_stroke = False
		ctx.save()
		if self.__apply_stroke(view, document, ctx, box, node, em_size):
			has_stroke = True
			if draw:
				ctx.stroke_preserve()
		ctx.restore()
		
		return has_fill, has_stroke
	
	def __apply_fill(self, view, document, ctx, box, node, em_size):
		"Prepares the context to fill() operation, including setting color and fill rules."
		
		if not self.__apply_color(view, document, ctx, box, node, em_size, 'fill', 'fill-opacity', 'black'):
			return False
		
		fill_rule = self.__get_attribute(view, document, ctx, box, node, em_size, 'fill-rule', None)
		
		if fill_rule == 'evenodd':
			ctx.set_fill_rule(cairo.FillRule.EVEN_ODD)
		elif fill_rule == 'winding':
			ctx.set_fill_rule(cairo.FillRule.WINDING)
		elif fill_rule == 'nonzero':
			ctx.set_fill_rule(cairo.FillRule.WINDING)
			#self.emit_warning(view, f"Unsupported fill rule: {fill_rule}.", node) # TODO
		elif fill_rule == None:
			pass
		else:
			self.emit_warning(view, f"Unsupported fill rule: {fill_rule}.", node)
		
		return True
	
	def __apply_stroke(self, view, document, ctx, box, node, em_size):
		"Prepares the context to stroke() operation, including setting color and line parameters."
		
		if not self.__apply_color(view, document, ctx, box, node, em_size, 'stroke', 'stroke-opacity', 'none'):
			return False
		
		try:
			stroke_width = self.__units(view, str(self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-width', 1)), em_size=em_size)
		except ValueError:
			self.emit_warning(view, f"Unsupported stroke spec: {self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-width')}.", node)
			return False
		
		if stroke_width > 0:
			ctx.set_line_width(stroke_width)
		else:
			return False
		
		linecap = self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-linecap', 'butt')
		if linecap == 'butt' or linecap == 'null':
			ctx.set_line_cap(cairo.LINE_CAP_BUTT)
		elif linecap == 'round':
			ctx.set_line_cap(cairo.LINE_CAP_ROUND)
		elif linecap == 'square':
			ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
		else:
			self.emit_warning(view, f"Unsupported linecap `{linecap}`.", node)
		
		pathLength = self.__parse_float(node.attrib.get('pathLength', None))
		if pathLength is None:
			pathScale = 1
		else:
			pathScale = self.__get_current_path_length(ctx) / pathLength
		
		dasharray = self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-dasharray', 'none')
		if dasharray == 'none' or dasharray == 'null':
			ctx.set_dash([], 0)
		else:
			dashoffset = self.__parse_float(self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-dashoffset', 0)) * pathScale
			
			try:
				ctx.set_dash([self.__parse_float(dasharray) * pathScale + 0], dashoffset)
			except ValueError:
				try:
					dashes = [_x * pathScale for _x in map(self.__parse_float, dasharray.split())]
				except ValueError:
					dashes = [_x * pathScale for _x in map(self.__parse_float, dasharray.split(','))]
				ctx.set_dash(dashes, dashoffset)
		
		
		linejoin = self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-linejoin', 'miter')
		if linejoin == 'miter':
			ctx.set_line_join(cairo.LineJoin.MITER)
		elif linejoin == 'bevel':
			ctx.set_line_join(cairo.LineJoin.BEVEL)
		elif linejoin == 'round':
			ctx.set_line_join(cairo.LineJoin.ROUND)
		else:
			self.emit_warning(view, f"Unsupported linejoin `{linejoin}`.", node)
		
		miterlimit = self.__get_attribute(view, document, ctx, box, node, em_size, 'stroke-miterlimit', '4')
		try:
			miterlimit = self.__parse_float(miterlimit)
		except ValueError:
			self.emit_warning(view, f"Miter limit float parse error `{miterlimit}`.", node)
		else:
			ctx.set_miter_limit(miterlimit)
		
		return True
	
	def __parse_color(self, color, view, node):
		if color[0] == '#' and len(color) == 4:
			r, g, b = [int(_c, 16) / 15 for _c in color[1:]]
		
		elif color[0] == '#' and len(color) == 7:
			r, g, b = [int(_c, 16) / 255 for _c in (color[1:3], color[3:5], color[5:7])]
							
		elif color[:4] == 'rgb(' and color[-1] == ')':
			r, g, b = [max(0, min(1, (self.__parse_float(_c) / 255 if _c.strip()[-1] != '%' else self.__parse_float(_c.strip()[:-1]) / 100))) for _c in color[4:-1].split(',')]
		
		elif color[:4] == 'hsl(' and color[-1] == ')':
			cc = color[4:-1].split(',')
			
			h = max(0, min(360, (self.__parse_float(cc[0])))) / 360
			s = max(0, min(100, (self.__parse_float(cc[1] if cc[1][-1] != '%' else cc[1][:-1])))) / 100
			l = max(0, min(100, (self.__parse_float(cc[2] if cc[2][-1] != '%' else cc[2][:-1])))) / 100
			
			r, g, b = hls_to_rgb(h, l, s)
		
		else:
			self.emit_warning(view, f"Unsupported color specification: {color}.", node)
			return None
		
		return r, g, b
	
	def __apply_color(self, view, document, ctx, box, node, em_size, color_attr, opacity_attr, default_color):
		"Set painting source to the color identified by provided parameters."
		
		color = self.__get_attribute(view, document, ctx, box, node, em_size, color_attr, default_color).strip()
		target = node.getparent()
		while color in ('currentColor', 'inherit') and (target is not None):			
			if color == 'currentColor':
				color = self.__get_attribute(view, document, ctx, box, target, em_size, 'color', default_color).strip()
			elif color == 'inherit':
				color = self.__get_attribute(view, document, ctx, box, target, em_size, color_attr, default_color).strip()
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
		
		opacity = self.__get_attribute(view, document, ctx, box, node, em_size, opacity_attr, None)
		if opacity == 'null':
			a = None # None means 1 (full opacity), not 0 (full transparency)
		else:
			a = self.__parse_float(opacity)
		
		if a == 0:
			return False
		
		if color[:4] == 'url(' and color[-1] == ')':
			href = color.strip()[4:-1]
			if href[0] == '"' and href[-1] == '"': href = href[1:-1]
			return self.__apply_pattern(view, document, ctx, box, node, em_size, href)
			# TODO: transparency
		else:
			cc = self.__parse_color(color, view, node)
			if cc == None:
				return False
			else:
				r, g, b = cc
		
		try:
			if a == None:
				ctx.set_source_rgb(r, g, b)
			else:
				ctx.set_source_rgba(r, g, b, a)
		except UnboundLocalError:
			pass
		
		return True
	
	def __apply_pattern(self, view, document, ctx, box, node, em_size, url):
		"Set painting source to a pattern, i.e. a gradient, identified by url."
		
		current_url = self.get_document_url(document)
		href = self.resolve_url(url, current_url)
		target_doc = self.get_document(href)
		if target_doc == None:
			self.emit_warning(view, f"Color pattern ref not found: {href}.", node)
			return defaultdict(list)
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
				self.emit_warning(view, f"Unknown gradient units: {gradient_units}.", target)
			
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
					self.emit_warning(view, f"Ref not found: {href}.", node)
					return False
				else:
					next_gradient = next_gradient_doc.getroot()

					add_attrib = {}
					del_attrib = set()
					
					try:
						add_attrib[f'{{{self.xmlns_xlink}}}href'] = next_gradient.attrib[f'{{{self.xmlns_xlink}}}href']
					except KeyError:
						del_attrib.add(f'{{{self.xmlns_xlink}}}href')
					
					try:
						add_attrib['href'] = next_gradient.attrib['href']
					except KeyError:
						del_attrib.add('href')
					
					if 'transform' in orig_target.attrib:
						add_attrib['transform'] = orig_target.attrib['transform'] + next_gradient.attrib.get('transform', '')
					
					if 'gradientTransform' in orig_target.attrib:
						add_attrib['gradientTransform'] = orig_target.attrib['gradientTransform'] + next_gradient.attrib.get('gradientTransform', '')
					
					target = OverlayElement(orig_target.getparent(), orig_target, next_gradient, orig_target.tag, add_attrib, del_attrib)
			
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
					self.emit_warning(view, f"Invalid x1 specification in linear gradient: {target.attrib['x1']}.", target)
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
					self.emit_warning(view, f"Invalid y1 specification in linear gradient: {target.attrib['y1']}.", target)
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
					self.emit_warning(view, f"Invalid x2 specification in linear gradient: {target.attrib['x2']}.", target)
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
					self.emit_warning(view, f"Invalid y2 specification in linear gradient: {target.attrib['y2']}.", target)
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
					self.emit_warning(view, f"Invalid r specification in radial gradient: {target.attrib['r']}.", target)
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
					self.emit_warning(view, f"Invalid cx specification in linear gradient: {target.attrib['cx']}.", target)
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
					self.emit_warning(view, f"Invalid cy specification in linear gradient: {target.attrib['cy']}.", target)
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
					self.emit_warning(view, f"Invalid r specification in radial gradient: {target.attrib['fr']}.", target)
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
					self.emit_warning(view, f"Invalid fx specification in linear gradient: {target.attrib['fx']}.", target)
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
					self.emit_warning(view, f"Invalid cy specification in linear gradient: {target.attrib['fy']}.", target)
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
					self.emit_warning(view, f"Error in offset spec of a linear gradient: {colorstop.attrib['offset']}.", colorstop)
					offset = last_offset
				
				last_offset = offset
				stop_color = None
				stop_opacity = None
				
				stop_color = self.__get_attribute(view, document, ctx, box, colorstop, em_size, 'stop-color', None)
				if stop_color == None:
					self.emit_warning(view, "Stop color of linear gradient not found.", colorstop)
					continue
				
				stop_opacity = self.__parse_float(self.__get_attribute(view, document, ctx, box, colorstop, em_size, 'stop-opacity', None))
				
				if not stop_color or stop_color.lower() in ('none', 'transparent'):
					continue
				
				try:
					stop_color = self.web_colors[stop_color.lower()]
				except KeyError:
					pass
				
				cc = self.__parse_color(stop_color, view, node)
				if cc == None:
					continue
				else:
					r, g, b = cc
				
				if stop_opacity == None:
					gradient.add_color_stop_rgb(offset, r, g, b)
				else:
					gradient.add_color_stop_rgba(offset, r, g, b, stop_opacity)
			
			gradient_transform = target.attrib.get('gradientTransform', None)
			if gradient_transform is not None:
				self.__apply_transform(view, document, ctx, box, target, em_size, gradient_transform)
			
			ctx.set_source(gradient)
		
		elif target.tag == f'{{{self.xmlns_svg}}}pattern':
			pattern_width = self.__units(view, target.attrib['width'], percentage=(width + height) / 2, em_size=em_size)
			pattern_height = self.__units(view, target.attrib['height'], percentage=(width + height) / 2, em_size=em_size)
			
			surface = cairo.ImageSurface(cairo.Format.ARGB32, math.ceil(pattern_width), math.ceil(pattern_height))
			
			self.__render_group(view, document, cairo.Context(surface), box, target, 12, None) # TODO: initial em size
			pattern = cairo.SurfacePattern(surface)
			pattern.set_extend(cairo.Extend.REPEAT)

			ctx.set_source(pattern)
			
			# TODO: pattern transform

		else:
			self.emit_warning(view, f"Unsupported fill element: {target.tag}.", node)
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
	
	@staticmethod
	def __remove_whitespace(txt):
		txt = txt.replace("\xA0", " ")
		txt = txt.replace("\t", " ")
		txt = txt.replace("\r", " ")
		txt = txt.replace("\n", " ")
		
		txtn = txt.replace("  ", " ")
		while txtn != txt:
			txt = txtn
			txtn = txt.replace("  ", " ")
		
		#if txt != " ":
		#	txt = txt.lstrip()
		return txt.lstrip()
	
	def __render_text(self, view, document, ctx, box, textnode, em_size, pointer):
		pango_layout = PangoCairo.create_layout(ctx)
		textspec = self.__produce_text(view, document, ctx, box, textnode, em_size, '', 0, 0, pango_layout)
		return self.__render_text_spec(view, document, ctx, box, textspec, em_size, None, pango_layout, pointer)
	
	def __render_text_spec(self, view, document, ctx, box, textspec, em_size, ta_width, pango_layout, pointer):
		node, txt_paths, tx, ty, extents = textspec
		
		# TODO: support links
		
		display = self.__get_attribute(view, document, ctx, box, node, em_size, 'display', 'block').lower()
		visibility = self.__get_attribute(view, document, ctx, box, node, em_size, 'visibility', 'visible').lower()
		
		if visibility == 'collapse' or display == 'none':
			return []
		
		left, top, width, height = box
		hover_nodes = []
		
		dsx = dsy = 0
		
		if (ta_width is None) or any((_attr in node.attrib) for _attr in ['text-anchor', 'x', 'dx']):
			ta_width = extents.width
		
		text_anchor = self.__get_attribute(view, document, ctx, box, node, em_size, 'text-anchor', 'begin').strip()
		if text_anchor == 'end':
			dsx -= ta_width #extents.width
		elif text_anchor == 'middle':
			dsx -= ta_width / 2 #extents.width / 2
		
		baseline_shift = node.attrib.get('baseline-shift', 'baseline').strip()
		#baseline_shift = self.__get_attribute(view, document, ctx, box, node, em_size, 'baseline-shift', 'baseline').strip()
		if baseline_shift == 'sub':
			font_size = self.__font_size(view, document, ctx, box, node, em_size)
			dsy += font_size / 2
		elif baseline_shift == 'super':
			font_size = self.__font_size(view, document, ctx, box, node, em_size)
			dsy -= font_size / 2
		
		transform = node.attrib.get('transform', '')
		
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, em_size, transform)
		
		if visibility != 'hidden':
			filter_ = self.__get_attribute(view, document, ctx, box, node, em_size, 'filter', None)
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
		
		self.__apply_font(view, document, ctx, box, node, em_size, pango_layout)
		
		for spec in txt_paths:
			if spec[0] is not None: continue
			
			_, txt, sx, sy, sextents = spec
			sx += dsx
			sy += dsy
			
			if pango_layout is not None:
				pango_layout.set_text(txt)
				ctx.move_to(sx, sy - pango_layout.get_baseline() / Pango.SCALE)
				PangoCairo.layout_path(ctx, pango_layout)
			else:
				ctx.move_to(sx, sy)
				ctx.text_path(txt)
			
			has_fill, has_stroke = self.__apply_paint(view, document, ctx, box, node, em_size, (visibility != 'hidden'))
			
			if pointer:
				px, py = ctx.device_to_user(*pointer)
				if ctx.in_clip(px, py):
					if ctx.in_fill(px, py) or ctx.in_stroke(px, py): # TODO: pointer events
						if node not in hover_nodes:
							hover_nodes.append(node)
			
			ctx.new_path()
		
		for spec in txt_paths:
			if spec[0] is None: continue
			hover_nodes.extend(self.__render_text_spec(view, document, ctx, box, spec, em_size, ta_width, pango_layout, pointer))
		
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
	
	def __produce_text(self, view, document, ctx, box, node, em_size, whitespace, x, y, pango_layout):
		left, top, width, height = box
		
		x = self.__units(view, node.attrib.get('x', str(x)).split()[0], percentage=width, em_size=em_size) # TODO: support sequences
		y = self.__units(view, node.attrib.get('y', str(y)).split()[0], percentage=height, em_size=em_size) # TODO: support sequences
		dx = self.__units(view, node.attrib.get('dx', '0').split()[0], percentage=width, em_size=em_size) # TODO: support sequences
		dy = self.__units(view, node.attrib.get('dy', '0').split()[0], percentage=height, em_size=em_size) # TODO: support sequences
		
		whitespace = node.attrib.get(f'{{{self.xmlns_xml}}}space', whitespace)
		strip = whitespace != 'preserve'
		
		txt_paths = []
		
		text_left = None
		text_right = None
		text_top = None
		text_bottom = None
		x_advance = 0
		y_advance = 0
		
		if node.text:
			txt = self.__remove_whitespace(node.text) if strip else node.text
			if txt:
				node_x = x + dx + x_advance
				node_y = y + dy + y_advance
				
				self.__apply_font(view, document, ctx, box, node, em_size, pango_layout)
				if pango_layout is not None:
					pango_layout.set_text(txt)
					
					ink_rect, logical_rect = pango_layout.get_pixel_extents()
					pleft, ptop, pwidth, pheight = ink_rect.x, ink_rect.y, ink_rect.width, ink_rect.height
					px_bearing = pleft
					py_bearing = ptop
					px_advance = logical_rect.x + logical_rect.width
					py_advance = 0 #logical_rect.y + logical_rect.height
					
					extents = cairo.TextExtents(px_bearing, py_bearing, pwidth, pheight, px_advance, py_advance)
				else:
					extents = ctx.text_extents(txt)
				
				txt_paths.append((None, txt, node_x, node_y, extents))
				
				node_left = node_x + extents.x_bearing
				node_right = node_x + extents.x_bearing + extents.width
				node_top = node_y + extents.y_bearing
				node_bottom = node_y + extents.y_bearing + extents.height
				
				x_advance += extents.x_advance
				y_advance += extents.y_advance
				
				text_left = min(text_left, node_left) if text_left is not None else node_left
				text_right = max(text_right, node_right) if text_right is not None else node_right
				text_top = min(text_top, node_top) if text_top is not None else node_top
				text_bottom = max(text_bottom, node_bottom) if text_bottom is not None else node_bottom
		
		for child in node:
			if child.tag not in [f'{{{self.xmlns_svg}}}tspan', f'{{{self.xmlns_svg}}}a']:
				self.emit_warning(view, f"Unsupported tag {child.tag}.", child)
				continue
			
			node_x = x + dx + x_advance
			node_y = y + dy + y_advance
			
			subnode, subpaths, span_dx, span_dy, extents = self.__produce_text(view, document, ctx, box, child, em_size, whitespace, node_x, node_y, pango_layout)
			txt_paths.append((subnode, subpaths, span_dx, span_dy, extents))
			
			node_left = node_x + extents.x_bearing + span_dx - node_x
			node_right = node_x + extents.x_bearing + extents.width + span_dx - node_x
			node_top = node_y + extents.y_bearing + span_dy - node_y
			node_bottom = node_y + extents.y_bearing + extents.height + span_dy - node_y
			
			x_advance += extents.x_advance + span_dx - node_x
			y_advance += extents.y_advance + span_dy - node_y
			
			text_left = min(text_left, node_left) if text_left is not None else node_left
			text_right = max(text_right, node_right) if text_right is not None else node_right
			text_top = min(text_top, node_top) if text_top is not None else node_top
			text_bottom = max(text_bottom, node_bottom) if text_bottom is not None else node_bottom
			
			if child.tail:
				txt = self.__remove_whitespace(child.tail) if strip else child.tail
				if strip and child.tail and child.tail[0] in " \xA0\t\r\n":
					txt = " " + txt
				
				node_x = x + dx + x_advance
				node_y = y + dy + y_advance
				
				if txt == " ": # avoid creating many text paths with nothing but a space (usually separating <tspan/> elements)
					if pango_layout is not None:
						space_width = 3.1 / 1.33333 # spacing used by pango
					else:
						space_width = 3.4 # spacing used by cairo
					node_right = node_x + space_width					
					text_right = max(text_right, node_right) if text_right is not None else node_right
					x_advance += space_width
				elif txt:
					self.__apply_font(view, document, ctx, box, node, em_size, pango_layout)
					if pango_layout is not None:
						pango_layout.set_text(txt)
						
						ink_rect, logical_rect = pango_layout.get_pixel_extents()
						pleft, ptop, pwidth, pheight = ink_rect.x, ink_rect.y, ink_rect.width, ink_rect.height
						px_bearing = pleft
						py_bearing = ptop
						px_advance = logical_rect.x + logical_rect.width
						py_advance = 0 #logical_rect.y + logical_rect.height
						
						extents = cairo.TextExtents(px_bearing, py_bearing, pwidth, pheight, px_advance, py_advance)
					else:
						extents = ctx.text_extents(txt)
					
					txt_paths.append((None, txt, node_x, node_y, extents))
					
					node_left = node_x + extents.x_bearing
					node_right = node_x + extents.x_bearing + extents.width
					node_top = node_y + extents.y_bearing
					node_bottom = node_y + extents.y_bearing + extents.height
					
					x_advance += extents.x_advance
					y_advance += extents.y_advance
					
					text_left = min(text_left, node_left) if text_left is not None else node_left
					text_right = max(text_right, node_right) if text_right is not None else node_right
					text_top = min(text_top, node_top) if text_top is not None else node_top
					text_bottom = max(text_bottom, node_bottom) if text_bottom is not None else node_bottom
		
		if text_left is None: text_left = 0
		if text_right is None: text_right = 0
		if text_top is None: text_top = 0
		if text_bottom is None: text_bottom = 0
		extents = cairo.TextExtents(text_left - (x + dx), text_top - (y + dy), text_right - text_left, text_bottom - text_top, x_advance, y_advance)
		
		return node, txt_paths, x + dx, y + dy, extents
	
	def __apply_font(self, view, document, ctx, box, node, em_size, pango_layout):
		left, top, width, height = box
		
		pango_font = Pango.FontDescription()
		
		font_family = self.__get_attribute(view, document, ctx, box, node, em_size, 'font-family', 'serif') # FIXME: default font family serif?
		font_style_attrib = self.__get_attribute(view, document, ctx, box, node, em_size, 'font-style', 'normal')
		font_weight_attrib = self.__get_attribute(view, document, ctx, box, node, em_size, 'font-weight', 'normal')
		
		if font_style_attrib == 'normal':
			font_style = cairo.FontSlant.NORMAL
			pango_font.set_style(Pango.Style.NORMAL)
		elif font_style_attrib == 'italic':
			font_style = cairo.FontSlant.ITALIC
			pango_font.set_style(Pango.Style.ITALIC)
		elif font_style_attrib == 'oblique':
			font_style = cairo.FontSlant.OBLIQUE
			pango_font.set_style(Pango.Style.OBLIQUE)
		else:
			self.emit_warning(view, f"Unsupported font style '{font_style_attrib}'.", node)
			font_style = cairo.FontSlant.NORMAL
			pango_font.set_style(Pango.Style.NORMAL)
		
		if font_weight_attrib == 'normal':
			font_weight = cairo.FontWeight.NORMAL
			pango_font.set_weight(Pango.Weight.NORMAL)
		elif font_weight_attrib == 'bold':
			font_weight = cairo.FontWeight.BOLD
			pango_font.set_weight(Pango.Weight.BOLD)
		else:
			try:
				font_weight_number = int(font_weight_attrib)
				pango_font.set_weight(font_weight_number)
			except ValueError:
				self.emit_warning(view, f"Unsupported font weight '{font_weight_attrib}'.", node)
				font_weight = cairo.FontWeight.NORMAL
				pango_font.set_weight(Pango.Weight.NORMAL)
			else:
				if font_weight_number > 500:
					font_weight = cairo.FontWeight.BOLD
					pango_font.set_weight(Pango.Weight.BOLD)
				else:
					font_weight = cairo.FontWeight.NORMAL
					pango_font.set_weight(Pango.Weight.NORMAL)
		
		font_size = self.__font_size(view, document, ctx, box, node, em_size)
		ctx.set_font_size(font_size)
		pango_font.set_size(font_size * Pango.SCALE / 1.33333)
		
		for family in reversed(font_family.split(',')):
			ctx.select_font_face(family, font_style, font_weight)
			pango_font.set_family(family)
			if pango_layout is not None:
				pango_layout.set_font_description(pango_font)
	
	def __font_size(self, view, document, ctx, box, node, em_size):
		font_size_attrib = self.__get_attribute(view, document, ctx, box, node, em_size, 'font-size', 12)
		
		if font_size_attrib == 'smaller':
			font_size_attrib = '0.9em'
		elif font_size_attrib == 'bigger':
			font_size_attrib = '1.1em'
		
		_, _, width, height = box
		font_size = self.__units(view, font_size_attrib, percentage=(width + height) / 2, em_size=em_size)
		return font_size
	
	def __draw_path(self, view, document, ctx, box, node, em_size):
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
				return self.__units(view, next_token(), percentage=percentage, em_size=em_size)
			except (ValueError, AttributeError, TypeError) as error:
				raise NotANumber(error)
		
		try:
			next_token()
		except StopIteration:
			return
		
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
						
						angle = math.radians(angle)
						rx, ry = abs(rx), abs(ry)
						large_arc_flag = bool(large_arc_flag)
						sweep_flag = bool(sweep_flag)
						
						self.__draw_arc(ctx, x_start, y_start, x_stop, y_stop, rx, ry, angle, large_arc_flag, sweep_flag)
				
				elif command in 'Zz':
					ctx.close_path()
					first = True
				
				else:
					self.emit_warning(view, f"Unsupported path syntax: {command}.", node)
					#raise ValueError("Unsupported path syntax")
				
				next_token()
			
			except NotANumber:
				continue
			except StopIteration:
				break
			except ValueError as error:
				self.emit_warning(view, f"Error in path rendering: {str(error)}.", node)
				raise
				return
	
	@staticmethod
	def __draw_rounded_rectangle(ctx, x, y, w, h, rx, ry):
		r = (rx + ry) / 2 # TODO: non-symmetric rounded corners
		ctx.new_sub_path()
		ctx.arc(x + r, y + r, r, math.radians(180), math.radians(270))
		ctx.line_to(x + w - r, y)
		ctx.arc(x + w - r, y + r, r, math.radians(-90), math.radians(0))
		ctx.line_to(x + w, y + h - r)
		ctx.arc(x + w - r, y + h - r, r, math.radians(0), math.radians(90))
		ctx.line_to(x + r, y + h)
		ctx.arc(x + r, y + h - r, r, math.radians(90), math.radians(180))
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
		if sweep_flag != large_arc_flag: ext_angle = math.copysign(math.pi, ext_angle) - ext_angle
		
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
	
	def __render_image(self, view, document, ctx, box, node, em_size, pointer):
		"Render external image."
		
		try:
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
		except AttributeError:
			href = node.attrib.get('href', None)
		
		if not href:
			self.emit_warning(view, "Image without href.", node)
			return defaultdict(list)
		
		url = self.resolve_url(href, self.get_document_url(document))
		
		left, top, width, height = box
		x = self.__units(view, node.attrib.get('x', 0), percentage=width, em_size=em_size)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height, em_size=em_size)
		w = self.__units(view, node.attrib.get('width', width), percentage=width, em_size=em_size)
		h = self.__units(view, node.attrib.get('height', height), percentage=height, em_size=em_size)
		box = x, y, w, h
		
		transform = node.attrib.get('transform', None)
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, em_size, transform)
		
		hover_nodes = []
		
		try:
			image = self.get_document(url)
			if not pointer:
				self.draw_image(view, image, ctx, box)
			#else: # no events inside <image/>
			#	hover_subnodes = self.poke_image(view, image, ctx, box, *pointer)
			#	hover_nodes.extend(hover_subnodes)
		except (IndexError, KeyError):
			self.emit_warning(view, f"Could not fetch url: {url}.", node)
		except NotImplementedError:
			self.emit_warning(view, f"Unsupported image format: {type(image).__name__}.", node)
		finally:
			if transform:
				ctx.restore()
		
		if pointer:
			rx, ry = ctx.device_to_user(*pointer)
			if x <= rx <= x + w and y <= ry <= y + h and ctx.in_clip(rx, ry):
				hover_nodes.insert(0, node)
		return hover_nodes
	
	def __render_foreign_object(self, view, document, ctx, box, node, em_size, pointer):
		"Render <foreignObject/>. Rendering of the child node must be implemented separately."
		
		left, top, width, height = box
		x = self.__units(view, node.attrib.get('x', 0), percentage=width, em_size=em_size)
		y = self.__units(view, node.attrib.get('y', 0), percentage=height, em_size=em_size)
		w = self.__units(view, node.attrib.get('width', width), percentage=width, em_size=em_size)
		h = self.__units(view, node.attrib.get('height', height), percentage=height, em_size=em_size)
		box = x, y, w, h
		
		transform = node.attrib.get('transform', None)
		if transform:
			ctx.save()
			self.__apply_transform(view, document, ctx, box, node, em_size, transform)
		
		hover_nodes = []
		
		try:
			for child in node:
				try:
					ctx.save()
					if not pointer:
						self.draw_image(view, child, ctx, box)
					else:
						hover_subnodes = self.poke_image(view, child, ctx, box, *pointer)
						hover_nodes.extend(hover_subnodes)
				except NotImplementedError:
					self.emit_warning(view, f"Unsupported foreign object: `{child.tag}`.", child)
				finally:
					ctx.restore()
		finally:
			if transform:
				ctx.restore()
		
		if pointer:
			rx, ry = ctx.device_to_user(*pointer)
			if x <= rx <= x + w and y <= ry <= y + h and ctx.in_clip(rx, ry):
				hover_nodes.insert(0, node)
		return hover_nodes


if __debug__ and __name__ == '__main__':
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	from pathlib import Path
	from format.xml import XMLFormat, XMLDocument
	from format.css import CSSFormat, CSSDocument
	from format.null import NullFormat
	from download.data import DataDownload
	from urllib.parse import unquote as url_unquote
	
	print("svg image")
	
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
	
	class SVGRenderModel(SVGImage, CSSFormat, XMLFormat, DataDownload, NullFormat):
		def scan_document_links(self, document):
			if SVGImage.is_svg_document(self, document):
				return SVGImage.scan_document_links(self, document)
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
				return SVGImage.create_document(self, data, mime_type)
			else:
				raise NotImplementedError("Could not create unsupported document type.")
		
		def resolve_url(self, rel_url, base_url):
			return rel_url
		
		def emit_warning(self, view, message, target):
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
				return defaultdict(list)
			return r
		
		def get_dpi(self, view):
			return 96
		
		def get_pointed(self, view):
			return None
	
	class PseudoView:
		def __init__(self):
			pass
	
	#nn = 0
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue

		for filepath in example.iterdir():
			if filepath.suffix != '.svg': continue
			#if filepath.name != 'animated-text-fine-cravings.svg': continue
			#nn += 1
			#if nn > 1: break
			
			#profiler = PyCallGraph(output=GraphvizOutput(output_file=f'profile/svg_{example.name}_{filepath.name}.png'))
			#profiler.start()
			
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			rnd = SVGRenderModel()
			view = PseudoView()
			
			document = rnd.create_document(filepath.read_bytes(), 'image/svg')
			l = list(rnd.scan_document_links(document))
			
			rnd.tree = document
			try:
				rnd.draw_image(view, document, ctx, (0, 0, 1024, 768))
			except TypeError: # error from Pango
				pass
			else:	
				assert ctx.balance == 0
				
			#profiler.done()


