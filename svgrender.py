#!/usr/bin/python3
#-*- coding:utf-8 -*-



__all__ = 'render_svg', 'parse_svg_defs', 'parse_svg_links'


import re
import math
from math import pi
from enum import Enum
import cairo
from tinycss2 import parse_declaration_list



xmlns_svg = 'http://www.w3.org/2000/svg'

xmlns_xlink = 'http://www.w3.org/1999/xlink'



class ParseError(Exception):
	pass


def parse_svg_metadata(node):
	title = None
	desc = None
	
	if node.tag != f'{{{xmlns_svg}}}svg':
		raise ParseError("Root element not 'svg'.")
	
	for child in node:
		if child.tag == f'{{{xmlns_svg}}}title':
			title = child.text
		elif child.tag == f'{{{xmlns_svg}}}desc':
			desc = child.text
		elif child.tag == f'{{{xmlns_svg}}}style':
			pass
	
	return title, desc


def parse_svg_defs(node):
	defs = {}
	for child in node:
		try:
			defs[child.attrib['id']] = child
		except KeyError:
			pass
		defs.update(parse_svg_defs(child))
	return defs


def parse_svg_links(node):
	links = set()
	
	if node.tag == f'{{{xmlns_svg}}}use':
		links.add(node.attrib[f'{{{xmlns_xlink}}}href'])
	
	for child in node:
		links.update(parse_svg_links(child))
	
	return links



Mode = Enum('Mode', 'none paint clip')


def render_svg(node, ctx, refs, mode=Mode.paint):
	if node.tag != f'{{{xmlns_svg}}}svg':
		raise ParseError("Root element not 'svg'.")
	
	ctx.save()
	
	try:
		vb_x, vb_y, vb_w, vb_h = map(units, node.attrib['viewBox'].split(' '))
		ctx.translate(-vb_x, -vb_y)
		ctx.scale(1 / vb_w, 1 / vb_h)
	except KeyError:
		pass
	
	parse_group(node, ctx, refs, Mode.paint)
	
	ctx.restore()


def parse_group(node, ctx, refs, mode):
	for child in node:
		parse_node(child, ctx, refs, mode)
		
		


def parse_node(node, ctx, refs, mode):
	if 'transform' in node.attrib:
		ctx.save()
		parse_transform(node, ctx)
	
	shape = False
	
	if node.tag == f'{{{xmlns_svg}}}rect':
		x, y, w, h = map(units, (node.attrib['x'], node.attrib['y'], node.attrib['width'], node.attrib['height']))
		
		try:
			rx = units(node.attrib['rx'])
		except KeyError:
			rx = 0
		
		try:
			ry = units(node.attrib['ry'])
		except KeyError:
			ry = 0
		
		if rx or ry:
			ctx.rounded_rectangle(x, y, w, h, rx, ry)
		else:
			ctx.rectangle(x, y, w, h)
		shape = True
	elif node.tag == f'{{{xmlns_svg}}}circle':
		cx, cy, r = map(units, (node.attrib['cx'], node.attrib['cy'], node.attrib['r']))
		ctx.arc(cx, cy, r, r, 0, 2*pi)
		shape = True
	elif node.tag == f'{{{xmlns_svg}}}ellipse':
		cx, cy, rx, ry = map(units, (node.attrib['cx'], node.attrib['cy'], node.attrib['rx'], node.attrib['ry']))
		ctx.arc(cx, cy, rx, ry, 0, 2*pi)
		shape = True
	elif node.tag == f'{{{xmlns_svg}}}g':
		parse_group(node, ctx, refs, mode)
	elif node.tag == f'{{{xmlns_svg}}}a':
		ctx.tag_begin('a', "href='%s'" % node.attrib[f'{{{xmlns_xlink}}}href'])
		parse_group(node, ctx, refs, mode)
		ctx.tag_end('a')
	elif node.tag == f'{{{xmlns_svg}}}image':
		parse_img(node, ctx)
	elif node.tag == f'{{{xmlns_svg}}}svg':
		render_svg(node, ctx, refs, mode)
	elif node.tag == f'{{{xmlns_svg}}}text':
		parse_text(node, ctx)
		shape = True
	elif node.tag == f'{{{xmlns_svg}}}path':
		parse_path(node, ctx)
		shape = True
	elif node.tag == f'{{{xmlns_svg}}}use':
		use_node = refs[node.attrib[f'{{{xmlns_xlink}}}href']]
		parse_node(use_node, ctx, refs, mode)
	elif node.tag == f'{{{xmlns_svg}}}defs':
		pass
	elif node.tag == f'{{{xmlns_svg}}}metadata':
		pass
	else:
		print(" UNSUPPORTED TAG:", node.tag, node.attrib)
	
	if shape:
		if mode == Mode.paint:
			
			parse_fill(node, ctx, refs)
			parse_stroke(node, ctx, refs)
			ctx.new_path()			
		
		elif mode == Mode.clip:
			ctx.clip()
	
	if 'transform' in node.attrib:
		ctx.restore()

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

