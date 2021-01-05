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
from tinycss2 import parse_declaration_list, parse_stylesheet
from collections import defaultdict
from copy import deepcopy


try:
	distance = math.dist
except AttributeError:
	def distance(a, b):
		return math.sqrt(sum((_a - _b)**2 for (_a, _b) in zip(a, b)))


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
	

class SVGRender:
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
	
	color_attr = 'stroke', 'fill'
	
	Mode = Enum('Mode', 'none paint clip')
	
	class NotANumber(BaseException):
		def __init__(self, original):
			self.original = original
	
	def __init__(self):
		self.svg_url = None
		self.svg_title = ""
		self.svg_description = ""
		self.__documents = {}
		self.__defs = {}
		self.__stylesheets = []
		self.__parents = {}
	
	def svg_open(self, url):
		self.svg_url = url
		
		if url in self.__documents:
			self.__display(self.__documents[url])
		elif url:
			self.svg_request_url(url)
	
	def svg_request_url(self, url):
		from xml.etree.ElementTree import ElementTree
		document = ElementTree()
		document.parse(url)
		self.svg_register_document(url, document)
	
	def svg_register_document(self, url, document):
		self.__documents[url] = document
		self.__scan_links(url, document.getroot())
		if self.svg_url == url:
			self.__display(document.getroot())
		if self.svg_url in self.__documents:
			self.svg_update()
	
	def svg_clear_documents(self):
		self.__documents = {}
		self.__defs = {}
		self.svg_update()
	
	def svg_update(self):
		pass
	
	def svg_get_document(self, url=None):
		if url == None: url = self.svg_url
		return self.__documents[url]
	
	def svg_render(self, ctx, box, pointer=None):
		try:
			document = self.__documents[self.svg_url]
		except KeyError:
			return [] if pointer else None
		else:
			return self.__render_svg(document.getroot(), ctx, box, True, pointer=pointer)
	
	def svg_alternative_stylesheet(self, node):
		pass
	
	def svg_error(self, message, param, node):
		import sys
		print("SVG error in", self.svg_url, ":", file=sys.stderr)
		print("    ", message, file=sys.stderr)
		print("    ", param, file=sys.stderr)
		print("    ", node.tag, node.attrib, file=sys.stderr)
	
	def __scan_links(self, url, node):
		try:
			self.__defs[url + '#' + node.attrib['id']] = node
		except KeyError:
			pass
		
		if node.tag in (f'{{{self.xmlns_svg}}}use', f'{{{self.xmlns_svg}}}image'):
			url = node.attrib[f'{{{self.xmlns_xlink}}}href']
			if url and (url[0] != '#') and (url not in self.__documents):
				self.__documents[url] = None
				self.svg_request_url(url)
		
		for child in node:
			self.__scan_links(url, child)
	
	def __display(self, node):
		stylesheets = []
		
		for child in node:
			if child.tag == f'{{{self.xmlns_svg}}}title':
				self.svg_title = child.text
			elif child.tag == f'{{{self.xmlns_svg}}}desc':
				self.svg_description = child.text
			elif child.tag == f'{{{self.xmlns_svg}}}defs':
				for subchild in child:
					if subchild.tag != f'{{{self.xmlns_svg}}}style': continue
					
					if ('type' not in subchild.attrib) or (subchild.attrib['type'] == 'text/css'):
						stylesheets.extend(parse_stylesheet(subchild.text))
					else:
						stylesheet = self.svg_alternative_stylesheet(subchild)
						if stylesheet:
							stylesheets.extend(parse_stylesheet(stylesheet))
			
			if child.tag != f'{{{self.xmlns_svg}}}style': continue
			
			if ('type' not in child.attrib) or (child.attrib['type'] == 'text/css'):
				stylesheets.extend(parse_stylesheet(child.text))
			else:
				stylesheet = self.svg_alternative_stylesheet(child)
				if stylesheet:
					stylesheets.append(parse_stylesheet(stylesheet))
		
		self.__stylesheets = stylesheets
		self.__parents = {}
	
	@staticmethod
	def __rounded_rectangle(ctx, x, y, w, h, rx, ry):
		radius = max(rx, ry) # TODO
		ctx.new_sub_path()
		ctx.arc(x + rx, y + ry, radius, radians(180), radians(270))
		ctx.arc(x + w - rx, y + ry, radius, radians(-90), radians(0))
		ctx.arc(x + w - rx, y + h - ry, radius, radians(0), radians(90))
		ctx.arc(x + rx, y + h - ry, radius, radians(90), radians(180))
		ctx.close_path()
	
	def __render_svg(self, node, ctx, box, topmost, mode=Mode.paint, pointer=None):
		left, top, width, height = box
		
		if node.tag != f'{{{self.xmlns_svg}}}svg':
			self.svg_error("Root element not 'svg'.", node.tag, node)
		
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
		
		#ctx.rectangle(0, 0, svg_width, svg_height)
		#ctx.set_source_rgb(1, 0, 0)
		#ctx.set_line_width(5)
		#ctx.set_dash([5], 5)
		#ctx.stroke()
		#unit = ctx.get_matrix()
		
		try:
			vb_x, vb_y, vb_w, vb_h = node.attrib['viewBox'].split()
			
			viewbox_x = self.__units(vb_x, percentage=width)
			viewbox_y = self.__units(vb_y, percentage=height)
			viewbox_w = self.__units(vb_w, percentage=width)
			viewbox_h = self.__units(vb_h, percentage=height)
			
			x_scale = svg_width / viewbox_w
			y_scale = svg_height / viewbox_h
			
			x_scale = y_scale = min(x_scale, y_scale)
			
			ctx.scale(x_scale, y_scale)
			ctx.translate(-viewbox_x, -viewbox_y)
		except KeyError:
			viewbox_x = viewbox_y = 0
			viewbox_w = svg_width
			viewbox_h = svg_height
		
		#ctx.rectangle(viewbox_x, viewbox_y, viewbox_w, viewbox_h)
		#ctx.save()
		#ctx.set_matrix(unit)
		#ctx.set_source_rgb(0, 0, 1)
		#ctx.set_dash([5], 0)
		#ctx.stroke()
		#ctx.restore()
		
		children_under_pointer = self.__render_group(node, ctx, (viewbox_x, viewbox_y, viewbox_w, viewbox_h), mode, pointer, ignore_xy=topmost)
		
		ctx.restore()
		
		if pointer:
			return children_under_pointer
	
	def __render_group(self, node, ctx, box, mode=Mode.paint, pointer=None, ignore_xy=False):
		#print("group", node.tag)
		left, top, width, height = box
		
		if pointer:
			under_pointer = []
		
		if not ignore_xy:
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
		
		#ctx.set_source_rgb(0, 0, 0)
		#ctx.move_to(0, -5)
		#ctx.line_to(0, 5)
		#ctx.move_to(-5, 0)
		#ctx.line_to(5, 0)
		#ctx.set_line_width(1)
		#ctx.stroke()
		#ctx.move_to(10, 10)
		#ctx.text_path(node.attrib.get('id', '?'))
		#ctx.fill()
		
		for child in node:
			self.__parents[child] = node
			children_under_pointer = self.__render_shape(child, ctx, (left, top, width, height), mode, pointer)
			
			if pointer:
				under_pointer.extend(children_under_pointer)
		
		if not ignore_xy and (x or y):
			ctx.restore()
		
		if pointer:
			return under_pointer
	
	def __render_shape(self, node, ctx, box, mode=Mode.paint, pointer=None):
		if node.tag in [f'{{{self.xmlns_svg}}}{_tagname}' for _tagname in ('defs', 'title', 'desc', 'metadata', 'style', 'linearGradient', 'radialGradient', 'script', 'symbol')]:
			return []
		elif node.tag == f'{{{self.xmlns_sodipodi}}}namedview':
			return []
		
		left, top, width, height = box
		
		if pointer:
			under_pointer = []
		
		#style = self.__process_style(node)
		
		if node.tag == f'{{{self.xmlns_svg}}}use':
			transform_present = False # ignore transform on <use/> tag, it will be applied on the target element anyway
		else:
			transform_present = self.__apply_transform(node, ctx, (left, top, width, height))
		
		shape = False
		
		if node.tag == f'{{{self.xmlns_svg}}}switch':
			for child in node:
				satisfied = False
				if satisfied:
					self.__render_shape(child, ctx, box, mode, pointer)
					break
		
		elif node.tag == f'{{{self.xmlns_svg}}}rect':
			x, w, rx = [self.__units(node.attrib.get(_a, '0'), percentage=width) for _a in ('x', 'width', 'rx')]
			y, h, ry = [self.__units(node.attrib.get(_a, '0'), percentage=height) for _a in ('y', 'height', 'ry')]
			
			rx = max(rx, 0)
			ry = max(ry, 0)
			
			if rx or ry:
				self.__rounded_rectangle(ctx, x, y, w, h, rx, ry)
			else:
				ctx.rectangle(x, y, w, h)
			
			shape = True
		
		elif node.tag == f'{{{self.xmlns_svg}}}circle':
			try:
				cx = self.__units(node.attrib['cx'], percentage=width)
			except KeyError:
				cx = 0
			
			try:
				cy = self.__units(node.attrib['cy'], percentage=height)
			except KeyError:
				cy = 0
			
			r = self.__units(node.attrib['r'], percentage=min(width, height)) # FIXME
			ctx.arc(cx, cy, r, 0, 2*pi)
			shape = True
		
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
			shape = True
		
		elif node.tag == f'{{{self.xmlns_svg}}}line':
			x1 = self.__units(node.attrib['x1'], percentage=width)
			y1 = self.__units(node.attrib['y1'], percentage=height)
			x2 = self.__units(node.attrib['x2'], percentage=width)
			y2 = self.__units(node.attrib['y2'], percentage=height)
			ctx.move_to(x1, y1)
			ctx.line_to(x2, y2)
			shape = True
		
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
				shape = True
		
		elif node.tag == f'{{{self.xmlns_svg}}}g':
			#print("start group")
			children_under_pointer = self.__render_group(node, ctx, (left, top, width, height), mode, pointer)
			if pointer:
				under_pointer.extend(children_under_pointer)
			#print("stop group")
		
		elif node.tag == f'{{{self.xmlns_svg}}}a':
			try:
				ctx.tag_begin('a', "href='%s'" % node.attrib[f'{{{self.xmlns_xlink}}}href'])
			except AttributeError:
				pass
			
			children_under_pointer = self.__render_group(node, ctx, (left, top, width, height), mode, pointer)
			if pointer:
				under_pointer.extend(children_under_pointer)
			
			try:
				ctx.tag_end('a')
			except AttributeError:
				pass
		
		elif node.tag == f'{{{self.xmlns_svg}}}svg':
			self.__render_svg(node, ctx, (left, top, width, height), False, mode, pointer)
		
		elif node.tag == f'{{{self.xmlns_svg}}}text':
			self.__draw_text(node, ctx, (left, top, width, height))
			shape = True
		
		elif node.tag == f'{{{self.xmlns_svg}}}path':
			self.__draw_path(node, ctx, (left, top, width, height))
			shape = True
		
		elif node.tag == f'{{{self.xmlns_svg}}}use':
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
			if href[0] == '#': href = self.svg_url + href
			if href in self.__defs:
				use_node = deepcopy(self.__defs[href])
				self.__parents[use_node] = self.__parents[node]
				for attr, val in node.attrib.items():
					use_node.attrib[attr] = val
				#print("use", use_node.tag)
				if use_node.tag == f'{{{self.xmlns_svg}}}symbol':
					#print("render_group")
					assert not transform_present
					transform_present = self.__apply_transform(node, ctx, box)
					children_under_pointer = self.__render_group(use_node, ctx, box, mode, pointer)
				else:
					#print("render_shape")
					children_under_pointer = self.__render_shape(use_node, ctx, box, mode, pointer)
				if pointer:
					under_pointer.extend(children_under_pointer)
		
		elif node.tag == f'{{{self.xmlns_svg}}}image':
			x, w = [self.__units(node.attrib[_a], percentage=width) for _a in ('x', 'width')]
			y, h = [self.__units(node.attrib[_a], percentage=height) for _a in ('y', 'height')]
			
			href = node.attrib[f'{{{self.xmlns_xlink}}}href']
			
			if (href in self.__documents) and (self.__documents[href] != None):
				ctx.save()
				ctx.rectangle(x, y, w, h)
				ctx.clip()
				if mode == self.Mode.paint:
					#ctx.translate(x, y)
					children_under_pointer = self.__render_svg(self.__documents[href].getroot(), ctx, (x, y, w, h), False, mode, pointer)
				ctx.restore()
				if pointer:
					under_pointer.extend(children_under_pointer)
		
		elif node.tag == f'{{{self.xmlns_svg}}}foreignObject':
			x, w = [self.__units(node.attrib[_a], percentage=width) for _a in ('x', 'width')]
			y, h = [self.__units(node.attrib[_a], percentage=height) for _a in ('y', 'height')]
			
			ctx.save()
			ctx.rectangle(x, y, w, h)
			ctx.clip()
			
			# TODO
			self.svg_error("Foreign nodes not supported", None, node)
			ctx.set_source_rgba(0.85, 0.85, 0.85, 0.2)
			ctx.paint()
			shape = True
			
			ctx.restore()
		
		else:
			self.svg_error("UNSUPPORTED TAG: %s %s" % (node.tag, repr(node.attrib)), node.tag, node)
			pass
		
		if shape:
			shape_under_pointer = False
			
			fill = self.__apply_fill(node, ctx)
			if fill:
				if pointer:
					ctx.save()
					ctx.identity_matrix()
					if ctx.in_fill(*pointer):
						shape_under_pointer = True
					ctx.restore()
				
				if mode == self.Mode.paint:
					ctx.fill_preserve()
			
			stroke = self.__apply_stroke(node, ctx)
			if stroke:
				if pointer:
					ctx.save()
					ctx.identity_matrix()
					if ctx.in_stroke(*pointer):
						shape_under_pointer = True
					ctx.restore()
	
				if mode == self.Mode.paint:
					ctx.stroke_preserve()
			
			#print(shape, fill, stroke, mode)
			
			if mode == self.Mode.paint or mode == self.Mode.none:
				ctx.new_path()
			elif mode == Mode.clip:
				ctx.clip()
			
			if shape_under_pointer:
				under_pointer.append(node)
		
		if transform_present:
			ctx.restore()
		
		if pointer:
			return under_pointer
	
	def __apply_pattern_from_url(self, url, ctx, node):
		href = url[4:-1]
		if href[0] == '#': href = self.svg_url + href
		
		try:
			target = self.__defs[href]
			target_style = self.__process_style(target)
		except KeyError:
			self.svg_error("Ref not found: %s" % href, href, node)
			return False
		
		if target.tag == f'{{{self.xmlns_svg}}}linearGradient' or target.tag == f'{{{self.xmlns_svg}}}radialGradient':
			
			if target.tag == f'{{{self.xmlns_svg}}}linearGradient':

				try:
					href = target.attrib[f'{{{self.xmlns_xlink}}}href']
				except KeyError:
					pass
				else:
					if href[0] == '#': href = self.svg_url + href
					orig_target = target
					try:
						target = deepcopy(self.__defs[href])
					except KeyError:
						self.svg_error("Ref not found: %s" % href, href, node)
						return False
					
					for attr, val in orig_target.attrib.items():
						target.attrib[attr] = val
					
					for stop in orig_target:
						for tstop in target:
							if tstop.attrib['id'] == stop['id']:
								target.remove(tstop)
						target.append(stop)
				
				default_x1, default_y1, default_x2, default_y2 = ctx.path_extents()
				
				try:
					spec = target_style['x1']
					if spec[-1] == '%':
						x1 = float(spec[:-1]) / 100 * (default_x2 - default_x1) + default_x1
					else:
						x1 = float(spec) * (default_x2 - default_x1) + default_x1
					#x1 = self.__units(target.attrib['x1'], percentage=default_x2-default_x1, percentage_origin=default_x1)
				except KeyError:
					x1 = default_x1
				except ValueError:
					self.svg_error("Invalid x1 specification in linear gradient.", target.attrib['x1'], target)
					x1 = default_x1
				
				try:
					spec = target_style['y1']
					if spec[-1] == '%':
						y1 = float(spec[:-1]) / 100 * (default_y2 - default_y1) + default_y1
					else:
						y1 = float(spec) * (default_y2 - default_y1) + default_y1
					#y1 = self.__units(target.attrib['y1'], percentage=default_y2-default_y1, percentage_origin=default_y1)
				except KeyError:
					y1 = default_y1
				except ValueError:
					self.svg_error("Invalid y1 specification in linear gradient.", target.attrib['y1'], target)
					y1 = default_y1
				
				try:
					spec = target_style['x2']
					if spec[-1] == '%':
						x2 = float(spec[:-1]) / 100 * (default_x2 - default_x1) + default_x1
					else:
						x2 = float(spec) * (default_x2 - default_x1) + default_x1
					#x2 = self.__units(target.attrib['x2'], percentage=default_x2-default_x1, percentage_origin=default_x1)
				except KeyError:
					x2 = default_x2
				except ValueError:
					self.svg_error("Invalid x2 specification in linear gradient.", target.attrib['x2'], target)
					x2 = default_x2
				
				try:
					spec = target_style['y2']
					if spec[-1] == '%':
						y2 = float(spec[:-1]) / 100 * (default_y2 - default_y1) + default_y1
					else:
						y2 = float(spec) * (default_y2 - default_y1) + default_y1
					#y2 = self.__units(target.attrib['y2'], percentage=default_y2-default_y1, percentage_origin=default_y1)
				except KeyError:
					y2 = default_y1
				except ValueError:
					self.svg_error("Invalid y2 specification in linear gradient.", target.attrib['y2'], target)
					y2 = default_y1
				
				gradient = cairo.LinearGradient(x1, y1, x2, y2)
			
			elif target.tag == f'{{{self.xmlns_svg}}}radialGradient':
				try:
					spec = target_style['r']
					if spec[-1] == '%':
						r = float(spec[:-1]) / 100
					else:
						r = float(spec)
				except KeyError:
					r = 500 # FIXME
				except ValueError:
					self.svg_error("Invalid r specification in radial gradient.", target.attrib['r'], target)
					r = 0
				
				try:
					spec = target_style['cx']
					if spec[-1] == '%':
						cx = float(spec[:-1]) / 100
					else:
						cx = float(spec)
				except KeyError:
					cx = 0
				except ValueError:
					self.svg_error("Invalid cx specification in linear gradient.", target.attrib['cx'], target)
					cx = 0
				
				try:
					spec = target_style['cy']
					if spec[-1] == '%':
						cy = float(spec[:-1]) / 100
					else:
						cy = float(spec)
				except KeyError:
					cy = 0
				except ValueError:
					self.svg_error("Invalid cy specification in linear gradient.", target.attrib['cy'], target)
					cy = 0
				
				gradient = cairo.RadialGradient(cx, cx, 0, cx, cx, r)
			
			for colorstop in target:
				colorstop_style = self.__process_style(colorstop)
				try:
					offset_spec = colorstop_style['offset']
					if offset_spec[-1] == '%':
						offset = float(offset_spec[:-1]) / 100
					else:
						offset = float(offset_spec)
				except KeyError:
					offset = 0
				except ValueError:
					self.svg_error("Error in offset spec of a linear gradient.", colorstop.attrib['offset'], colorstop)
					continue
				
				stop_color = None
				stop_opacity = None
				try:
					for decl in parse_declaration_list(colorstop.attrib['style']):
						if not hasattr(decl, 'name'):
							pass
						elif decl.name == 'stop-color':
							if decl.value[0].type == 'hash':
								stop_color = '#' + decl.value[0].value
							else:
								stop_color = decl.value[0].value
						elif decl.name == 'stop-opacity':
							stop_opacity = decl.value[0].value
				except KeyError:
					pass
				
				try:
					stop_color = colorstop_style['stop-color']
				except KeyError:
					if stop_color == None:
						self.svg_error("Stop color of linear gradient not found.", None, colorstop)
						continue
				
				try:
					stop_opacity = float(colorstop_style['stop-opacity'])
				except KeyError:
					pass
				
				if not stop_color or stop_color.lower() in ('none', 'transparent'):
					continue
				
				try:
					stop_color = self.colors[stop_color.lower()]
				except KeyError:
					pass

				if len(stop_color) not in (4, 7) or stop_color[0] != '#':
					self.svg_error("Unsupported color specification: %s" % stop_color, stop_color, colorstop)
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
			
			ctx.set_source(gradient)
		else:
			self.svg_error("Unsupported fill element: %s" % target.tag, target.tag, node)
			return False
	
	def __process_style(self, node):
		result = {}
		
		styles = []
		
		#print(node.tag)
		
		for stylesheet in self.__stylesheets:
			try:
				qualifier = ''.join(_p.serialize() for _p in stylesheet.prelude).strip()
			except AttributeError:
				continue
			
			match = False
			
			# TODO: xpath matching
			if qualifier[0] == '.' and node.attrib.get('class', None) == qualifier[1:]:
				match = True
			elif qualifier[0] == '#' and node.attrib.get('id', None) == qualifier[1:]:
				match = True
			elif f'{{{self.xmlns_svg}}}{qualifier}' == node.tag:
				match = True
			
			#print(repr(qualifier), repr(node.attrib.get('class', None)), repr(node.attrib.get('id', None)))
			#print(match, (qualifier[0] == '.'), (node.attrib.get('class', None) == qualifier[1:]), (qualifier[0] == '#'), (node.attrib.get('id', None) == qualifier[1:]), (f'{{{self.xmlns_svg}}}{qualifier}' == node.tag))
			
			if match:
				style_decl = ''.join(_p.serialize() for _p in stylesheet.content).strip()
				styles.append(parse_declaration_list(style_decl))
				#print(style_decl)
		
		def ancestors(node):
			yield node
			try:
				yield from ancestors(self.__parents[node])
			except KeyError:
				pass
		
		for cnode in reversed(list(ancestors(node))):
			try:
				style_decl = cnode.attrib['style']
				styles.append(parse_declaration_list(style_decl))
			except KeyError:
				pass
		
		for n, style in enumerate(styles):
			for decl in style:
				try:
					attr = decl.name.strip()
				except AttributeError:
					continue
				val = ''.join((_v.serialize() if _v.type != 'url' else f'url({_v.value})' ) for _v in  decl.value).strip()
				if val != None and attr != 'transform': # transform should not be inherited
					result[attr] = val
		
		if styles:
			for decl in styles[-1]:
				try:
					attr = decl.name.strip()
				except AttributeError:
					continue
				if attr == 'transform':
					val = ''.join((_v.serialize() if _v.type != 'url' else f'url({_v.value})' ) for _v in  decl.value).strip()
					if val != None:
						result[attr] = val
		
		for cnode in reversed(list(ancestors(node))):
			for attr, val in cnode.attrib.items():
				attr = attr.replace('_', '-')
				if attr != 'transform' and val != 'inherit': # transform should not be inherited
					result[attr] = val
		
		if 'transform' in node.attrib:
			result['transform'] = node.attrib['transform']
		
		for attr in result.keys():
			if attr in self.color_attr:
				v = result[attr]
				
				try:
					v = self.colors[v.lower()]
				except KeyError:
					pass
				
				if v[0] == '#':
					if len(v) == 7:
						r = int(v[1:3], 16) / 255
						g = int(v[3:5], 16) / 255
						b = int(v[5:7], 16) / 255
					elif len(v) == 4:
						r = int(v[1:2], 16) / 15
						g = int(v[2:3], 16) / 15
						b = int(v[3:4], 16) / 15
					else:
						self.svg_error("Invalid color spec", v, node)
				elif v[:4] == 'rgb(' and v[-1] == ')':
					r, g, b = (float(_c) / 255 for _c in v[4:-1].split(','))
			
			try:
				result[attr] = r, g, b
				del r, g, b
			except UnboundLocalError:
				pass
		
		return result
	
	def __apply_color(self, node, ctx, color_attr, opacity_attr, default_color):
		style = self.__process_style(node)
		
		try:
			color = style[color_attr]
		except KeyError:
			color = default_color
		
		try:
			if not color or color.lower() in ('none', 'transparent'):
				return False
		except AttributeError:
			pass
		
		if color == 'currentColor':
			try:
				color = style['color']
			except KeyError:
				return False
		
		try:
			a = float(style[opacity_attr])
		except KeyError:
			try:
				a = float(style['opacity'])
			except KeyError:
				a = None
		
		#print(color, a)
		
		if a == 0:
			return False
		
		try:
			r, g, b = color
		except ValueError:
			spec = color
			if spec[:4] == 'url(' and spec[-1] == ')':
				self.__apply_pattern_from_url(spec, ctx, node)
				# TODO: transparency
			else:
				self.svg_error("Unsupported color specification: %s" % spec, spec, node)
		except KeyError:
			ctx.set_source_rgb(0, 0, 0)
		else:
			if a == None:
				ctx.set_source_rgb(r, g, b)
			else:
				ctx.set_source_rgba(r, g, b, a)
		
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
	
	def __apply_fill(self, node, ctx):
		return self.__apply_color(node, ctx, 'fill', 'fill-opacity', (0, 0, 0))
	
	def __apply_stroke(self, node, ctx):
		if not self.__apply_color(node, ctx, 'stroke', 'stroke-opacity', 'none'):
			return False
		
		style = self.__process_style(node)
		
		try:
			stroke_width = self.__units(str(style['stroke-width']))
		except KeyError:
			stroke_width = 1
		except ValueError:
			self.svg_error("Unsupported stroke spec: %s" % style['stroke-width'], style['stroke-width'], node)
			return False
		
		#print("stroke_width", stroke_width)
		if stroke_width > 0:
			ctx.set_line_width(stroke_width)
		else:
			return False
		
		try:
			linecap = style['stroke-linecap']
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
				self.svg_error("Unsupported linecap", linecap, node)
		
		try:
			pathLength = float(style['pathLength'])
		except KeyError:
			pathLength = None
			pathScale = 1
		else:
			pathScale = self.__get_current_path_length(ctx) / pathLength
		
		try:
			dasharray = style['stroke-dasharray']
		except KeyError:
			ctx.set_dash([], 0)
		else:
			try:
				dashoffset = float(style['stroke-dashoffset']) * pathScale
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
		
		try:
			dasharray = style['stroke-linecap']
		except KeyError:
			pass
		else:
			pass # TODO
		
		try:
			dasharray = style['stroke-linejoin']
		except KeyError:
			pass
		else:
			pass # TODO
		
		try:
			dasharray = style['stroke-mitterlimit']
		except KeyError:
			pass
		else:
			pass # TODO
		
		return True
	
	__p_number = r'[+-]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][+-]?\d+)?' # regex pattern matching a floating point number
	
	__re_tokens = re.compile(fr'({__p_number}|[a-zA-Z])')
	
	def __draw_path(self, node, ctx, box):
		left, top, width, height = box
		
		text = node.attrib['d']
		
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
						lx, ly = x3 - x2, y3 - y2
				
				elif command in 'c':
					while True:
						x1, y1 = next_coord(width), next_coord(height)
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						#print("c", ctx.get_current_point(), (x1, y1), (x2, y2), (x3, y3))
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2
				
				elif command in 'S':
					x0, y0 = ctx.get_current_point()
					while True:
						x1, y1 = x0 + lx, y0 + ly
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2
						x0, y0 = x3, y3
				
				elif command in 's':
					while True:
						x1, y1 = lx, ly
						x2, y2 = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2
				
				elif command in 'Q':
					x0, y0 = ctx.get_current_point()
					while True:
						xm, ym = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (2 / 3 * x0 + 1 / 3 * xm), (2 / 3 * y0 + 1 / 3 * ym)
						x2, y2 = (1 / 3 * xm + 2 / 3 * x3), (1 / 3 * ym + 2 / 3 * y3)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2
						x0, y0 = x3, y3
				
				elif command in 'q':
					while True:
						xm, ym = next_coord(width), next_coord(height)
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (1 / 3 * xm), (1 / 3 * ym)
						x2, y2 = (1 / 3 * xm + 2 / 3 * x3), (1 / 3 * ym + 2 / 3 * y3)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2
				
				elif command in 'T':
					x0, y0 = ctx.get_current_point()
					while True:
						xm, ym = x0 + lx, y0 + ly
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (2 / 3 * x0 + 1 / 3 * xm), (2 / 3 * y0 + 1 / 3 * ym)
						x2, y2 = (1 / 3 * xm + 2 / 3 * x3), (1 / 3 * ym + 2 / 3 * y3)
						ctx.curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2
						x0, y0 = x3, y3
				
				elif command in 't':
					while True:
						xm, ym = lx, ly
						x3, y3 = next_coord(width), next_coord(height)
						x1, y1 = (1 / 3 * xm), (1 / 3 * ym)
						x2, y2 = (1 / 3 * xm + 2 / 3 * x3), (1 / 3 * ym + 2 / 3 * y3)
						ctx.rel_curve_to(x1, y1, x2, y2, x3, y3)
						lx, ly = x3 - x2, y3 - y2		
				
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
						
						#debug_surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
						#debug_ctx = cairo.Context(debug_surface)
						#try:
						#	self.__draw_arc(ctx, x_start, y_start, x_stop, y_stop, rx, ry, angle, large_arc_flag, sweep_flag, debug_ctx)
						#except AssertionError as error:
						#	print("error:", repr(error))
						#ctx.set_source_surface(debug_surface)
						#ctx.paint()
						#debug_surface.finish()
						
						'''
						if command == 'a':
							x_mid, y_mid = -x_stop / 2, -y_stop / 2
							x_stop += x_start
							y_stop += y_start
						elif command == 'A':
							x_mid, y_mid = (x_start - x_stop) / 2, (y_start - y_stop) / 2
						
						large_arc_flag = bool(large_arc_flag)
						sweep_flag = bool(sweep_flag)
						
						rx, ry = abs(rx), abs(ry)
						
						angle = radians(angle)
						sin_angle = math.sin(angle)
						cos_angle = math.cos(angle)
						
						print(rx, ry, angle, large_arc_flag, sweep_flag, x_stop, y_stop)
						print(x_mid, y_mid)
						
						x_rot = cos_angle * x_mid + sin_angle * y_mid
						y_rot = -sin_angle * x_mid + cos_angle * y_mid
						
						l = (x_rot / rx)**2 + (y_rot / ry)**2
						if l > 1:
							ls = math.sqrt(l)
							rx *= ls
							ry *= ls
						
						sd = (rx * y_rot)**2 + (ry * x_rot)**2
						sn = (rx * ry)**2 - sd
						print(sn, sd)
						s = math.sqrt(sn / sd)
						
						if large_arc_flag == sweep_flag:
							s = -s
						
						cx_rot = s * rx * y_rot / ry
						cy_rot = -s * ry * x_rot / rx
						
						cx = cos_angle * cx_rot - sin_angle * cy_rot + (x_start + x_stop) / 2
						cy = sin_angle * cx_rot + cos_angle * cy_rot + (y_start + y_stop) / 2
						
						theta = self.__arc_angle((1, 0), ((x_rot - cx_rot) / rx, (y_rot - cy_rot) / ry))
						delta = self.__arc_angle(((x_rot - cx_rot) / rx, (y_rot - cy_rot) / ry), ((-x_rot - cx_rot) / rx, (-y_rot - cy_rot) / ry))
						while delta >= 2 * pi: delta -= 2 * pi
						while delta < 0: delta += 2 * pi
						if not sweep_flag: delta -= 2 * pi
						
						ctx.save()
						#ctx.translate((x_start + x_stop) / 2, (y_start + y_stop) / 2)
						ctx.translate(cx, cy)
						ctx.scale(rx, ry)
						ctx.rotate(angle)
						#ctx.translate(-(x_start + x_stop) / 2, -(y_start + y_stop) / 2)
						
						
						if sweep_flag:
							ctx.arc(0, 0, 1, theta, theta + delta)
						else:
							ctx.arc_negative(0, 0, 1, theta, theta + delta)
						ctx.restore()
						'''
				
				elif command in 'Zz':
					ctx.close_path()
					first = True
				
				else:
					self.svg_error('Unsupported path syntax: %s' % command, tokens, node)
					raise ValueError("Unsupported path syntax")
				
				next_token()
			
			except self.NotANumber:
				continue
			except StopIteration:
				break
			except ValueError as error:
				self.svg_error("Error in path rendering", str(error), node)
				raise
				return
		
		#ctx.close_path()
	
	def __draw_text(self, node, ctx, box):
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
		
		if node.text:
			ctx.text_path(node.text.strip())
		
		for child in node:
			if child.tag == f'{{{self.xmlns_svg}}}tspan':
				ctx.save()
				
				try:
					x = self.__units(child.attrib['x'], percentage=width)
				except KeyError:
					x = None
				
				try:
					y = self.__units(child.attrib['y'], percentage=height)
				except KeyError:
					y = None
				
				if x != None or y != None:
					if x == None: x = 0
					if y == None: y = 0
					ctx.move_to(x, y)
				
				try:
					dx = self.__units(child.attrib['dx'], percentage=width)
				except KeyError:
					dx = 0
				
				try:
					dy = self.__units(child.attrib['dy'], percentage=height)
				except KeyError:
					dy = 0
				
				if dx or dy:
					ctx.rel_move_to(dx, dy)
				
				if child.text:
					ctx.text_path(child.text.strip())
				
				ctx.restore()
			else:
				self.svg_error("Unsupported tag %s" % child.tag, child.tag, child)
			
			if child.tail:
				ctx.text_path(child.tail.strip())
	
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
	
	def __apply_transform(self, node, ctx, box, save_ctx=True):
		left, top, width, height = box
		
		style = self.__process_style(node)
		try:
			text = style['transform']
		except KeyError:
			return False
		
		try:
			origin = style['transform-origin'].split()
		except KeyError:
			#origin_x = width / 2 + left
			#origin_y = height / 2 + top
			origin_x = 0
			origin_y = 0
		else:
			origin_x = self.__units(origin[0], percentage=width)
			origin_y = self.__units(origin[1], percentage=height)
		
		if save_ctx: ctx.save()
		
		#print(box, origin_x, origin_y)
		#
		#ctx.move_to(0, -5)
		#ctx.line_to(0, 5)
		#ctx.move_to(-5, 0)
		#ctx.line_to(5, 0)
		#ctx.set_source_rgb(1, 0, 0)
		#ctx.save()
		#ctx.set_line_width(1)
		#ctx.stroke()
		#ctx.restore()
		
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
			
			self.svg_error("Unsupported transformation: %s" % repr(text[n:]), text[n:], node)
			break
		
		if origin_x or origin_y:
			ctx.translate(-origin_x, -origin_y)
		
		#ctx.move_to(-5, -5)
		#ctx.line_to(5, 5)
		#ctx.move_to(-5, 5)
		#ctx.line_to(5, -5)
		#ctx.set_source_rgb(0, 1, 0)
		#ctx.save()
		#ctx.set_line_width(1)
		#ctx.stroke()
		#ctx.restore()
		
		return True
	
	@staticmethod
	def __arc_angle(u, v):
		ux, uy = u
		vx, vy = v
		
		dot = ux * vx + uy * vy
		len_ = math.sqrt((ux**2 + uy**2) * (vx**2 + vy**2))
		ang = math.acos(min(max(dot / len_, -1), 1))
		
		if ux * vy - uy * vx < 0:
			ang = -ang
		return ang
	
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
		
		less_x = chord_x / (radius_x * (math.cos(start_angle) -  math.cos(end_angle)))
		less_y = chord_y / (radius_y * (math.sin(start_angle) -  math.sin(end_angle)))
		less = max(less_x, less_y)
		
		if less > 1:
			radius_x *= less
			radius_y *= less
		
		center_x = (start_x + end_x - radius_x * (math.cos(start_angle + alpha_angle) + math.cos(end_angle + alpha_angle))) / 2
		center_y = (start_y + end_y - radius_y * (math.sin(start_angle + alpha_angle) + math.sin(end_angle + alpha_angle))) / 2
		
		ctx.save()
		ctx.translate(center_x, center_y)
		ctx.rotate(alpha_angle)
		ctx.scale(radius_x, radius_y)
		ctx.translate(-center_x, -center_y)
		
		start_angle_scaled = math.tan((radius_y / radius_x) * math.atan(start_angle - alpha_angle))
		end_angle_scaled = math.tan((radius_y / radius_x) * math.atan(end_angle - alpha_angle))
		
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
		
		try:
			assert mid_x / (-2* sin_mid_angle) == mid_y / (2 * cos_mid_angle) + epsilon, "identity 1"
			assert mid_x / mid_y == -math.tan((start_angle + end_angle) / 2) + epsilon, "identity 2"
			#assert start_x == center_x + radius_x * math.cos(start_angle) + epsilon, "identity 5"
			#assert start_y == center_y + radius_y * math.sin(start_angle) + epsilon, "identity 6"
			#assert end_x == center_x + radius_x * math.cos(end_angle) + epsilon, "identity 7"
			#assert end_y == center_y + radius_y * math.sin(end_angle) + epsilon, "identity 8"
		except ZeroDivisionError:
			pass
	
	@staticmethod
	def __units(spec, percentage=None, percentage_origin=0):
		spec = spec.strip()
		if not spec:
			return 0
		
		shift = 0
		
		if spec[-2:] == 'px':
			scale = 1
			value = spec[:-2]
		elif spec[-2:] == 'ex':
			scale = 1
			value = spec[:-2]
		elif spec[-2:] == 'mm':
			scale = 96 / 25.4
			value = spec[:-2]
		elif spec[-2:] == 'cm':
			scale = 96 / 2.54
			value = spec[:-2]
		elif spec[-2:] == 'in':
			scale = 96
			value = spec[:-2]
		elif spec[-2:] == 'pc':
			scale = 96 / 6
			value = spec[:-2]
		elif spec[-2:] == 'pt':
			scale = 96 / 72
			value = spec[:-2]
		elif spec[-2:] == 'em':
			scale = 1 # FIXME
			value = spec[:-2]
		elif spec[-1:] == 'Q':
			scale = 96 / (2.54 * 40)
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




