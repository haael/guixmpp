#!/usr/bin/python3
#-*- coding:utf-8 -*-

"""
SVGRender - A simple module that renders an SVG image to a Cairo context.
"""


__all__ = 'SVGRender',


import re
import math
from math import pi, radians
from enum import Enum
import cairo
from collections import defaultdict
from itertools import chain


try:
	distance = math.dist
except AttributeError:
	def distance(a, b):
		return math.sqrt(sum((_a - _b)**2 for (_a, _b) in zip(a, b)))

'''
if __debug__:
	class Epsilon:
		def __init__(self, value=0, accuracy=0):
			if accuracy < 0:
				raise ValueError("Accuracy must be nonnegative.")
			self.value = value
			self.accuracy = accuracy
		
		@staticmethod
		def __value(x):
			try:
				return x.value
			except AttributeError:
				return x
		
		@staticmethod
		def __accuracy(x):
			try:
				return x.accuracy
			except AttributeError:
				return 0
		
		def __add__(self, other):
			return self.__class__(self.value + self.__value(other), self.accuracy + self.__accuracy(other))
		
		def __radd__(self, other):
			return self.__class__(self.__value(other) + self.value, self.accuracy + self.__accuracy(other))
		
		def __sub__(self, other):
			return self.__class__(self.value - self.__value(other), self.accuracy + self.__accuracy(other))
		
		def __rsub__(self, other):
			return self.__class__(self.__value(other) - self.value, self.accuracy + self.__accuracy(other))
		
		def __mul__(self, other):
			return self.__class__(self.value * self.__value(other), self.accuracy * (abs(self.__value(other)) + self.__accuracy(other)))
		
		def __rmul__(self, other):
			return self.__class__(self.__value(other) * self.value, (abs(self.__value(other)) + self.__accuracy(other)) * self.accuracy)
		
		def __truediv__(self, other):
			if abs(self.__value(other)) <= self.__accuracy(other):
				raise ArithmeticError("Error is infinite. You divided epsilon by a value close to zero.")
			return self.__class__(self.value / self.__value(other), (abs(self.value) + self.accuracy) / (abs(self.__value(other)) - self.__accuracy(other)))
		
		def __rtruediv__(self, other):
			if abs(self.value) <= self.accuracy:
				raise ArithmeticError("Error is infinite. You divided epsilon by a value close to zero.")
			return self.__class__(self.__value(other) / self.value, (abs(self.__value(other)) + self.__accuracy(other)) / (abs(self.value) - self.accuracy))
		
		def __pow__(self, exponent):
			return self.__class__(self.value**exponent, self.accuracy**exponent if self.accuracy else 0)
		
		def __bool__(self):
			return bool(self.value)
		
		def __int__(self):
			return int(self.value)
		
		def __float__(self):
			return float(self.value)
		
		def __eq__(self, other):
			return self.value - self.accuracy <= float(other) <= self.value + self.accuracy
	
	
	epsilon = Epsilon(accuracy=0.002)
'''