filter, flood-color, flood-opacity, font-family, font-size, font-size-adjust, font-stretch, font-style, font-variant, font-weight, glyph-orientation-horizontal, glyph-orientation-vertical, image-rendering, kerning, letter-spacing, lighting-color, marker-end, marker-mid, marker-start, mask, opacity, overflow, pointer-events, shape-rendering, stop-color, stop-opacity, stroke, stroke-dasharray, stroke-dashoffset, stroke-linecap, stroke-linejoin, stroke-miterlimit, stroke-opacity, stroke-width, text-anchor, transform, text-decoration, text-rendering, unicode-bidi, vector-effect, visibility, word-spacing, writing-mode
Filters Attributes
Section
Filter Primitive Attributes

height, result, width, x, y
Transfer Function Attributes

type, tableValues, slope, intercept, amplitude, exponent, offset

'''



def parse_fill(node, ctx, refs):
	fill = None
	fill_opacity = None
	
	try:
		style = node.attrib['style']
		decls = parse_declaration_list(style)
		for decl in decls:
			if decl.name == 'fill':
				if decl.value[0].type == 'hash':
					fill = '#' + decl.value[0].value
				elif decl.value[0].type == 'string':
					fill = decl.value[0].value
				else:
					raise ParseError("Unsupported paint specification type: %s, '%s'", str(decl.value[0].type), str(decl.value[0].value))
			elif decl.name == 'fill-opacity':
				if decl.value[0].type == 'number':
					fill_opacity = decl.value[0].value
				else:
					raise ParseError("Unsupported number specification type:", str(decl.value[0].type))
	except KeyError:
		pass
	
	try:
		fill = node.attrib['fill']
	except KeyError:
		pass
	
	print(fill, fill_opacity)
	
	if not fill or fill.lower() in ('none', 'transparent'):
		return
	
	try:
		fill = colors[fill.lower()]
	except KeyError:
		pass
	
	if fill[0] == '#':
		if len(fill) == 7:
			r = int(fill[1:3], 16) / 255
			g = int(fill[3:5], 16) / 255
			b = int(fill[5:7], 16) / 255
			a = 1
		elif len(fill) == 4:
			r = int(fill[1:2], 16) / 15
			g = int(fill[2:3], 16) / 15
			b = int(fill[3:4], 16) / 15
			a = 1
		else:
			raise ParseError("Unsupported color specification: %s" % fill)
	elif fill[:4] == 'url(' and fill[-1] == ')':
		print("urls not supported yet")
		return
	else:
		raise ParseError("Unsupported paint specification: %s" % fill)
	
	try:
		fill_opacity = float(node.attrib['fill_opacity'])
	except KeyError:
		fill_opacity = 1
	except ValueError as error:
		raise ParseError("Error in float conversion.")
	
	a *= fill_opacity
	
	if a == 1:
		ctx.set_source_rgb(r, g, b)
		print("fill color:", r, g, b)
	else:
		ctx.set_source_rgba(r, g, b, a)
		print("fill color:", r, g, b, a)
	
	if a > 0:
		ctx.fill_preserve()
		print("fill")


def parse_stroke(node, ctx, refs):
	try:
		stroke = node.attrib['stroke']
	except KeyError:
		return
	
	if stroke.lower() in ('none', 'transparent'):
		return
	
	try:
		stroke = colors[stroke.lower()]
	except KeyError:
		pass
	
	if stroke[0] == '#':
		if len(stroke) == 7:
			r = int(stroke[1:3], 16) / 255
			g = int(stroke[3:5], 16) / 255
			b = int(stroke[5:7], 16) / 255
			a = 1
		elif len(stroke) == 4:
			r = int(stroke[1:2], 16) / 15
			g = int(stroke[2:3], 16) / 15
			b = int(stroke[3:4], 16) / 15
			a = 1
		else:
			raise ParseError("Unsupported color specification: %s" % stroke)
	elif stroke[:4] == 'url(' and stroke[-1] == ')':
		print("urls not supported yet")
		return
	else:
		raise ParseError("Unsupported paint specification: %s" % stroke)
		
	if a == 1:
		ctx.set_source_rgb(r, g, b)
	else:
		ctx.set_source_rgba(r, g, b, a)
	
	if a > 0:
		ctx.stroke_preserve()



def parse_img(node, ctx):
	print(" image")


def parse_text(node, ctx):
	x, y = map(units, (node.attrib['x'], node.attrib['y']))
	ctx.move_to(x, y)
	
	if node.text:
		ctx.text_path(node.text)
	
	for child in node:
		if child.tag == f'{{{xmlns_svg}}}tspan':
			try:
				dx = units(child.attrib['dx'])
			except KeyError:
				dx = 0
			try:
				dy = units(child.attrib['dy'])
			except KeyError:
				dy = 0
			
			if dx or dy:
				ctx.rel_move_to(dx, dy)
			
			if child.text:
				ctx.text_path(child.text)
		
		if child.tail:
			ctx.text_path(child.tail)


re_matrix = re.compile(r'matrix\s*\(\s*([^,\s]*)[,\s]+([^,\s]*)[,\s]+([^,\s]*)[,\s]+([^,\s]*)[,\s]+([^,\s]*)[,\s]+([^\)\s]*)\s*\)')

re_translate = re.compile(r'translate\s*\(\s*([^,\s]*)[,\s]+([^\)\s]*)\s*\)')

re_scale1 = re.compile(r'scale\s*\(\s*([^,\)\s]*)\s*\)')

re_scale2 = re.compile(r'scale\s*\(\s*([^,\s]*)[,\s]+([^\)\s]*)\s*\)')

re_rotate = re.compile(r'rotate\s*\(\s*([^,\s]*)\s*\)')

def parse_transform(node, ctx):
	text = node.attrib['transform']
	
	n = 0
	while n < len(text):
		match = re_matrix.search(text, n)
		if match:
			m0, m1, m2, m3, m4, m5 = map(float, list(match.groups()))
			print(m0, m1, m2, m3, m4, m5)
			transformation = cairo.Matrix(m0, m1, m2, m3, m4, m5)
			ctx.transform(transformation)
			n = match.end()
			continue
		
		match = re_translate.search(text, n)
		if match:
			x, y = map(units, list(match.groups()))
			ctx.translate(x, y)
			n = match.end()
			continue
		
		match = re_scale1.search(text, n)
		if match:
			#print(text)
			s, = map(units, list(match.groups()))
			ctx.scale(s, s)
			n = match.end()
			continue
		
		match = re_scale2.search(text, n)
		if match:
			#print(text)
			sx, sy = map(units, list(match.groups()))
			ctx.scale(sx, sy)
			n = match.end()
			continue
		
		match = re_rotate.search(text, n)
		if match:
			r, = map(units, list(match.groups()))
			ctx.rotate(r)
			n = match.end()
			continue
		
		raise ParseError(text)


class NotANumber(BaseException):
	def __init__(self, original):
		self.original = original

re_tokens = re.compile(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[+-]?\.\d+(?:[eE][+-]?\d+)?|\b\s+\b|\w(?=\w))')

def parse_path(node, ctx):
	text = node.attrib['d']
	
	tokens = (_t for _t in (_t.strip() for _t in re_tokens.split(text)) if (_t and _t != ','))
	
	token = None
	
	def next_token():
		nonlocal token
		token = next(tokens)
		return token
	
	def next_coord():
		try:
			return units(next_token())
		except ParseError as error:
			raise NotANumber(error)
	
	next_token()
	
	x = y = 0
	
	while True:
		try:
			command = token
			
			if command in 'M':
				while True:
					x = next_coord()
					y = next_coord()
					ctx.move_to(x, y)
			elif command in 'm':
				while True:
					x = next_coord()
					y = next_coord()
					ctx.rel_move_to(x, y)
			elif command in 'L':
				while True:
					x = next_coord()
					y = next_coord()
					ctx.line_to(x, y)
			elif command in 'l':
				while True:
					x = next_coord()
					y = next_coord()
					ctx.rel_line_to(x, y)
			elif command in 'H':
				while True:
					x = next_coord()
					ctx.line_to(x, y)
			elif command in 'h':
				while True:
					x = next_coord()
					ctx.rel_line_to(x, y)
			elif command in 'V':
				while True:
					y = next_coord()
					ctx.line_to(x, y)
			elif command in 'v':
				while True:
					y = next_coord()
					ctx.rel_line_to(x, y)
			elif command in 'Zz':
				ctx.close_path()
			else:
				raise ParseError('Unsupported command syntax: %s' % text)

			'''
			elif command in 'Qq':
				while do_while:
					cp1 = nextXY()
					cursor = nextXY()
					delta = cursor - cp1
					self.quadraticCurveTo(cp1, cursor)
					do_while = nextIsNumber()
	
			elif command in 'Tt':
				while do_while:
					cp2 = cursor + delta if delta else cursor
					cursor = nextXY()
					delta = cursor - cp2
					self.quadraticCurveTo(cp2, cursor)
					do_while = nextIsNumber()
	
			elif command in 'Cc':
				while do_while:
					cp3 = nextXY()
					cp4 = nextXY()
					cursor = nextXY()
					delta = cursor - cp4
					self.cubicCurveTo(cp3, cp4, cursor)
					do_while = nextIsNumber()
	
			elif command in 'Ss':
				while do_while:
					cp5 = cursor + delta if delta else cursor
					cp6 = nextXY()
					cursor = nextXY()
					delta = cursor - cp6
					self.cubicCurveTo(cp5, cp6, cursor)
					do_while = nextIsNumber()

			elif command in 'Aa':
	
			'''
			
			next_token()
		
		except NotANumber:
			continue
		except StopIteration:
			break





def units(text):
	text = text.strip()
	if not text:
		return 0
	
	if text[-2:] == 'px':
		scale = 1
		value = text[:-2]
	elif text[-2:] == 'ex':
		scale = 1
		value = text[:-2]
	else:
		scale = 1
		value = text
	
	try:
		return float(value)
	except ValueError:
		raise ParseError("Unsupported dimension specification: %s" % text)






# From: http://www.w3.org/TR/SVG11/types.html#ColorKeywords
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




if __name__ == '__main__':
	from xml.etree.ElementTree import ElementTree
	
	document = ElementTree()
	document.parse('/home/bartek/Projekty/guixmpp/gfx/Comparison of several satellite navigation system orbits.svg')
	
	class PseudoContext:
		def __getattr__(self, name):
			return lambda *args: print("ctx." + name + str(args))
	
	ctx = PseudoContext()
	node = document.getroot()
	
	defs = parse_svg_defs(node)
	links = parse_svg_links(node)
	
	print(links)
	print()
	
	refs = {}
	for link in links:
		if link[0] == '#':
			try:
				refs[link] = defs[link[1:]]
			except KeyError:
				pass
	
	render_svg(node, ctx, refs=refs)


'''