if __name__ == '__main__':
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
		
		def path_extents(self):
			print(self.__name + '.path_extents()')
			return 0, 0, 1, 1
		
		def set_dash(self, dashes, offset):
			print(self.__name + '.set_dash(', repr(dashes), ',', repr(offset), ')')
		
		def __getattr__(self, attr):
			return lambda *args: print(self.__name + '.' + attr + str(args))
	
	gfx = Path('gfx')
	
	class SVGRenderGfx(SVGRender):
		def svg_request_url(self, url):
			if url.startswith('data:'):
				pass
			elif url == 'espresso.svg':
				super().svg_request_url(str(gfx / url))
				self.svg_register_document(url, self.svg_get_document(str(gfx / url)))
			else:
				super().svg_request_url(url)
	
	for filepath in gfx.iterdir():
		if filepath.suffix != '.svg': continue
		print(filepath)
		if not str(filepath).startswith('gfx/typographer_caps.svg'): continue
		rnd = SVGRenderGfx()
		rnd.svg_open(str(filepath))
		ctx = PseudoContext(f'Context("{str(filepath)}")')
		rnd.svg_render(ctx, (0, 0, 1024, 768))


'''

id, lang, tabindex, xml:base, xml:lang, xml:space
Style Attributes

class, style
Conditional Processing Attributes

externalResourcesRequired, requiredExtensions, requiredFeatures, systemLanguage.
XLink Attributes
Section

xlink:href, xlink:type, xlink:role, xlink:arcrole, xlink:title, xlink:show, xlink:actuate
Presentation Attributes
Section
Note that all SVG presentation attributes can be used as CSS properties.

alignment-baseline, baseline-shift, clip, clip-path, clip-rule
color, color-interpolation, color-interpolation-filters, color-profile, color-rendering

cursor, direction, display, dominant-baseline, enable-background
fill, fill-opacity, fill-rule

filter, flood-color, flood-opacity, font-family, font-size, font-size-adjust, font-stretch, font-style, font-variant, font-weight, glyph-orientation-horizontal, glyph-orientation-vertical, image-rendering, kerning, letter-spacing, lighting-color, marker-end, marker-mid, marker-start, mask, opacity, overflow, pointer-events, shape-rendering, stop-color, stop-opacity

stroke, stroke-dasharray, stroke-dashoffset, stroke-linecap, stroke-linejoin, stroke-miterlimit, stroke-opacity, stroke-width

text-anchor, transform, text-decoration, text-rendering, unicode-bidi, vector-effect, visibility, word-spacing, writing-mode
Filters Attributes
Section
Filter Primitive Attributes

height, result, width, x, y
Transfer Function Attributes

type, tableValues, slope, intercept, amplitude, exponent, offset

'''