class SVGRender:
	xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	xmlns_svg = 'http://www.w3.org/2000/svg'
	xmlns_xlink = 'http://www.w3.org/1999/xlink'
	xmlns_sodipodi = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
	xmlns_inkscape = 'http://www.inkscape.org/namespaces/inkscape'
	
	colors = {
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
	
	class NotANumber(BaseException):
		def __init__(self, original):
			self.original = original
	
	def __init__(self):
		self.__defs = {}
		self.dpi = 96
	
	def __apply_stylesheet(self, url, style, node):
		from tinycss2 import parse_declaration_list, serialize
		
		for rule in style:
			try:
				target_refs = serialize(rule.prelude).strip().split(',')
				
				match = False
				for target_ref in target_refs:
					target_ref = target_ref.strip()
					if target_ref[0] == '#' and node.attrib.get('id', None) == target_ref[1:]:
						match = True
					elif target_ref[0] == '.' and target_ref[1:] in node.attrib.get('class', None).split(' '):
						match = True
					elif node.tag == f'{{{self.xmlns_svg}}}{target_ref}':
						match = True
					
					if match: break
				
				if not match: continue
				
				for decl in parse_declaration_list(serialize(rule.content)):
					try:
						node.attrib[decl.name] = serialize(decl.value)
					except AttributeError:
						pass
			
			except (AttributeError, KeyError):
				pass
		
		for child in node:
			self.__apply_stylesheet(url, style, child)
	
	def __parse_stylesheet_resource(self, stylesheet_text, target_url, root):
		from tinycss2 import parse_stylesheet
		self.__apply_stylesheet(target_url, parse_stylesheet(stylesheet_text), root)
	
	def __parse_style_tag(self, style_url, node, target_url, root):
		from tinycss2 import parse_stylesheet, serialize
		
		if node.tag == f'{{{self.xmlns_svg}}}style':
			self.__apply_stylesheet(target_url, parse_stylesheet(node.text), root)
		
		for child in node:
			self.__parse_style_tag(style_url, child, target_url, root)
	
	def __parse_style_attrib(self, url, node):
		from tinycss2 import parse_declaration_list, serialize
		
		try:
			for decl in parse_declaration_list(node.attrib['style']):
				try:
					node.attrib[decl.name] = serialize(decl.value)
				except AttributeError:
					pass
		except KeyError:
			pass
		
		for child in node:
			self.__parse_style_attrib(url, child)
	
	def parse_css(self, url, document):
		"""
		Transform an SVG document using downloaded CSS stylesheets. If a stylesheet is not downloaded yet, request it.
		If a stylesheet is missing, it is not applied. This method may return different result depending on the cached stylesheets.
		A downloaded stylesheet may recursively request another one.
		This method should be called successively until all stylesheets are available. The resulting document tree is returned as result.
		"""
		root = document.getroot()
		try:
			if document.stylesheet:
				href = self.resolve_url(document.stylesheet, self.main_url)
				stylesheet = self.get_doc(href).decode('utf-8')
			else:
				stylesheet = None
		except AttributeError:
			pass
		except KeyError:
			self.request_url(self.resolve_url(document.stylesheet, self.main_url))
		else:
			if stylesheet:
				self.__parse_stylesheet_resource(stylesheet, url, root)
		self.__parse_style_tag(url, root, url, root)
		self.__parse_style_attrib(url, root)
		return document
	
	def transform_document(self, url, document):
		"Transform the SVG document before registering it. CSS parsing should happen here."
		try:
			if document.getroot().tag == f'{{{self.xmlns_svg}}}svg':
				self.parse_css(url, document)
		except AttributeError:
			pass
		return document
	
	def scan_link(self, base_url, node):
		try:
			self.__defs[base_url + '#' + node.attrib['id'].strip()] = node
		except KeyError:
			pass
		
		if node.tag in (f'{{{self.xmlns_svg}}}use', f'{{{self.xmlns_svg}}}image'):
			url = node.attrib[f'{{{self.xmlns_xlink}}}href'].strip()
			if url:
				abs_url = self.resolve_url(url, base_url)
				if '#' in abs_url:
					abs_url = '#'.join(abs_url.split('#')[:-1])
				self.request_url(abs_url)
	
	def render_xml(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		if node.tag in [f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in ('defs', 'title', 'desc', 'metadata', 'style', 'linearGradient', 'radialGradient', 'script', 'symbol', 'animate', 'filter')]:
			pass
		elif node.tag == f'{{{self.xmlns_sodipodi}}}namedview': # a very common nonstandard tag in svg documents created by inkscape
			pass
		elif node.tag == f'{{{self.xmlns_svg}}}use':
			return self.render_use(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag == f'{{{self.xmlns_svg}}}svg':
			return self.render_svg(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag == f'{{{self.xmlns_svg}}}g':
			return self.render_group(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag == f'{{{self.xmlns_svg}}}switch':
			return self.render_switch(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag == f'{{{self.xmlns_svg}}}a':
			return self.render_anchor(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag == f'{{{self.xmlns_svg}}}image':
			return self.render_image(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag == f'{{{self.xmlns_svg}}}foreignObject':
			return self.render_foreign_object(ctx, box, node, ancestors, current_url, level, draw, pointer)
		elif node.tag in [f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in ('polygon', 'line', 'ellipse', 'circle', 'rect', 'path', 'text')]:
			return self.render_shape(ctx, box, node, ancestors, current_url, level, draw, pointer)
		else:
			self.error(f"unsupported tag: {node.tag}", node.tag, node)
		
		return []
	
	class OverlayElement(list):
		def findall(self, path):
			if path == '..':
				return [self.parent]
			else:
				raise ValueError
	
	def render_use(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		href = self.resolve_url(node.attrib[f'{{{self.xmlns_xlink}}}href'], current_url)
		
		try:
			original = self.__defs[href]
		except KeyError:
			self.error(f"Ref not found: {href}", href, node)
			return []
		
		target = self.OverlayElement()
		if original.tag == f'{{{self.xmlns_svg}}}symbol':
			target.tag = f'{{{self.xmlns_svg}}}g'
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
		
		return self.render_xml(ctx, box, target, ancestors, current_url, level, draw, pointer)
	
	supported_features = frozenset(['http://www.w3.org/TR/SVG11/feature#Shape'])
	supported_extensions = frozenset()
	
	def render_switch(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		for child in node:
			required_features = frozenset(child.attrib.get('requiredFeatures', '').strip().split())
			required_extensions = frozenset(child.attrib.get('requiredExtensions', '').strip().split())
			if required_features <= self.supported_features and required_extensions <= self.supported_extensions:
				return self.render_xml(ctx, box, child, ancestors + [node], current_url, level, draw, pointer)
		return []
	
	def render_anchor(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		try:
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
			ctx.tag_begin('a', f'href=\'{href}\'')
		except AttributeError:
			pass
		
		nodes_under_pointer = self.render_group(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		try:
			ctx.tag_end('a')
		except AttributeError:
			pass
		
		return nodes_under_pointer
	
	def render_image(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		href = node.attrib[f'{{{self.xmlns_xlink}}}href']
		url = self.resolve_url(href, current_url)
		
		left, top, width, height = box
		x = self.__units(node.attrib['x'], percentage=width)
		y = self.__units(node.attrib['y'], percentage=height)
		w = self.__units(node.attrib['width'], percentage=width)
		h = self.__units(node.attrib['height'], percentage=height)
		box = x, y, w, h
		
		#if pointer: pointer = pointer[0] - x, pointer[1] - y # TODO: user coordinates
		
		if 'transform' in node.attrib:
			ctx.save()
			self.__apply_transform(ctx, box, node, ancestors)
		
		nodes_under_pointer = self.render_url(ctx, box, url, level, draw, pointer)
		
		if 'transform' in node.attrib:
			ctx.restore()
		
		if nodes_under_pointer:
			nodes_under_pointer.insert(0, node)
			if nodes_under_pointer[-1] == None:
				del nodes_under_pointer[-1]
		return nodes_under_pointer
	
	def render_foreign_object(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		nodes_under_pointer = []
		
		left, top, width, height = box
		
		if pointer:
			px, py = pointer
			if left <= px < left + width and top <= py < top + height:
				nodes_under_pointer.append(node)
		
		x = left + self.__units(node.get('x', '0'), percentage=width)
		y = top + self.__units(node.get('y', '0'), percentage=height)
		w = self.__units(node.get('width', '100%'), percentage=width)
		h = self.__units(node.get('height', '100%'), percentage=height)
		
		ancestors = ancestors + [node]
		ctx.save()
		for child in node:
			nodes_under_pointer += self.render_xml(ctx, (x, y, w, h), child, ancestors, current_url, level+1, draw, pointer)		
		ctx.restore()
		
		return nodes_under_pointer
	
	def render_svg(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		if node.tag != f'{{{self.xmlns_svg}}}svg':
			self.error("root element not 'svg'", node.tag, node)
			return []
		
		left, top, width, height = box
		
		ctx.save()
		
		if left or top:
			ctx.translate(left, top)
		
		try:
			svg_width = self.__units(node.attrib['width'], percentage=width)
		except KeyError:
			svg_width = width
		
		try:
			svg_height = self.__units(node.attrib['height'], percentage=height)
		except KeyError:
			svg_height = height
		
		ctx.rectangle(0, 0, svg_width, svg_height)
		ctx.clip()
		
		try:
			vb_x, vb_y, vb_w, vb_h = node.attrib['viewBox'].split()
		except KeyError:
			viewbox_x = viewbox_y = 0
			viewbox_w = svg_width
			viewbox_h = svg_height
		else:
			viewbox_x = self.__units(vb_x, percentage=width)
			viewbox_y = self.__units(vb_y, percentage=height)
			viewbox_w = self.__units(vb_w, percentage=width)
			viewbox_h = self.__units(vb_h, percentage=height)
			
			x_scale = svg_width / viewbox_w
			y_scale = svg_height / viewbox_h
			
			x_scale = y_scale = min(x_scale, y_scale)
			
			ctx.scale(x_scale, y_scale)
			ctx.translate(-viewbox_x, -viewbox_y)
		
		nodes_under_pointer = self.render_group(ctx, (viewbox_x, viewbox_y, viewbox_w, viewbox_h), node, ancestors, current_url, level, draw, pointer)
		
		ctx.restore()
		
		return nodes_under_pointer
	
	def render_group(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		left, top, width, height = box
		
		if level:
			try:
				x = self.__units(node.attrib['x'], percentage=width)
			except KeyError:
				x = 0
			
			try:
				y = self.__units(node.attrib['y'], percentage=height)
			except KeyError:
				y = 0
			
			if x or y:
				ctx.save()
				ctx.translate(x, y)
		
		if 'transform' in node.attrib:
			ctx.save()
			self.__apply_transform(ctx, box, node, ancestors)
		
		nodes_under_pointer = []
		ancestors = ancestors + [node]
		for child in node:
			nodes_under_pointer += self.render_xml(ctx, box, child, ancestors, current_url, level+1, draw, pointer)
		
		if 'transform' in node.attrib:
			ctx.restore()
		
		if level and (x or y):
			ctx.restore()
		
		if nodes_under_pointer:
			nodes_under_pointer.insert(0, node)
		
		return nodes_under_pointer
	
	@staticmethod
	def __draw_rounded_rectangle(ctx, x, y, w, h, rx, ry):
		r = (rx + ry) / 2 # TODO
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
	
	def render_shape(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		left, top, width, height = box
		
		try:
			filter_ = node.attrib['filter']
		except KeyError:
			filter_ = None
		
		try:
			visibility = self.__search_attrib(node, ancestors, 'visibility')
		except KeyError:
			visibility = 'visible'
		
		is_visible = visibility not in ('hidden', 'collapse')
		
		if filter_ and draw and is_visible:
			margin = 10
			image = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(box[2] + 2 * margin + 1), int(box[3] + 2 * margin + 1))
			image_ctx = cairo.Context(image)
			image_ctx.set_matrix(ctx.get_matrix())
			image_ctx.translate(-box[0] + margin, -box[1] + margin)
			old_ctx = ctx
			ctx = image_ctx
		
		if 'transform' in node.attrib:
			ctx.save()
			self.__apply_transform(ctx, box, node, ancestors)
		
		if node.tag == f'{{{self.xmlns_svg}}}rect':
			x, w, rx = [self.__units(node.attrib.get(_a, '0'), percentage=width) for _a in ('x', 'width', 'rx')]
			y, h, ry = [self.__units(node.attrib.get(_a, '0'), percentage=height) for _a in ('y', 'height', 'ry')]
			
			rx = max(rx, 0)
			ry = max(ry, 0)
			
			if rx or ry:
				self.__draw_rounded_rectangle(ctx, x, y, w, h, rx, ry)
			else:
				#print("rectangle:", x, y, w, h)
				ctx.rectangle(x, y, w, h)
		
		elif node.tag == f'{{{self.xmlns_svg}}}circle':
			try:
				cx = self.__units(node.attrib['cx'], percentage=width)
			except KeyError:
				cx = 0
			
			try:
				cy = self.__units(node.attrib['cy'], percentage=height)
			except KeyError:
				cy = 0
			
			r = self.__units(node.attrib['r'], percentage=(width + height) / 2)
			ctx.arc(cx, cy, r, 0, 2*pi)
		
		elif node.tag == f'{{{self.xmlns_svg}}}ellipse':
			cx = self.__units(node.attrib['cx'], percentage=width)
			cy = self.__units(node.attrib['cy'], percentage=height)
			rx = self.__units(node.attrib['rx'], percentage=width)
			ry = self.__units(node.attrib['ry'], percentage=height)
			ctx.save()
			ctx.translate(cx, cy)
			ctx.scale(rx, ry)
			ctx.arc(0, 0, 1, 0, 2*pi)
			ctx.restore()
		
		elif node.tag == f'{{{self.xmlns_svg}}}line':
			x1 = self.__units(node.attrib['x1'], percentage=width)
			y1 = self.__units(node.attrib['y1'], percentage=height)
			x2 = self.__units(node.attrib['x2'], percentage=width)
			y2 = self.__units(node.attrib['y2'], percentage=height)
			ctx.move_to(x1, y1)
			ctx.line_to(x2, y2)
		
		elif node.tag == f'{{{self.xmlns_svg}}}polygon':
			points = node.attrib['points'].split()
			first = True
			for point in points:
				xs, ys, *_ = point.split(',')
				x = self.__units(xs, percentage=width)
				y = self.__units(ys, percentage=height)
				if first:
					ctx.move_to(x, y)
					first = False
				else:
					ctx.line_to(x, y)
			if not first:
				ctx.close_path()
		
		elif node.tag == f'{{{self.xmlns_svg}}}path':
			#print(node.attrib.get('transform', None))
			self.__draw_path(ctx, box, node, ancestors, level)
		
		elif node.tag == f'{{{self.xmlns_svg}}}text':
			self.__draw_text(ctx, box, node, ancestors, level)
		
		else:
			self.error(f"tag {node.tag} not supported by this method", node.tag, node)
				
		has_fill, has_stroke = self.__apply_paint(ctx, box, node, ancestors, current_url, draw and is_visible)
		
		nodes_under_pointer = []
		if pointer:
			try:
				pointer_events = self.__search_attrib(node, ancestors, 'pointer-events')
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
				self.error(f"Unsupported value of attribute `visibility`: '{visibility}'", visibility, node)
				check_fill = is_visible and has_fill
				check_stroke = is_visible and has_stroke
			
			if check_fill or check_stroke:
				x, y = ctx.device_to_user(*pointer)
				#print(has_fill, has_stroke, check_fill, check_stroke, (x, y), ctx.in_fill(x, y), ctx.in_stroke(x, y))
				if (check_stroke and ctx.in_stroke(x, y)) or (check_fill and ctx.in_fill(x, y)):
					nodes_under_pointer.append(node)
		
		ctx.new_path()
		
		if 'transform' in node.attrib:
			ctx.restore()
		
		if filter_ and draw and is_visible:
			image.flush()
			#stride = image.get_stride()
			#data = image.get_data()
			#for x in range(margin, image.get_width() - margin):
			#	for y in range(margin, image.get_height() - margin):
			#		rs = 0
			#		gs = 0
			#		bs = 0
			#		
			#		for d in range(-2, 3):
			#			for e in range(-2, 3):
			#				j = (y + e) * stride + (x + d) * 4
			#				r, g, b = data[j + 2], data[j + 1], data[j + 0]
			#				rs += r / (1 + d**2 + e**2)
			#				gs += g / (1 + d**2 + e**2)
			#				bs += b / (1 + d**2 + e**2)
			#		
			#		i = y * stride + x * 4
			#		data[i + 2], data[i + 1], data[i + 0] = int(r), int(g), int(b)
			
			ctx = old_ctx
			ctx.set_source_surface(image, -margin, -margin)
			ctx.rectangle(*box)
			ctx.fill()
			image.finish()
		
		return nodes_under_pointer
	
	def __apply_paint(self, ctx, box, node, ancestors, current_url, draw):
		has_fill = False
		ctx.save()
		if self.__apply_fill(ctx, box, node, ancestors, current_url):
			has_fill = True
			if draw:
				ctx.fill_preserve()
		ctx.restore()
		
		has_stroke = False
		ctx.save()
		if self.__apply_stroke(ctx, box, node, ancestors, current_url):
			has_stroke = True
			if draw:
				ctx.stroke_preserve()
		ctx.restore()
		
		return has_fill, has_stroke
	
	def __apply_pattern_from_url(self, ctx, box, node, ancestors, current_url, url):
		#print(url)
		href = url.strip()[4:-1]
		if href[0] == '"' and href[-1] == '"': href = href[1:-1]
		href = self.resolve_url(href, current_url)
		
		try:
			target = self.__defs[href]
		except KeyError:
			self.error(f"Color pattern ref not found: {href}", href, node)
			return False
		
		left, top, width, height = box
		
		if target.tag == f'{{{self.xmlns_svg}}}linearGradient' or target.tag == f'{{{self.xmlns_svg}}}radialGradient':
			
			if target.attrib.get('gradientUnits', '') == 'userSpaceOnUse':
				userspace = True
			else:
				userspace = False
			
			if target.tag == f'{{{self.xmlns_svg}}}linearGradient':

				try:
					href = target.attrib[f'{{{self.xmlns_xlink}}}href']
				except KeyError:
					pass
				else:
					href = self.resolve_url(href, current_url)
					#if href[0] == '#': href = self.main_url + href
					orig_target = target
					try:
						original = self.__defs[href]
					except KeyError:
						self.error("Ref not found: %s" % href, href, node)
						return False
					else:
						target = self.OverlayElement()
						target.tag = original.tag
						target.attrib = dict(original.attrib)
						target.attrib.update(dict((_k, _v) for (_k, _v) in orig_target.attrib.items() if _k != f'{{{self.xmlns_xlink}}}href'))
						target.extend(original)
						target.text = original.text
						target.tail = original.tail
					
					for stop in orig_target:
						for tstop in target:
							if tstop.attrib['id'] == stop['id']:
								target.remove(tstop)
						target.append(stop)
				
				default_x1, default_y1, default_x2, default_y2 = ctx.path_extents()
				
				try:
					spec = target.attrib['x1']
					if spec[-1] == '%':
						x1 = float(spec[:-1]) / 100 * (default_x2 - default_x1) + default_x1
					else:
						x1 = float(spec) #* (default_x2 - default_x1) + default_x1
						
						if not userspace:
							x1 = x1 * (default_x2 - default_x1) + default_x1
					
					#x1 = self.__units(target.attrib['x1'], percentage=default_x2-default_x1, percentage_origin=default_x1)
				except KeyError:
					x1 = default_x1
				except ValueError:
					self.error("Invalid x1 specification in linear gradient.", target.attrib['x1'], target)
					x1 = default_x1
				
				try:
					spec = target.attrib['y1']
					if spec[-1] == '%':
						y1 = float(spec[:-1]) / 100 * (default_y2 - default_y1) + default_y1
					else:
						y1 = float(spec) #* (default_y2 - default_y1) + default_y1
						
						if not userspace:
							y1 = y1 * (default_y2 - default_y1) + default_y1

					#y1 = self.__units(target.attrib['y1'], percentage=default_y2-default_y1, percentage_origin=default_y1)
				except KeyError:
					y1 = default_y1
				except ValueError:
					self.error("Invalid y1 specification in linear gradient.", target.attrib['y1'], target)
					y1 = default_y1
				
				try:
					spec = target.attrib['x2']
					if spec[-1] == '%':
						x2 = float(spec[:-1]) / 100 * (default_x2 - default_x1) + default_x1
					else:
						x2 = float(spec) #* (default_x2 - default_x1) + default_x1
						
						if not userspace:
							x2 = x2 * (default_x2 - default_x1) + default_x1

					#x2 = self.__units(target.attrib['x2'], percentage=default_x2-default_x1, percentage_origin=default_x1)
				except KeyError:
					x2 = default_x2
				except ValueError:
					self.error("Invalid x2 specification in linear gradient.", target.attrib['x2'], target)
					x2 = default_x2
				
				try:
					spec = target.attrib['y2']
					if spec[-1] == '%':
						y2 = float(spec[:-1]) / 100 * (default_y2 - default_y1) + default_y1
					else:
						y2 = float(spec) #* (default_y2 - default_y1) + default_y1
						
						if not userspace:
							y2 = y2 * (default_y2 - default_y1) + default_y1

					#y2 = self.__units(target.attrib['y2'], percentage=default_y2-default_y1, percentage_origin=default_y1)
				except KeyError:
					y2 = default_y1
				except ValueError:
					self.error("Invalid y2 specification in linear gradient.", target.attrib['y2'], target)
					y2 = default_y1
				
				#print("linear gradient", (x1, y1), (x2, y2), box)
				gradient = cairo.LinearGradient(x1 + left, y1 + top, x2 + left, y2 + top)
			
			elif target.tag == f'{{{self.xmlns_svg}}}radialGradient':
				default_x1, default_y1, default_x2, default_y2 = ctx.path_extents()
				
				try:
					spec = target.attrib['r']
					if spec[-1] == '%':
						r = float(spec[:-1]) / 100 * (default_x2 - default_x1 + default_y2 - default_y1) / 2 # TODO: right calculation
					else:
						r = float(spec)
				except KeyError:
					r = (width + height) / 2
				except ValueError:
					self.error("Invalid r specification in radial gradient.", target.attrib['r'], target)
					r = 0
				
				try:
					spec = target.attrib['cx']
					if spec[-1] == '%':
						cx = float(spec[:-1]) / 100 * (default_x2 - default_x1) + default_x1
					else:
						cx = float(spec)
				except KeyError:
					cx = 0
				except ValueError:
					self.error("Invalid cx specification in linear gradient.", target.attrib['cx'], target)
					cx = 0
				
				try:
					spec = target.attrib['cy']
					if spec[-1] == '%':
						cy = float(spec[:-1]) / 100 * (default_y2 - default_y1) + default_y1
					else:
						cy = float(spec)
				except KeyError:
					cy = 0
				except ValueError:
					self.error("Invalid cy specification in linear gradient.", target.attrib['cy'], target)
					cy = 0
				
				try:
					spec = target.attrib['fx']
					if spec[-1] == '%':
						fx = float(spec[:-1]) / 100 * (default_x2 - default_x1) + default_x1
					else:
						fx = float(spec)
				except KeyError:
					fx = cx
				except ValueError:
					self.error("Invalid fx specification in linear gradient.", target.attrib['fx'], target)
					fx = cx
				
				try:
					spec = target.attrib['fy']
					if spec[-1] == '%':
						fy = float(spec[:-1]) / 100 * (default_y2 - default_y1) + default_y1
					else:
						fy = float(spec)
				except KeyError:
					fy = cy
				except ValueError:
					self.error("Invalid cy specification in linear gradient.", target.attrib['fy'], target)
					fy = cy
				
				#print("radial gradient", (cx, cy), (fx, fy), r, box)
				gradient = cairo.RadialGradient(cx, cy, 0, fx, fy, r)
			
			try:
				href = target.attrib[f'{{{self.xmlns_xlink}}}href']
				#if href[0] == '#': href = self.main_url + href
				href = self.resolve_url(href, current_url)
				target = self.__defs[href]
			except KeyError:
				pass
			
			last_offset = 0
			for colorstop in target:
				#colorstop_style = self.__process_style(colorstop)
				try:
					offset_spec = colorstop.attrib['offset']
					if offset_spec[-1] == '%':
						offset = float(offset_spec[:-1]) / 100
					else:
						offset = float(offset_spec)
				except KeyError:
					offset = last_offset
				except ValueError:
					self.error("Error in offset spec of a linear gradient.", colorstop.attrib['offset'], colorstop)
					offset = last_offset
				
				last_offset = offset
				stop_color = None
				stop_opacity = None
				
				try:
					stop_color = colorstop.attrib['stop-color'].strip()
				except KeyError:
					if stop_color == None:
						self.error("Stop color of linear gradient not found.", None, colorstop)
						continue
				
				try:
					stop_opacity = float(colorstop.attrib['stop-opacity'])
				except KeyError:
					pass
				
				if not stop_color or stop_color.lower() in ('none', 'transparent'):
					continue
				
				try:
					stop_color = self.colors[stop_color.lower()]
				except KeyError:
					pass

				if len(stop_color) not in (4, 7) or stop_color[0] != '#':
					self.error("Unsupported color specification in gradient: %s" % stop_color, stop_color, colorstop)
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
					#print("gradient stop", offset, (r, g, b))
					gradient.add_color_stop_rgb(offset, r, g, b)
				else:
					#print("gradient stop", offset, (r, g, b, stop_opacity))
					gradient.add_color_stop_rgba(offset, r, g, b, stop_opacity)
			
			#print(target.attrib)
			self.__apply_transform(ctx, box, target, ancestors + [node], 'gradientTransform')
			
			ctx.set_source(gradient)
		else:
			self.error("Unsupported fill element: %s" % target.tag, target.tag, node)
			return False
	
	def __search_attrib(self, node, ancestors, attrib):
		try:
			return node.attrib[attrib]
		except (KeyError, AttributeError):
			pass
		
		for ancestor in reversed(ancestors):
			try:
				return ancestor.attrib[attrib]
			except KeyError:
				pass
		
		raise KeyError(f"Attribute {attrib} not found in any of ancestors")
	
	def __apply_color(self, ctx, box, node, ancestors, current_url, color_attr, opacity_attr, default_color):
		#style = self.__process_style(node)
		
		try:
			color = self.__search_attrib(node, ancestors, color_attr).strip()
		except KeyError:
			#print("color not found:", color_attr)
			color = default_color
		
		n = -1
		while color == 'currentColor' or color == 'inherit':
			if color == 'currentColor':
				try:
					color = self.__search_attrib(node if n == -1 else None, ancestors[:(-n if n > 0 else None)], 'color').strip()
				except KeyError:
					color = default_color
			elif color == 'inherit' and n >= 0:
				try:
					color = self.__search_attrib(None, ancestors[:(-n if n > 0 else None)], color_attr).strip()
					#print(node.tag, color_attr, "inherit ->", color)
					#print("inherit:", [_a.tag for _a in ancestors[:(-n if n > 0 else None)]], n)
				except KeyError:
					color = default_color
			n += 1
		
		assert color != 'currentColor' and color != 'inherit'
		
		#color = color.lower()
		
		try:
			color = self.colors[color.lower()]
		except KeyError:
			pass
		
		try:
			if not color or color.lower() in ('none', 'transparent'):
				return False
		except AttributeError:
			pass
		
		try:
			a = float(node.attrib[opacity_attr])
		except KeyError:
			try:
				a = float(node.attrib['opacity'])
			except KeyError:
				a = None
		
		#print(color, a)
		
		if a == 0:
			return False
		
		if color[0] == '#' and len(color) == 4:
			r, g, b = [int(_c, 16) / 15 for _c in color[1:]]
		elif color[0] == '#' and len(color) == 7:
			r, g, b = [int(_c, 16) / 255 for _c in (color[1:3], color[3:5], color[5:7])]
			#print(color, r, g, b)
		elif color[:4] == 'url(' and color[-1] == ')':
			self.__apply_pattern_from_url(ctx, box, node, ancestors, current_url, color)
			# TODO: transparency
		elif color[:4] == 'rgb(' and color[-1] == ')':
			r, g, b = [max(0, min(1, (float(_c) / 255 if _c.strip()[-1] != '%' else float(_c.strip()[:-1]) / 100))) for _c in color[4:-1].split(',')]
		else:
			self.error(f"Unsupported color specification in {color_attr}: {color}", color, node)
		
		try:
			if a == None:
				ctx.set_source_rgb(r, g, b)
			else:
				ctx.set_source_rgba(r, g, b, a)
		except UnboundLocalError:
			pass
		
		#if node.tag == '{http://www.w3.org/2000/svg}rect':
		#	print("rect", color_attr, a, r, g, b)
		
		
		return True
	
	@staticmethod
	def __warp_current_path(ctx, function):
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
	
	def __apply_fill(self, ctx, box, node, ancestors, current_url):
		if not self.__apply_color(ctx, box, node, ancestors, current_url, 'fill', 'fill-opacity', 'black'):
			return False
		
		try:
			fill_rule = self.__search_attrib(node, ancestors, 'fill-rule')
		except KeyError:
			fill_rule = None
		
		if fill_rule == 'evenodd':
			ctx.set_fill_rule(cairo.FillRule.EVEN_ODD)
		elif fill_rule == 'winding':
			ctx.set_fill_rule(cairo.FillRule.WINDING)
		elif fill_rule == 'nonzero':
			self.error(f"Unsupported fill rule: {fill_rule}", fill_rule, node) # TODO
		elif fill_rule == None:
			pass
		else:
			self.error(f"Unsupported fill rule: {fill_rule}", fill_rule, node)
		
		return True
	
	def __apply_stroke(self, ctx, box, node, ancestors, current_url):
		if not self.__apply_color(ctx, box, node, ancestors, current_url, 'stroke', 'stroke-opacity', 'none'):
			return False
		
		try:
			stroke_width = self.__units(str(self.__search_attrib(node, ancestors, 'stroke-width')))
		except KeyError:
			stroke_width = 1
		except ValueError:
			self.error(f"Unsupported stroke spec: {self.__search_attrib(node, ancestors, 'stroke-width')}", self.__search_attrib(node, ancestors, 'stroke-width'), node)
			return False
		
		if stroke_width > 0:
			ctx.set_line_width(stroke_width)
		else:
			return False
		
		try:
			linecap = self.__search_attrib(node, ancestors, 'stroke-linecap')
		except KeyError:
			ctx.set_line_cap(cairo.LINE_CAP_BUTT)
		else:
			if linecap == 'butt':
				ctx.set_line_cap(cairo.LINE_CAP_BUTT)
			elif linecap == 'round':
				ctx.set_line_cap(cairo.LINE_CAP_ROUND)
			elif linecap == 'square':
				ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
			else:
				self.error("Unsupported linecap", linecap, node)
		
		try:
			pathLength = float(node.attrib['pathLength'])
		except KeyError:
			pathLength = None
			pathScale = 1
		else:
			pathScale = self.__get_current_path_length(ctx) / pathLength
		
		try:
			dasharray = self.__search_attrib(node, ancestors, 'stroke-dasharray')
		except KeyError:
			ctx.set_dash([], 0)
		else:
			try:
				dashoffset = float(self.__search_attrib(node, ancestors, 'stroke-dashoffset')) * pathScale
			except KeyError:
				dashoffset = 0
			
			if dasharray != 'none':
				try:
					ctx.set_dash([float(dasharray) * pathScale + 0], dashoffset)
				except ValueError:
					try:
						dashes = [_x * pathScale for _x in map(float, dasharray.split())]
					except ValueError:
						dashes = [_x * pathScale for _x in map(float, dasharray.split(','))]
					ctx.set_dash(dashes, dashoffset)
			else:
				ctx.set_dash([], 0)
		
		'''
		try:
			linejoin = self.__search_attrib(node, 'stroke-linejoin')
		except KeyError:
			pass
		else:
			pass # TODO
		
		try:
			mitterlimit = self.__search_attrib(node, 'stroke-mitterlimit')
		except KeyError:
			pass
		else:
			pass # TODO
		'''
		
		return True
	
	__p_number = r'[+-]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][+-]?\d+)?' # regex pattern matching a floating point number
	
	__re_tokens = re.compile(fr'({__p_number}|[a-zA-Z])')
	
	def __draw_path(self, ctx, box, node, ancestors, level):
		left, top, width, height = box
		
		text = node.attrib['d']
		#print("path:", text)
		
		tokens = (_t for _t in (_t.strip() for _t in self.__re_tokens.split(text)) if (_t and _t != ','))
		
		token = None
		first = True
		
		def next_token():
			nonlocal token, first
			token = next(tokens)
			#print(token)
			first = False
			return token
		
		def next_coord(percentage=None):
			try:
				return self.__units(next_token(), percentage)
			except (ValueError, AttributeError, TypeError) as error:
				raise self.NotANumber(error)
		
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
						#print("C", ctx.get_current_point(), (x1, y1), (x2, y2), (x3, y3))
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x2 - x3, y2 - y3
				
				elif command in 'c':
					while True:
						x1, y1 = next_coord(width), next_coord(height)
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						#print("c", ctx.get_current_point(), (x1, y1), (x2, y2), (x3, y3))
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
					self.error('Unsupported path syntax: %s' % command, tokens, node)
					raise ValueError("Unsupported path syntax")
				
				next_token()
			
			except self.NotANumber:
				continue
			except StopIteration:
				break
			except ValueError as error:
				self.error("Error in path rendering", str(error), node)
				raise
				return
	
	def __apply_font(self, ctx, box, node, ancestors):
		left, top, width, height = box
		
		try:
			font_family = self.__search_attrib(node, ancestors, 'font-family')
		except KeyError:
			font_family = ''
		
		try:
			font_style_attrib = self.__search_attrib(node, ancestors, 'font-style')
		except KeyError:
			font_style = cairo.FontSlant.NORMAL
		else:
			if font_style_attrib == 'normal':
				font_style = cairo.FontSlant.NORMAL
			elif font_style_attrib == 'italic':
				font_style = cairo.FontSlant.ITALIC
			elif font_style_attrib == 'oblique':
				font_style = cairo.FontSlant.OBLIQUE
			else:
				self.error(f"Unsupported font style '{font_style_attrib}'", font_style_attrib, node)
				font_style = cairo.FontSlant.NORMAL
		
		try:
			font_weight_attrib = self.__search_attrib(node, ancestors, 'font-weight')
		except KeyError:
			font_weight = cairo.FontWeight.NORMAL
		else:
			if font_weight_attrib == 'normal':
				font_weight = cairo.FontWeight.NORMAL
			elif font_weight_attrib == 'bold':
				font_weight = cairo.FontWeight.BOLD
			else:
				try:
					font_weight_number = int(font_weight_attrib)
				except ValueError:
					self.error(f"Unsupported font weight '{font_weight_attrib}'", font_weight_attrib, node)
					font_weight = cairo.FontWeight.NORMAL
				else:
					if font_weight_number > 500:
						font_weight = cairo.FontWeight.BOLD
					else:
						font_weight = cairo.FontWeight.NORMAL
		
		try:
			text_anchor = self.__search_attrib(node, ancestors, 'text-anchor').strip()
		except KeyError:
			text_anchor = ''
		
		try:
			font_size_attrib = self.__search_attrib(node, ancestors, 'font-size')
		except KeyError:
			font_size = 12
		else:
			font_size = self.__units(font_size_attrib, percentage=(width + height) / 2)
		
		#print("font size", font_size)
		#print("font family", font_family.split(',')[-1])
		for family in font_family.split(','):
			ctx.select_font_face(family, font_style, font_weight)
		ctx.set_font_size(font_size)
		
		return text_anchor
	
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
	
	def __draw_tspan(self, ctx, box, node, ancestors, level, strip):
		left, top, width, height = box
		ctx.save()
		
		try:
			x = self.__units(node.attrib['x'], percentage=width)
		except KeyError:
			x = 0
		
		try:
			y = self.__units(node.attrib['y'], percentage=height)
		except KeyError:
			y = 0
		
		if x or y:
			ctx.move_to(x, y)
		
		try:
			dx = self.__units(node.attrib['dx'], percentage=width)
		except KeyError:
			dx = 0
		
		try:
			dy = self.__units(node.attrib['dy'], percentage=height)
		except KeyError:
			dy = 0
		
		if dx or dy:
			ctx.rel_move_to(dx, dy)
		
		text_anchor = self.__apply_font(ctx, box, node, ancestors)
		
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
				self.error("Unsupported tag %s" % child.tag, child.tag, child)
				continue
			self.__draw_tspan(ctx, box, child, ancestors + [node], level, strip)
			
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
	
	def __draw_text(self, ctx, box, node, ancestors, level):
		left, top, width, height = box
		
		try:
			x = self.__units(node.attrib['x'], percentage=width)
		except KeyError:
			x = 0
		
		try:
			y = self.__units(node.attrib['y'], percentage=height)
		except KeyError:
			y = 0
		
		ctx.move_to(x, y)
		
		try:
			strip = node.attrib[f'{{{self.xmlns_xml}}}space'] != 'preserve'
		except KeyError:
			strip = True
		
		text_anchor = self.__apply_font(ctx, box, node, ancestors)
		
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
				self.error("Unsupported tag %s" % child.tag, child.tag, child)
				continue
			self.__draw_tspan(ctx, box, child, ancestors + [node], level, strip)
			
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
	
	def __apply_transform(self, ctx, box, node, ancestors, transform_attrib='transform'):
		left, top, width, height = box
		
		try:
			text = node.attrib[transform_attrib]
			#print(transform_attrib, text)
		except KeyError:
			return False
		
		try:
			origin = node.attrib['transform-origin'].split()
		except KeyError:
			origin_x = 0
			origin_y = 0
		else:
			origin_x = self.__units(origin[0], percentage=width)
			origin_y = self.__units(origin[1], percentage=height)
		
		if origin_x or origin_y:
			ctx.translate(origin_x, origin_y)

		n = 0
		while n < len(text):
			#print(text[n:])
			
			match = self.__re_matrix.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("matrix", list(match.groups()))
				m0, m1, m2, m3, m4, m5 = map(float, list(match.groups()))
				transformation = cairo.Matrix(m0, m1, m2, m3, m4, m5)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			match = self.__re_translate.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("translate", list(match.groups()))
				x, y = map(self.__units, list(match.groups()))
				ctx.translate(x, y)
				n = match.end()
				continue
			
			match = self.__re_scale1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("scale1", list(match.groups()))
				s, = map(float, list(match.groups()))
				ctx.scale(s, s)
				n = match.end()
				continue
			
			match = self.__re_scale2.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("scale2", list(match.groups()))
				sx, sy = map(float, list(match.groups()))
				ctx.scale(sx, sy)
				n = match.end()
				continue
			
			match = self.__re_rotate1.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("rotate1", list(match.groups()), node.tag)
				r, = map(float, list(match.groups()))
				ctx.rotate(radians(r))
				n = match.end()
				continue
			
			match = self.__re_rotate3.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("rotate3", list(match.groups()))
				r, cx, cy = map(float, list(match.groups()))
				ctx.translate(cx, cy)
				ctx.rotate(radians(r))
				ctx.translate(-cx, -cy)
				n = match.end()
				continue
			
			match = self.__re_skewX.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("skewX", list(match.groups()))
				a, = map(float, list(match.groups()))
				transformation = cairo.Matrix(1, 0, math.tan(radians(a)), 1, 0, 0)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			match = self.__re_skewY.search(text, n)
			if match and self.__transform_separators(text[n:match.start()]):
				#print("skewY", list(match.groups()))
				a, = map(float, list(match.groups()))
				transformation = cairo.Matrix(1, math.tan(radians(a)), 0, 1, 0, 0)
				ctx.transform(transformation)
				n = match.end()
				continue
			
			self.error("Unsupported transformation: %s" % repr(text[n:]), text[n:], node)
			break
		
		if origin_x or origin_y:
			ctx.translate(-origin_x, -origin_y)
		
		return True
	
	@classmethod
	def __draw_arc(cls, ctx, start_x, start_y, end_x, end_y, radius_x, radius_y, alpha_angle, large_arc_flag, sweep_flag, debug_ctx=None):
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
	
	def __units(self, spec, percentage=None, percentage_origin=0):
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
			scale = self.dpi / 25.4
			value = spec[:-2]
		elif spec[-2:] == 'cm':
			scale = self.dpi / 2.54
			value = spec[:-2]
		elif spec[-2:] == 'in':
			scale = self.dpi
			value = spec[:-2]
		elif spec[-2:] == 'pc':
			scale = self.dpi / 6
			value = spec[:-2]
		elif spec[-2:] == 'pt':
			scale = self.dpi / 72
			value = spec[:-2]
		elif spec[-2:] == 'em':
			scale = 1 # FIXME
			value = spec[:-2]
		elif spec[-1:] == 'Q':
			scale = self.dpi / (2.54 * 40)
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
		
		return float(value) * scale + shift
	

if __debug__ and __name__ == '__main__':
	from pathlib import Path
	from xmlmodel import XMLModel
	
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
		
		def text_extents(self, txt):
			print(self.__name + f'.text_extents("{txt}")')
			return cairo.Rectangle(0, 0, len(txt), 1)
		
		def set_dash(self, dashes, offset):
			print(self.__name + '.set_dash(', repr(dashes), ',', repr(offset), ')')
		
		def __getattr__(self, attr):
			return lambda *args: print(self.__name + '.' + attr + str(args))
	
	class ExtSVGRender(XMLModel, SVGRender):
		def __init__(self):
			XMLModel.__init__(self)
			SVGRender.__init__(self)
		
		def update(self):
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			rnd.render(ctx, (0, 0, 1024, 768))
		
		def scan_link(self, base_url, node):
			SVGRender.scan_link(self, base_url, node)
			XMLModel.scan_link(self, base_url, node)
		
		def render_xml(self, ctx, box, node, ancestors, url, level, draw, pointer):
			if node.tag.startswith(f'{{{self.xmlns_svg}}}') or node.tag.startswith(f'{{{self.xmlns_sodipodi}}}'):
				return SVGRender.render_xml(self, ctx, box, node, ancestors, url, level, draw, pointer)
			else:
				return XMLModel.render_xml(self, ctx, box, node, ancestors, url, level, draw, pointer)
		
		def transform_document(self, url, doc):
			doc = XMLModel.transform_document(self, url, doc)
			doc = SVGRender.transform_document(self, url, doc)
			return doc
	
	for filepath in Path('gfx').iterdir():
		if filepath.suffix != '.svg': continue
		print()
		print(filepath)
		rnd = ExtSVGRender()
		rnd.open(str(filepath))