quit()

_align_table = {
	'xMinYMin': (0.0, 0.0),
	'xMidYMin': (0.5, 0.0),
	'xMaxYMin': (1.0, 0.0),
	'xMinYMid': (0.0, 0.5),
	'xMidYMid': (0.5, 0.5),
	'xMaxYMid': (1.0, 0.5),
	'xMinYMax': (0.0, 1.0),
	'xMidYMax': (0.5, 1.0),
	'xMaxYMax': (1.0, 1.0),
}




quit()



class _Parser:
	def __init__(self, handler):
		self.matrix = _Matrix()
		self.handler = handler
		self.cursor = _Vector(0, 0)
		self.strokeScale = 1
		self.opacity = 1

	def moveTo(self, p):
		self.cursor = p
		p = self.matrix.transform(p)
		self.handler.move_to(p.x, p.y)

	def lineTo(self, p):
		self.cursor = p
		p = self.matrix.transform(p)
		self.handler.line_to(p.x, p.y)

	def quadraticCurveTo(self, p1, p2):
		c1 = self.cursor + (p1 - self.cursor) * (2.0 / 3.0)
		c2 = p2 + (p1 - p2) * (2.0 / 3.0)
		self.cursor = p2
		self.cubicCurveTo(c1, c2, p2)

	def cubicCurveTo(self, p1, p2, p3):
		self.cursor = p3
		p1 = self.matrix.transform(p1)
		p2 = self.matrix.transform(p2)
		p3 = self.matrix.transform(p3)
		self.handler.curve_to(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y)

	def outlineEllipse(self, cx, cy, rx, ry):
		c = self.matrix.transform(_Vector(cx, cy))
		r = c + self.matrix.transform(_Vector(rx, ry) - _Vector(cx, cy))
		self.handler.arc(c.x, c.y, r.x, r.y)
		#crx = rx * _CIRCLE_APPROXIMATION_CONSTANT
		#cry = ry * _CIRCLE_APPROXIMATION_CONSTANT
		#self.handler.new_path()
		#self.moveTo(_Vector(cx - rx, cy))
		#self.cubicCurveTo(_Vector(cx - rx, cy - cry), _Vector(cx - crx, cy - ry), _Vector(cx, cy - ry))
		#self.cubicCurveTo(_Vector(cx + crx, cy - ry), _Vector(cx + rx, cy - cry), _Vector(cx + rx, cy))
		#self.cubicCurveTo(_Vector(cx + rx, cy + cry), _Vector(cx + crx, cy + ry), _Vector(cx, cy + ry))
		#self.cubicCurveTo(_Vector(cx - crx, cy + ry), _Vector(cx - rx, cy + cry), _Vector(cx - rx, cy))
		#self.handler.close_path()

	def outlineRect(self, x, y, w, h):
		#self.handler.beginPath()
		#self.moveTo(_Vector(x, y))
		#self.lineTo(_Vector(x + w, y))
		#self.lineTo(_Vector(x + w, y + h))
		#self.lineTo(_Vector(x, y + h))
		#self.handler.closePath()
		pass

	def outlineRoundedRect(self, x, y, w, h, rx, ry):
		rx = min(rx, w * 0.5)
		ry = min(ry, h * 0.5)
		crx = rx * (1 - _CIRCLE_APPROXIMATION_CONSTANT)
		cry = ry * (1 - _CIRCLE_APPROXIMATION_CONSTANT)
		self.handler.beginPath()
		self.moveTo(_Vector(x + rx, y))
		self.lineTo(_Vector(x + w - rx, y))
		self.cubicCurveTo(_Vector(x + w - crx, y), _Vector(x + w, y + cry), _Vector(x + w, y + ry))
		self.lineTo(_Vector(x + w, y + h - ry))
		self.cubicCurveTo(_Vector(x + w, y + h - cry), _Vector(x + w - crx, y + h), _Vector(x + w - rx, y + h))
		self.lineTo(_Vector(x + rx, y + h))
		self.cubicCurveTo(_Vector(x + crx, y + h), _Vector(x, y + h - cry), _Vector(x, y + h - ry))
		self.lineTo(_Vector(x, y + ry))
		self.cubicCurveTo(_Vector(x, y + cry), _Vector(x + crx, y), _Vector(x + rx, y))
		self.handler.closePath()

	def visitPath(self, node, style):
		self.handler.beginPath()
		self._path(_attr(node, 'd'))
		self.fillAndStroke(node, style)

	def visitRect(self, node, style):
		x = _units(_attr(node, 'x'))
		y = _units(_attr(node, 'y'))
		w = _units(_attr(node, 'width'))
		h = _units(_attr(node, 'height'))
		rx = _units(_attr(node, 'rx'))
		ry = _units(_attr(node, 'ry'))
		if rx or ry: self.outlineRoundedRect(x, y, w, h, rx, ry)
		else: self.outlineRect(x, y, w, h)
		self.fillAndStroke(node, style)

	def visitLine(self, node, style):
		x1 = _units(_attr(node, 'x1'))
		y1 = _units(_attr(node, 'y1'))
		x2 = _units(_attr(node, 'x2'))
		y2 = _units(_attr(node, 'y2'))
		self.handler.beginPath()
		self.moveTo(_Vector(x1, y1))
		self.lineTo(_Vector(x2, y2))
		self.fillAndStroke(node, style)

	def visitCircle(self, node, style):
		x = _units(_attr(node, 'cx'))
		y = _units(_attr(node, 'cy'))
		r = _units(_attr(node, 'r'))
		self.outlineEllipse(x, y, r, r)
		self.fillAndStroke(node, style)

	def visitEllipse(self, node, style):
		x = _units(_attr(node, 'cx'))
		y = _units(_attr(node, 'cy'))
		rx = _units(_attr(node, 'rx'))
		ry = _units(_attr(node, 'ry'))
		self.outlineEllipse(x, y, rx, ry)
		self.fillAndStroke(node, style)

	def visitPolyline(self, node, style):
		self.handler.beginPath()
		for i, point in enumerate(_points(_attr(node, 'points'))):
			if i: self.lineTo(point)
			else: self.moveTo(point)
		self.fillAndStroke(node, style)

	def visitPolygon(self, node, style):
		self.handler.beginPath()
		for i, point in enumerate(_points(_attr(node, 'points'))):
			if i: self.lineTo(point)
			else: self.moveTo(point)
		self.handler.closePath()
		self.fillAndStroke(node, style)

	def fillAndStroke(self, node, style):
		fill = _attr(node, 'fill') or style.get('fill', 'black')
		stroke = _attr(node, 'stroke') or style.get('stroke', 'none')
		strokeWidth = _attr(node, 'stroke-width') or style.get('stroke-width', '1')

		if fill != 'none':
			c = _color(fill)
			self.handler.fill(c[0], c[1], c[2], c[3] * self.opacity)

		if stroke != 'none':
			c = _color(stroke)
			self.handler.stroke(c[0], c[1], c[2], c[3] * self.opacity, self.strokeScale * _units(strokeWidth))

	def visitViewbox(self, node, data):
		match = re.match(r'^[\s,]*([^\s,]+)[\s,]+([^\s,]+)[\s,]+([^\s,]+)[\s,]+([^\s,]+)[\s,]*$', _attr(node, 'viewBox'))
		if match:
			aspect = _attr(node, 'preserveAspectRatio') or 'xMidYMid'
			x, y, w, h = map(_units, match.groups())
			data.setdefault('width', w)
			data.setdefault('height', h)
			sx = data['width'] / w
			sy = data['height'] / h
			if aspect in _align_table:
				sx = sy = min(sx, sy)
				ax, ay = _align_table[aspect]
				x += (w - data['width'] / sx) * ax
				y += (h - data['height'] / sy) * ay
			self.matrix = _Matrix(sx, 0, -x * sx, 0, sy, -y * sy)
			self.strokeScale = math.sqrt(sx * sy)

	def visitSVG(self, node):
		data = {}
		if _attr(node, 'width'): data['width'] = _units(_attr(node, 'width'))
		if _attr(node, 'height'): data['height'] = _units(_attr(node, 'height'))
		if _attr(node, 'viewBox'): self.visitViewbox(node, data)
		if data: self.handler.metadata(data)

	def visit(self, node):
		old_matrix = self.matrix
		old_opacity = self.opacity

		style = _attr(node, 'style') or ''
		style = dict(tuple(y.strip() for y in x.split(':')) for x in style.split(';') if x)
		self.opacity *= float(_attr(node, 'opacity') or style.get('opacity', '1'))

		if _attr(node, 'transform'):
			self.matrix = self.matrix.multiply(_matrix(_attr(node, 'transform')))

		if node.nodeType == node.ELEMENT_NODE:
			if node.tagName == 'path': self.visitPath(node, style)
			elif node.tagName == 'rect': self.visitRect(node, style)
			elif node.tagName == 'line': self.visitLine(node, style)
			elif node.tagName == 'circle': self.visitCircle(node, style)
			elif node.tagName == 'ellipse': self.visitEllipse(node, style)
			elif node.tagName == 'polyline': self.visitPolyline(node, style)
			elif node.tagName == 'polygon': self.visitPolygon(node, style)
			elif node.tagName == 'svg': self.visitSVG(node)

		for child in node.childNodes:
			self.visit(child)

		self.matrix = old_matrix
		self.opacity = old_opacity






def _color(text):
	text = text.strip()
	text = _color_table.get(text, text)

	if re.match(r'^#[A-Fa-f0-9]{6}$', text):
		value = int(text[1:], 16)
		return (value >> 16 & 255, value >> 8 & 255, value & 255, 1.0)

	if re.match(r'^#[A-Fa-f0-9]{3}$', text):
		value = int(text[1:], 16)
		return ((value >> 8 & 15) * 0x11, (value >> 4 & 15) * 0x11, (value & 15) * 0x11, 1.0)

	match = re.match(r'^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$', text)
	if match:
		return (int(match.group(1)), int(match.group(2)), int(match.group(3)), 1.0)

	match = re.match(r'^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+(?:\.\d+)?|\.\d+)\s*\)$', text)
	if match:
		return (int(match.group(1)), int(match.group(2)), int(match.group(3)), float(match.group(4)))

	raise Exception('Unsupported color syntax: %s' % repr(text))

def _units(text):
	return float(text.replace('px', '')) if text else 0.0 # Only handle pixels for now

def _attr(node, name):
	return node.attributes.get(name).value if node.attributes and node.attributes.get(name) else None


def _points(text):
	tokens = _tokenize(text)
	return [_Vector(float(p[0]), float(p[1])) for p in zip(tokens[::2], tokens[1::2])]

'''

