#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTMLRender',


if __name__ == '__main__':
	import sys
	del sys.path[0]


import re
import math
from enum import Enum
import cairo
from collections import defaultdict, namedtuple
from weakref import WeakKeyDictionary
from itertools import chain, starmap
from urllib.parse import quote as url_quote
from colorsys import hls_to_rgb
import unicodedata


import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo


if __name__ == '__main__':
	from guixmpp.format.xml import XMLFormat
	from guixmpp.format.css import CSSFormat
else:
	from ..format.xml import XMLFormat
	from ..format.css import CSSFormat


def once(old_method):
	def new_method(self, *args):
		if getattr(self, '__once_' + old_method.__name__, True):
			setattr(self, '__once_' + old_method.__name__, False)
			return old_method(self, *args)
	new_method.__name__ = old_method.__name__
	return new_method


inf = float('inf')


Gravity = Enum('Gravity', 'TOP_LEFT TOP TOP_RIGHT LEFT CENTER RIGHT BOTTOM_LEFT BOTTOM BOTTOM_RIGHT')


class Box:
	def __init__(self, node, pseudoelement, inline, gravity, width=None, min_width=0, grow_width=1, max_width=inf, height=None, min_height=0, grow_height=1, max_height=inf, x_shift=0, y_shift=0):
		if not (hasattr(node, 'tag') or node is None):
			raise ValueError(f"`node` must be an XML node or None, got {type(node)}.")
		
		if not (isinstance(pseudoelement, str) or pseudoelement is None):
			raise ValueError(f"`pseudoelement` must be a string or None, got {type(pseudoelement)}.")
		
		if not isinstance(inline, bool):
			raise ValueError("`inline` must be a bool.")
		
		if not isinstance(gravity, Gravity):
			raise ValueError("`gravity` must be a `Gravity` value.")
		
		self.node = node
		self.pseudoelement = pseudoelement
		self.inline = inline
		self.gravity = gravity
		self.min_width = min_width if width is None else width
		self.max_width = max_width if width is None else width
		self.grow_width = grow_width if (self.min_width < self.max_width) else 0
		self.min_height = min_height if height is None else height
		self.max_height = max_height if height is None else height
		self.grow_height = grow_height if (self.min_height < self.max_height) else 0
		self.x_shift = x_shift
		self.y_shift = y_shift
		
		if self.x_shift == inf: raise ValueError("X shift can not be inf.")
		if self.y_shift == inf: raise ValueError("Y shift can not be inf.")
		if self.min_width == inf: raise ValueError("Min width can not be inf.")
		if self.min_height == inf: raise ValueError("Min height can not be inf.")
		if not self.min_width <= self.max_width: raise ValueError(f"Min width must be no greater than max width ({self.min_width} vs. {self.max_width}).")
		if not self.min_height <= self.max_height: raise ValueError(f"Min height must be no greater than max height ({self.min_height} vs. {self.max_height}).")
	
	def render(self, model, view, ctx, box, pointer=None):
		if pointer:
			return []
	
	def print_tree(self, level=0):
		yield level, self
	
	def overflow(self, box):
		x, y, w, h = box
		return (self.min_width - w) if (w < self.min_width) else (w - self.max_width) if (w > self.max_width) else 0, (self.min_height - h) if (h < self.min_height) else (h - self.max_height) if (h > self.max_height) else 0


if __debug__:
	class ColorfulBox(Box):
		def __init__(self, label, children, *args, **kwargs):
			self.label = label
			self.children = children
			super().__init__(*args, **kwargs)
		
		def render(self, model, view, ctx, box, pointer=None):
			x, y, w, h = box
			
			ctx.set_line_width(1)
			ctx.set_source_rgb(0, 1, 0)
			ctx.rectangle(x, y, w, h)
			ctx.stroke()
			ctx.move_to(x, y)
			ctx.rel_line_to(w, h)
			ctx.stroke()
			ctx.move_to(x + w, y)
			ctx.rel_line_to(-w, h)
			ctx.stroke()
			
			if self.gravity == Gravity.TOP_LEFT:
				tx, ty = x, y
			elif self.gravity == Gravity.TOP:
				tx, ty = x + w / 2, y
			elif self.gravity == Gravity.TOP_RIGHT:
				tx, ty = x + w, y
			elif self.gravity == Gravity.LEFT:
				tx, ty = x, y + h / 2
			elif self.gravity == Gravity.CENTER:
				tx, ty = x + w / 2, y + h / 2
			elif self.gravity == Gravity.RIGHT:
				tx, ty = x + w, y + h / 2
			elif self.gravity == Gravity.BOTTOM_LEFT:
				tx, ty = x, y + h
			elif self.gravity == Gravity.BOTTOM:
				tx, ty = x + w / 2, y + h
			elif self.gravity == Gravity.BOTTOM_RIGHT:
				tx, ty = x + w, y + h
			
			ctx.set_line_width(1)
			ctx.set_source_rgb(0, 0, 1)
			ctx.move_to(tx, ty)
			ctx.rel_line_to(self.x_shift, self.y_shift)
			ctx.stroke()
			
			tx += self.x_shift
			ty += self.y_shift
			ctx.set_source_rgb(1, 0, 0)
			ctx.arc(tx, ty, 5, 0, 2 * math.pi)
			ctx.fill()
			
			for child in self.children:
				cw = max(child.min_width, min(w, child.max_width))
				ch = max(child.min_height, min(h, child.max_height))
				
				if self.gravity == Gravity.TOP_LEFT:
					cx, cy = x, y
				elif self.gravity == Gravity.TOP:
					cx, cy = x + (w - cw) / 2, y
				elif self.gravity == Gravity.TOP_RIGHT:
					cx, cy = x + (w - cw), y
				elif self.gravity == Gravity.LEFT:
					cx, cy = x, y + (h - ch) / 2
				elif self.gravity == Gravity.CENTER:
					cx, cy = x + (w - cw) / 2, y + (h - ch) / 2
				elif self.gravity == Gravity.RIGHT:
					cx, cy = x + (w - cw), y + (h - ch) / 2
				elif self.gravity == Gravity.BOTTOM_LEFT:
					cx, cy = x, y + (h - ch)
				elif self.gravity == Gravity.BOTTOM:
					cx, cy = x + (w - cw) / 2, y + (h - ch)
				elif self.gravity == Gravity.BOTTOM_RIGHT:
					cx, cy = x + (w - cw), y + (h - ch)
				cx -= child.x_shift
				cy -= child.y_shift
				
				child.render(model, view, ctx, (cx, cy, cw, ch), pointer)
			
			ctx.set_line_width(5)
			ctx.set_font_size(25)
			ctx.move_to(x + 10, y + 30)
			ctx.text_path(self.label)
			ctx.set_source_rgb(1, 1, 1)
			ctx.stroke_preserve()
			ctx.set_source_rgb(0, 0, 0)
			ctx.fill()


class Whitespace(Box):
	def render(self, model, view, ctx, box, pointer=None):
		if pointer: return []
		pass


class Word(Box):
	def __init__(self, text, dx, dy, *args, **kwargs):
		self.text = text
		self.dx = dx
		self.dy = dy
		super().__init__(*args, **kwargs)
	
	def render(self, model, view, ctx, box, pointer=None):
		assert not any(_x == inf for _x in box)
		x, y, w, h = box
		
		if self.gravity == Gravity.TOP_LEFT:
			tx, ty = x, y
		elif self.gravity == Gravity.TOP:
			tx, ty = x + max(0, w - self.max_width) / 2, y
		elif self.gravity == Gravity.TOP_RIGHT:
			tx, ty = x + max(0, w - self.max_width), y
		elif self.gravity == Gravity.LEFT:
			tx, ty = x, y + max(0, h - self.min_height) / 2
		elif self.gravity == Gravity.CENTER:
			tx, ty = x + max(0, w - self.max_width) / 2, y + max(0, h - self.min_height) / 2
		elif self.gravity == Gravity.RIGHT:
			tx, ty = x + max(0, w - self.max_width), y + max(0, h - self.min_height) / 2
		elif self.gravity == Gravity.BOTTOM_LEFT:
			tx, ty = x, y + max(0, h - self.min_height)
		elif self.gravity == Gravity.BOTTOM:
			tx, ty = x + max(0, w - self.max_width) / 2, y + max(0, h - self.min_height)
		elif self.gravity == Gravity.BOTTOM_RIGHT:
			tx, ty = x + max(0, w - self.max_width), y + max(0, h - self.min_height)
		
		ctx.move_to(tx + self.dx, ty + self.dy)
		ctx.text_path(self.text)
		
		if pointer:
			nodes_under_pointer = []
			px, py = ctx.device_to_user(*pointer)
			if ctx.in_clip(px, py):
				if ctx.in_fill(px, py):
					nodes_under_pointer.append(self.node)
			ctx.new_path()
			return nodes_under_pointer
		else:
			ctx.set_source_rgb(0, 0, 0)
			ctx.fill()
		
		#ctx.set_line_width(1)
		#ctx.rectangle(x, y, w, h)
		#ctx.set_source_rgb(0, 1, 0)
		#ctx.stroke()
		#ctx.move_to(tx + self.dx, ty + self.dy)
		#ctx.rel_line_to(self.min_width, 0)
		#ctx.set_source_rgb(0, 0, 1)
		#ctx.stroke()


class Object(Box):
	def __init__(self, document, *args, **kwargs):
		self.document = document
		super().__init__(*args, **kwargs)
	
	def render(self, model, view, ctx, box, pointer=None):
		if not pointer:
			model.draw_image(view, self.document, ctx, box)
		else:
			return model.poke_image(view, self.document, ctx, box, *pointer)


class Row(Box):
	def __init__(self, children, font_size, *args, **kwargs):
		self.children = children
		self.font_size = font_size
		
		min_width = kwargs.get('min_width', sum(_child.min_width for _child in self.children) if self.children else 0)
		grow_width = kwargs.get('grow_width', sum(_child.grow_width for _child in self.children) if self.children else 0)
		max_width = kwargs.get('max_width', sum(_child.max_width for _child in self.children) if self.children else 0)
		min_height = kwargs.get('min_height', max(_child.min_height for _child in self.children) if self.children else 0)
		grow_height = kwargs.get('grow_height', sum(_child.grow_height for _child in self.children) if self.children else 0)
		max_height = kwargs.get('max_height', min(_child.max_height for _child in self.children) if self.children else 0)
		
		for arg in ['min_width', 'grow_width', 'max_width', 'min_height', 'grow_height', 'max_height']:
			kwargs.pop(arg, None)
		
		super().__init__(*args, min_width=min_width, grow_width=grow_width, max_width=max_width, min_height=min_height, grow_height=grow_height, max_height=max_height, **kwargs)
	
	def render(self, model, view, ctx, box, pointer=None):
		assert not any(_x == inf for _x in box)
		x, y, w, h = box
		
		if pointer:
			px, py = pointer
			if not ((x <= px < x + w) and (y <= py < y + h)):
				return []
		
		ctx.save()
		ctx.set_font_size(self.font_size)
		
		lw = max(self.min_width, min(w, self.max_width))
		allocated_space = [_child.min_width for _child in self.children]
		extra_space = lw - sum(allocated_space)
		weights = sum(_child.grow_width for (_n, _child) in enumerate(self.children) if allocated_space[_n] < _child.max_width)
		while extra_space > 0 and weights > 0:
			for n, child in enumerate(self.children):
				if allocated_space[n] >= child.max_width: continue
				allocated_space[n] += extra_space * child.grow_width / weights
				if allocated_space[n] > child.max_width:
					allocated_space[n] = child.max_width
			extra_space = lw - sum(allocated_space)
			weights = sum(_child.grow_width for (_n, _child) in enumerate(self.children) if allocated_space[_n] < _child.max_width)
		
		assert all(_x >= 0 for _x in allocated_space)
		
		if pointer:
			nodes_under_pointer = []
		
		if self.gravity in {Gravity.TOP_LEFT, Gravity.LEFT, Gravity.BOTTOM_LEFT}:
			ax = x
		elif self.gravity in {Gravity.TOP, Gravity.CENTER, Gravity.BOTTOM}:
			ax = x + (w - sum(allocated_space)) / 2
		elif self.gravity in {Gravity.TOP_RIGHT, Gravity.RIGHT, Gravity.BOTTOM_RIGHT}:
			ax = x + w - sum(allocated_space)
		else:
			raise ValueError
		
		for n, child in enumerate(self.children):
			aw = allocated_space[n]
			cw = max(child.min_width, min(aw, child.max_width))
			ch = max(child.min_height, min(h, child.max_height))
			
			cx = ax
			
			if self.gravity in {Gravity.TOP_LEFT, Gravity.TOP, Gravity.TOP_RIGHT}:
				cy = y
			elif self.gravity in {Gravity.LEFT, Gravity.CENTER, Gravity.RIGHT}:
				cy = y + (h - ch) / 2
			elif self.gravity in {Gravity.BOTTOM_LEFT, Gravity.BOTTOM, Gravity.BOTTOM_RIGHT}:
				cy = y + (h - ch)
			else:
				raise ValueError
			
			cx += child.x_shift
			cy += child.y_shift
			
			assert cw != inf
			assert ch != inf
			assert cx != inf
			assert y != inf
			assert h != inf
			assert child.y_shift != inf
			assert cy != inf
			
			if pointer:
				nodes_under_pointer.extend(child.render(model, view, ctx, (cx, cy, cw, ch), pointer))
			else:
				child.render(model, view, ctx, (cx, cy, cw, ch), pointer)
			
			#print((cx, cy, cw, ch))
			ax += aw
		
		if pointer and nodes_under_pointer:
			nodes_under_pointer.append(self.node)
		
		#ctx.set_line_width(1)
		#ctx.rectangle(x, y, w, h)
		#ctx.set_source_rgb(0, 1, 1)
		#ctx.stroke()
		
		#print(allocated_space)
		
		ctx.restore()
		
		if pointer:
			return nodes_under_pointer
	
	def print_tree(self, level=0):
		yield from super().print_tree(level)
		for child in self.children:
			yield from child.print_tree(level + 1)


class Column(Box):
	def __init__(self, children, font_size, *args, **kwargs):
		self.children = children
		self.font_size = font_size
		
		min_width = kwargs.get('min_width', max(_child.min_width for _child in self.children) if self.children else 0)
		grow_width = kwargs.get('grow_width', sum(_child.grow_width for _child in self.children) if self.children else 0)
		max_width = kwargs.get('max_width', min(_child.max_width for _child in self.children) if self.children else 0)
		min_height = kwargs.get('min_height', sum(_child.min_height for _child in self.children) if self.children else 0)
		grow_height = kwargs.get('grow_height', sum(_child.grow_height for _child in self.children) if self.children else 0)
		max_height = kwargs.get('max_height', sum(_child.max_height for _child in self.children) if self.children else 0)
		
		for arg in ['min_width', 'grow_width', 'max_width', 'min_height', 'grow_height', 'max_height']:
			kwargs.pop(arg, None)
		
		super().__init__(*args, min_width=min_width, grow_width=grow_width, max_width=max_width, min_height=min_height, grow_height=grow_height, max_height=max_height, **kwargs)
	
	def render(self, model, view, ctx, box, pointer=None):
		x, y, w, h = box
		
		if pointer:
			px, py = pointer
			if not ((x <= px < x + w) and (y <= py < y + h)):
				return []
		
		ctx.save()
		ctx.set_font_size(self.font_size)
		
		lh = max(self.min_height, min(h, self.max_height))
		allocated_space = [_child.min_height for _child in self.children]
		extra_space = lh - sum(allocated_space)
		weights = sum(_child.grow_height for (_n, _child) in enumerate(self.children) if allocated_space[_n] < _child.max_height)
		while extra_space > 0 and weights > 0:
			for n, child in enumerate(self.children):
				if allocated_space[n] >= child.max_height: continue
				allocated_space[n] += extra_space * child.grow_height / weights
				if allocated_space[n] > child.max_height:
					allocated_space[n] = child.max_height
			extra_space = lh - sum(allocated_space)
			weights = sum(_child.grow_height for (_n, _child) in enumerate(self.children) if allocated_space[_n] < _child.max_height)
		
		if pointer:
			nodes_under_pointer = []
		
		if self.gravity in {Gravity.TOP_LEFT, Gravity.TOP, Gravity.TOP_RIGHT}:
			ay = y
		elif self.gravity in {Gravity.LEFT, Gravity.CENTER, Gravity.RIGHT}:
			ay = y + (h - sum(allocated_space)) / 2
		elif self.gravity in {Gravity.BOTTOM_LEFT, Gravity.BOTTOM, Gravity.BOTTOM_RIGHT}:
			ay = y + h - sum(allocated_space)
		else:
			raise ValueError
		
		for n, child in enumerate(self.children):
			ah = allocated_space[n]
			cw = max(child.min_width, min(w, child.max_width))
			ch = max(child.min_height, min(ah, child.max_height))
			
			if self.gravity in {Gravity.TOP_LEFT, Gravity.LEFT, Gravity.BOTTOM_LEFT}:
				cx = x
			elif self.gravity in {Gravity.TOP, Gravity.CENTER, Gravity.BOTTOM}:
				cx = x + (w - cw) / 2
			elif self.gravity in {Gravity.TOP_RIGHT, Gravity.RIGHT, Gravity.BOTTOM_RIGHT}:
				cx = x + (w - cw)
			else:
				raise ValueError
			
			cy = ay
			
			cx += child.x_shift
			cy += child.y_shift
			
			if pointer:
				nodes_under_pointer.extend(child.render(model, view, ctx, (cx, cy, cw, ch), pointer))
			else:
				child.render(model, view, ctx, (cx, cy, cw, ch), pointer)
			
			ay += ah
		
		if pointer and nodes_under_pointer:
			nodes_under_pointer.append(self.node)
		
		ctx.restore()
		
		if pointer:
			return nodes_under_pointer
	
	def print_tree(self, level=0):
		yield from super().print_tree(level)
		for child in self.children:
			yield from child.print_tree(level + 1)


class HTMLRender:
	xmlns_xml = XMLFormat.xmlns_xml
	xmlns_xlink = XMLFormat.xmlns_xlink
	
	xmlns_html = 'http://www.w3.org/1999/xhtml'
	xmlns_html2 = 'http://www.w3.org/2002/06/xhtml2'
	
	__whitespace_chars = {"\n", "\r", "\t", " "}
	
	def __init__(self, *args, **kwargs):
		self.__css_matcher = WeakKeyDictionary()
	
	def create_document(self, data, mime):
		if mime == 'application/xhtml' or mime == 'application/xhtml+xml':
			document = self.create_document(data, 'application/xml')
		elif mime == 'text/html':
			document = self.create_document(data, 'application/sgml')
		else:
			return NotImplemented
		
		if '}' not in document.getroot().tag:
			root = self.__modify_tree(document.getroot(), lambda _element: self.__add_namespace(_element, None, self.xmlns_html))
			document._setroot(root)
		
		if self.is_html_document(document):
			return document
		else:
			raise ValueError("Not an HTML document.")
	
	def destroy_document(self, document):
		if not self.is_html_document(document):
			return NotImplemented
	
	def is_html_document(self, document):
		if self.is_xml_document(document): # full XML document
			return document.getroot().tag.startswith('{' + self.xmlns_html + '}') or document.getroot().tag.startswith('{' + self.xmlns_html2 + '}')
		else: # XML fragment
			try:
				return document.tag.startswith('{' + self.xmlns_html + '}') or document.tag.startswith('{' + self.xmlns_html2 + '}')
			except AttributeError:
				return False
	
	"css_attribute: initial_value, is_inheritable"
	__initial_attribute = {
		'accent-color': ('auto', True),
		'align-content': ('stretch', False),
		'align-items': ('stretch', False),
		'align-self': ('auto', False),
		'all': ('', False),
		'animation': ('', False),
		'animation-composition': ('replace', False),
		'animation-delay': ('0s', False),
		'animation-direction': ('normal', False),
		'animation-duration': ('0s', False),
		'animation-fill-mode': ('none', False),
		'animation-iteration-count': ('1', False),
		'animation-name': ('none', False),
		'animation-play-state': ('running', False),
		'animation-timing-function': ('ease', False),
		'appearance': ('none', False),
		'aspect-ratio': ('auto', False),
		'backdrop-filter': ('none', False),
		'backface-visibility': ('visible', False),
		'background': ('', False),
		'background-attachment': ('scroll', False),
		'background-blend-mode': ('normal', False),
		'background-clip': ('border-box', False),
		'background-color': ('transparent', False),
		'background-image': ('none', False),
		'background-origin': ('padding-box', False),
		'background-position': ('0% 0%', False),
		'background-position-x': ('0%', False),
		'background-position-y': ('0%', False),
		'background-repeat': ('repeat', False),
		'background-size': ('auto', False),
		'block-size': ('auto', False),
		'border': ('', False),
		'border-block': ('', False),
		'border-block-color': ('currentcolor', False),
		'border-block-end': ('', False),
		'border-block-end-color': ('currentcolor', False),
		'border-block-end-style': ('none', False),
		'border-block-end-width': ('medium', False),
		'border-block-start': ('', False),
		'border-block-start-color': ('currentcolor', False),
		'border-block-start-style': ('none', False),
		'border-block-start-width': ('medium', False),
		'border-block-style': ('none', False),
		'border-block-width': ('medium', False),
		'border-bottom': ('', False),
		'border-bottom-color': ('currentColor', False),
		'border-bottom-left-radius': ('0', False),
		'border-bottom-right-radius': ('0', False),
		'border-bottom-style': ('none', False),
		'border-bottom-width': ('medium', False),
		'border-collapse': ('seperate', True),
		'border-color': ('', False),
		'border-end-end-radius': ('0', False),
		'border-end-start-radius': ('0', False),
		'border-image': ('', False),
		'border-image-outset': ('0', False),
		'border-image-repeat': ('stretch', False),
		'border-image-slice': ('100%', False),
		'border-image-source': ('none', False),
		'border-image-width': ('1', False),
		'border-inline': ('', False),
		'border-inline-color': ('currentcolor', False),
		'border-inline-end': ('', False),
		'border-inline-end-color': ('currentcolor', False),
		'border-inline-end-style': ('none', False),
		'border-inline-end-width': ('medium', False),
		'border-inline-start': ('', False),
		'border-inline-start-color': ('currentcolor', False),
		'border-inline-start-style': ('none', False),
		'border-inline-start-width': ('medium', False),
		'border-inline-style': ('none', False),
		'border-inline-width': ('medium', False),
		'border-left': ('', False),
		'border-left-color': ('currentColor', False),
		'border-left-style': ('none', False),
		'border-left-width': ('medium', False),
		'border-radius': ('', False),
		'border-right': ('', False),
		'border-right-color': ('currentColor', False),
		'border-right-style': ('none', False),
		'border-right-width': ('medium', False),
		'border-spacing': ('0', True),
		'border-start-end-radius': ('0', False),
		'border-start-start-radius': ('0', False),
		'border-style': ('', False),
		'border-top': ('', False),
		'border-top-color': ('currentColor', False),
		'border-top-left-radius': ('0', False),
		'border-top-right-radius': ('0', False),
		'border-top-style': ('none', False),
		'border-top-width': ('medium', False),
		'border-width': ('', False),
		'bottom': ('auto', False),
		'box-decoration-break': ('slice', False),
		'box-shadow': ('none', False),
		'box-sizing': ('content-box', False),
		'break-after': ('auto', False),
		'break-before': ('auto', False),
		'break-inside': ('auto', True),
		'caption-side': ('top', True),
		'caret-color': ('auto', True),
		'clear': ('auto', False),
		'clip-path': ('none', False),
		'color': ('black', True),
		'color-scheme': ('normal', False),
		'column-count': ('auto', False),
		'column-fill': ('balance', False),
		'column-gap': ('normal', False),
		'column-rule': ('', False),
		'column-rule-color': ('currentColor', False),
		'column-rule-style': ('none', False),
		'column-rule-width': ('medium', False),
		'column-span': ('none', False),
		'column-width': ('auto', False),
		'columns': ('', False),
		'contain': ('none', False),
		'contain-intrinsic-block-size': ('none', False),
		'contain-intrinsic-height': ('none', False),
		'contain-intrinsic-inline-size': ('none', False),
		'contain-intrinsic-size': ('', False),
		'contain-intrinsic-width': ('none', False),
		'container': ('', False),
		'container-name': ('none', False),
		'container-type': ('normal', False),
		'content': ('normal', False),
		'counter-increment': ('none', False),
		'counter-reset': ('none', False),
		'counter-set': ('none', False),
		'cursor': ('auto', True),
		'direction': ('ltr', True),
		'display': ('inline', False),
		'empty-cells': ('show', True),
		'filter': ('none', False),
		'flex': ('', False),
		'flex-basis': ('auto', False),
		'flex-direction': ('row', False),
		'flex-flow': ('', False),
		'flex-grow': ('0', False),
		'flex-shrink': ('1', False),
		'flex-wrap': ('nowrap', False),
		'float': ('none', False),
		'font': ('', True),
		'font-family': ('serif', True),
		'font-feature-settings': ('normal', True),
		'font-kerning': ('auto', True),
		'font-language-override': ('normal', True),
		'font-optical-sizing': ('auto', True),
		'font-palette': ('normal', True),
		'font-size': ('medium', True),
		'font-size-adjust': ('none', True),
		'font-stretch': ('normal', True),
		'font-style': ('normal', True),
		'font-synthesis': ('weight style', True),
		'font-synthesis-small-caps': ('auto', True),
		'font-synthesis-style': ('auto', True),
		'font-synthesis-weight': ('auto', True),
		'font-variant': ('normal', True),
		'font-variant-alternates': ('normal', True),
		'font-variant-caps': ('normal', True),
		'font-variant-east-asian': ('normal', True),
		'font-variant-emoji': ('normal', True),
		'font-variant-ligatures': ('normal', True),
		'font-variant-numeric': ('normal', True),
		'font-variant-position': ('normal', True),
		'font-variation-settings': ('normal', True),
		'font-weight': ('normal', True),
		'forced-color-adjust': ('auto', True),
		'gap': ('', False),
		'grid': ('', False),
		'grid-area': ('', False),
		'grid-auto-columns': ('auto', False),
		'grid-auto-flow': ('row', False),
		'grid-auto-rows': ('auto', False),
		'grid-column': ('', False),
		'grid-column-end': ('auto', False),
		'grid-column-start': ('auto', False),
		'grid-row': ('', False),
		'grid-row-end': ('auto', False),
		'grid-row-start': ('auto', False),
		'grid-template': ('', False),
		'grid-template-areas': ('none', False),
		'grid-template-columns': ('none', False),
		'grid-template-rows': ('none', False),
		'hanging-punctuation': ('none', False),
		'height': ('auto', False),
		'hyphenate-character': ('auto', True),
		'hyphenate-limit-chars': ('auto', True),
		'hyphens': ('manual', True),
		'image-orientation': ('from-image', True),
		'image-rendering': ('auto', True),
		'inline-size': ('auto', False),
		'inset': ('', False),
		'inset-block': ('', False),
		'inset-block-end': ('auto', False),
		'inset-block-start': ('auto', False),
		'inset-inline': ('', False),
		'inset-inline-end': ('auto', False),
		'inset-inline-start': ('auto', False),
		'isolation': ('auto', False),
		'justify-content': ('flex-start', False),
		'justify-items': ('legacy', False),
		'justify-self': ('auto', False),
		'left': ('auto', False),
		'letter-spacing': ('normal', True),
		'line-break': ('auto', True),
		'line-height': ('normal', True),
		'list-style': ('', True),
		'list-style-image': ('none', True),
		'list-style-position': ('outside', True),
		'list-style-type': ('disc', True),
		'margin': ('', False),
		'margin-block': ('', False),
		'margin-block-end': ('0', False),
		'margin-block-start': ('0', False),
		'margin-bottom': ('0', False),
		'margin-inline': ('', False),
		'margin-inline-end': ('0', False),
		'margin-inline-start': ('0', False),
		'margin-left': ('0', False),
		'margin-right': ('0', False),
		'margin-top': ('0', False),
		'math-depth': ('0', True),
		'math-style': ('normal', True),
		'max-block-size': ('none', False),
		'max-height': ('none', False),
		'max-inline-size': ('none', False),
		'max-width': ('none', False),
		'min-block-size': ('0', False),
		'min-height': ('0', False),
		'min-inline-size': ('0', False),
		'min-width': ('0', False),
		'mix-blend-mode': ('normal', False),
		'object-fit': ('fill', False),
		'object-position': ('50% 50%', False),
		'offset': ('', False),
		'offset-anchor': ('auto', False),
		'offset-distance': ('0', False),
		'offset-path': ('none', False),
		'offset-position': ('auto', False),
		'offset-rotate': ('auto', False),
		'opacity': ('1', False),
		'order': ('0', False),
		'orphans': ('2', True),
		'outline': ('', False),
		'outline-color': ('invert', False),
		'outline-offset': ('0', False),
		'outline-style': ('none', False),
		'outline-width': ('medium', True),
		'overflow': ('', False),
		'overflow-anchor': ('auto', False),
		'overflow-block': ('auto', False),
		'overflow-clip-margin': ('0px', False),
		'overflow-inline': ('auto', False),
		'overflow-wrap': ('normal', True),
		'overflow-x': ('visible', False),
		'overflow-y': ('visible', False),
		'overscroll-behavior': ('auto', False),
		'overscroll-behavior-block': ('auto', False),
		'overscroll-behavior-inline': ('auto', False),
		'overscroll-behavior-x': ('auto', False),
		'overscroll-behavior-y': ('auto', False),
		'padding': ('', False),
		'padding-block': ('', False),
		'padding-block-end': ('0', False),
		'padding-block-start': ('0', False),
		'padding-bottom': ('0', False),
		'padding-inline': ('', False),
		'padding-inline-end': ('0', False),
		'padding-inline-start': ('0', False),
		'padding-left': ('0', False),
		'padding-right': ('0', False),
		'padding-top': ('0', False),
		'page': ('auto', True),
		'paint-order': ('normal', True),
		'perspective': ('none', False),
		'perspective-origin': ('50% 50%', False),
		'place-content': ('normal', False),
		'place-items': ('', False),
		'place-self': ('', False),
		'pointer-events': ('auto', True),
		'position': ('static', False),
		'print-color-adjust': ('economy', True),
		'quotes': ('"\u201C" "\u201D" "\u2018" "\u2019"', True),
		'resize': ('none', False),
		'right': ('auto', False),
		'rotate': ('none', False),
		'row-gap': ('normal', False),
		'ruby-align': ('auto', True),
		'ruby-position': ('before', True),
		'scale': ('none', False),
		'scroll-behavior': ('auto', False),
		'scroll-margin': ('', False),
		'scroll-margin-block': ('', False),
		'scroll-margin-block-end': ('0', False),
		'scroll-margin-block-start': ('0', False),
		'scroll-margin-bottom': ('0', False),
		'scroll-margin-inline': ('', False),
		'scroll-margin-inline-end': ('0', False),
		'scroll-margin-inline-start': ('0', False),
		'scroll-margin-left': ('0', False),
		'scroll-margin-right': ('0', False),
		'scroll-margin-top': ('0', False),
		'scroll-padding': ('', False),
		'scroll-padding-block': ('', False),
		'scroll-padding-block-end': ('auto', False),
		'scroll-padding-block-start': ('auto', False),
		'scroll-padding-inline': ('', False),
		'scroll-padding-inline-end': ('auto', False),
		'scroll-padding-inline-start': ('auto', False),
		'scroll-snap-align': ('none', False),
		'scroll-snap-stop': ('normal', False),
		'scroll-snap-type': ('none', False),
		'scrollbar-color': ('auto', True),
		'scrollbar-gutter': ('auto', False),
		'scrollbar-width': ('auto', False),
		'shape-image-threshold': ('0', False),
		'shape-margin': ('0', False),
		'shape-outside': ('none', False),
		'tab-size': ('8', True),
		'table-layout': ('auto', False),
		'text-align': ('start', True),
		'text-align-last': ('auto', True),
		'text-combine-upright': ('none', True),
		'text-decoration': ('none', False),
		'text-decoration-color': ('currentColor', False),
		'text-decoration-line': ('none', False),
		'text-decoration-skip-ink': ('auto', True),
		'text-decoration-style': ('solid', False),
		'text-decoration-thickness': ('auto', False),
		'text-emphasis': ('', True),
		'text-emphasis-color': ('currentColor', True),
		'text-emphasis-position': ('over right', True),
		'text-emphasis-style': ('none', True),
		'text-indent': ('0', True),
		'text-justify': ('auto', True),
		'text-orientation': ('mixed', True),
		'text-overflow': ('clip', False),
		'text-rendering': ('auto', True),
		'text-shadow': ('none', True),
		'text-transform': ('none', True),
		'text-underline-offset': ('auto', True),
		'text-underline-position': ('auto', True),
		'top': ('auto', False),
		'touch-action': ('auto', False),
		'transform': ('none', False),
		'transform-box': ('view-box', False),
		'transform-origin': ('50% 50%', False),
		'transform-style': ('flat', False),
		'transition': ('', False),
		'transition-delay': ('0s', False),
		'transition-duration': ('0s', False),
		'transition-property': ('all', False),
		'transition-timing-function': ('ease', False),
		'translate': ('none', False),
		'unicode-bidi': ('normal', False),
		'user-select': ('auto', False),
		'vertical-align': ('baseline', False),
		'visibility': ('visible', False),
		'white-space': ('normal', True),
		'widows': ('2', True),
		'width': ('auto', False),
		'will-change': ('auto', False),
		'word-break': ('normal', True),
		'word-spacing': ('normal', True),
		'word-wrap': ('normal', True),
		'writing-mode': ('horizontal-tb', True),
		'z-index': ('auto', False)
	}
	
	"html_tag: { css_attribute:default_value, ... }"
	__default_attribute = {
		'a': {}, # 	Defines a hyperlink.
		'abbr': {}, #	Defines an abbreviated form of a longer word or phrase.
		'acronym': {}, # [OBSOLETE] Defines an acronym. Use <abbr/> instead.
		'address': {}, # 	Specifies the author's contact information.
		'applet': {}, # 	[OBSOLETE] Embeds a Java applet (mini Java applications) on the page. Use <object/> instead.
		'area': {}, # 	Defines a specific area within an image map.
		'article': {}, # 	Defines an article.
		'aside': {}, # 	Defines some content loosely related to the page content.
		'audio': {}, # 	Embeds a sound, or an audio stream in an HTML document.
		'b': {}, # 	Displays text in a bold style.
		'base': {}, # 	Defines the base URL for all relative URLs in a document.
		'basefont': {}, # 	[OBSOLETE] Specifies the base font for a page. Use CSS instead.
		'bdi': {}, # 	Represents text that is isolated from its surrounding for the purposes of bidirectional text formatting.
		'bdo': {}, # 	Overrides the current text direction.
		'big': {}, # 	[OBSOLETE] Displays text in a large size. Use CSS instead.
		'blockquote': {}, # 	Represents a section that is quoted from another source.
		'body': {}, # 	Defines the document's body.
		'br': {'content':"\n"}, # 	Produces a single line break.
		'button': {}, # 	Creates a clickable button.
		'canvas': {}, # 	Defines a region in the document, which can be used to draw graphics on the fly via scripting (usually JavaScript).
		'caption': {}, # 	Defines the caption or title of the table.
		'center': {'text-align':'center'}, # 	[OBSOLETE] Align contents in the center. Use CSS instead.
		'cite': {}, # 	Indicates a citation or reference to another source.
		'code': {}, # 	Specifies text as computer code.
		'col': {}, # 	Defines attribute values for one or more columns in a table.
		'colgroup': {}, # 	Specifies attributes for multiple columns in a table.
		'data': {}, # 	Links a piece of content with a machine-readable translation.
		'datalist': {}, # 	Represents a set of pre-defined options for an <input/> element.
		'dd': {}, # 	Specifies a description, or value for the term (<dt/>) in a description list (<dl/>).
		'del': {}, # 	Represents text that has been deleted from the document.
		'details': {}, # 	Represents a widget from which the user can obtain additional information or controls on-demand.
		'dfn': {}, # 	Specifies a definition.
		'dialog': {}, # 	Defines a dialog box or subwindow.
		'dir': {}, # 	[OBSOLETE] Defines a directory list. Use <ul/> instead.
		'div': {}, # 	Specifies a division or a section in a document.
		'dl': {}, # 	Defines a description list.
		'dt': {}, # 	Defines a term (an item) in a description list.
		'em': {}, # 	Defines emphasized text.
		'embed': {}, # 	Embeds external application, typically multimedia content like audio or video into an HTML document.
		'fieldset': {}, # 	Specifies a set of related form fields.
		'figcaption': {}, # 	Defines a caption or legend for a figure.
		'figure': {}, # 	Represents a figure illustrated as part of the document.
		'font': {}, # 	[OBSOLETE] Defines font, color, and size for text. Use CSS instead.
		'footer': {}, # 	Represents the footer of a document or a section.
		'form': {}, # 	Defines an HTML form for user input.
		'frame': {}, # 	[OBSOLETE] Defines a single frame within a frameset.
		'frameset': {}, # 	[OBSOLETE] Defines a collection of frames or other frameset.
		'head': {}, # 	Defines the head portion of the document that contains information about the document such as title.
		'header': {}, # 	Represents the header of a document or a section.
		'hgroup': {}, # 	Defines a group of headings.
		'h1': {'font-size':'xx-large'}, #	Defines HTML headings.
		'h2': {'font-size':'x-large'}, #	Defines HTML headings.
		'h3': {'font-size':'large'}, #	Defines HTML headings.
		'h4': {'font-size':'medium'}, #	Defines HTML headings.
		'h5': {'font-size':'small'}, #	Defines HTML headings.
		'h6': {'font-size':'xx-small'}, #	Defines HTML headings.
		'hr': {}, # 	Produce a horizontal line.
		'html': {}, # 	Defines the root of an HTML document.
		'i': {}, #		Displays text in an italic style.
		'iframe': {}, # 	Displays a URL in an inline frame.
		'img': {}, # 	Represents an image.
		'input': {}, #		Defines an input control.
		'ins': {}, # 	Defines a block of text that has been inserted into a document.
		'kbd': {}, # 	Specifies text as keyboard input.
		'keygen': {}, # 	Represents a control for generating a public-private key pair.
		'label': {}, #		Defines a label for an <input/> control.
		'legend': {}, # 	Defines a caption for a <fieldset/> element.
		'li': {}, # 	Defines a list item.
		'link': {}, # 	Defines the relationship between the current document and an external resource.
		'main': {}, # 	Represents the main or dominant content of the document.
		'map': {}, # 	Defines a client-side image-map.
		'mark': {}, # 	Represents text highlighted for reference purposes.
		'menu': {}, # 	Represents a list of commands.
		'menuitem': {}, # 	Defines a list (or menuitem) of commands that a user can perform.
		'meta': {}, # 	Provides structured metadata about the document content.
		'meter': {}, # 	Represents a scalar measurement within a known range.
		'nav': {}, # 	Defines a section of navigation links.
		'noframes': {}, # 	[OBSOLETE] Defines an alternate content that displays in browsers that do not support frames.
		'noscript': {}, # 	Defines alternative content to display when the browser doesn't support scripting.
		'object': {}, # 	Defines an embedded object.
		'ol': {}, # 	Defines an ordered list.
		'optgroup': {}, # 	Defines a group of related options in a selection list.
		'option': {}, # 	Defines an option in a selection list.
		'output': {}, # 	Represents the result of a calculation.
		'p': {}, # 	Defines a paragraph.
		'p::first-line': {'font-size':'20'},
		'param': {}, # 	Defines a parameter for an object or applet element.
		'picture': {}, # 	Defines a container for multiple image sources.
		'pre': {}, # 	Defines a block of preformatted text.
		'progress': {}, # 	Represents the completion progress of a task.
		'q': {}, # 	Defines a short inline quotation.
		'q::before': {'content':'open-quote'}, # 	Defines a short inline quotation.
		'q::after': {'content':'close-quote'}, # 	Defines a short inline quotation.
		'rp': {}, # 	Provides fall-back parenthesis for browsers that that don't support ruby annotations.
		'rt': {}, # 	Defines the pronunciation of character presented in a ruby annotations.
		'ruby': {}, # 	Represents a ruby annotation.
		's': {}, # 	Represents contents that are no longer accurate or no longer relevant.
		'samp': {}, # 	Specifies text as sample output from a computer program.
		'script': {}, # 	Places script in the document for client-side processing.
		'section': {}, # 	Defines a section of a document, such as header, footer etc.
		'select': {}, # 	Defines a selection list within a form.
		'small': {}, # 	Displays text in a smaller size.
		'source': {}, # 	Defines alternative media resources for the media elements like <audio/> or <video/>
		'span': {}, # 	Defines an inline styleless section in a document.
		'strike': {}, # 	[OBSOLETE] Displays text in strikethrough style.
		'strong': {}, # 	Indicate strongly emphasized text.
		'style': {}, # 	Inserts style information (commonly CSS) into the head of a document.
		'sub': {}, # 	Defines subscripted text.
		'summary': {}, # 	Defines a summary for the <details/> element.
		'sup': {}, # 	Defines superscripted text.
		#'svg': {}, # 	Embed SVG (Scalable Vector Graphics) content in an HTML document.
		'table': {}, # 	Defines a data table.
		'tbody': {}, # 	Groups a set of rows defining the main body of the table data.
		'td': {}, # 	Defines a cell in a table.
		'template': {}, # 	Defines the fragments of HTML that should be hidden when the page is loaded, but can be cloned and inserted in the document by JavaScript.
		'textarea': {}, # 	Defines a multi-line text input control (text area).
		'tfoot': {}, # 	Groups a set of rows summarizing the columns of the table.
		'th': {}, # 	Defines a header cell in a table.
		'thead': {}, # 	Groups a set of rows that describes the column labels of a table.
		'time': {}, # 	Represents a time and/or date.
		'title': {}, # 	Defines a title for the document.
		'tr': {}, # 	Defines a row of cells in a table.
		'track': {}, # 	Defines text tracks for the media elements like <audio/> or <video/>
		'tt': {}, # 	[OBSOLETE] Displays text in a teletype style.
		'u': {}, #		Displays text with an underline.
		'ul': {}, # 	Defines an unordered list.
		'var': {}, # 	Defines a variable.
		'video': {}, # 	Embeds video content in an HTML document.
		'wbr': {}, # 	Represents a line break opportunity.
		'blink': {},
		'marquee': {}
	}
	
	__block_level_elements = {
		'html', 'body', 'address', 'article', 'aside', 'blockquote', 'canvas', 'dd', 'div', 'dl', 'dt', 'fieldset', 
		'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hr', 'center',
		'li', 'main', 'nav', 'noscript', 'ol', 'p', 'pre', 'section', 'table', 'tfoot', 'ul', 'video', 'noframes'
	}
	
	for element in __block_level_elements:
		__default_attribute[element]['display'] = 'block'
	
	__invisible_elements = {
		'script', 'head', 'basefont', 'meta', 'frameset', 'frame', 'style'
	}
	
	for element in __invisible_elements:
		__default_attribute[element]['display'] = 'none'
	
	__inherited_attributes = frozenset(_attr for _attr, (_, _inherited) in __initial_attribute.items() if _inherited)
	
	@staticmethod
	def __traverse_text(element, descend):
		if not descend(element): return
		yield element, '::before', None
		yield element, None, element.text
		for child in element:
			yield from HTMLRender.__traverse_text(child, descend)
			yield element, None, child.tail
		yield element, '::after', None
	
	def __add_namespace(self, element, prefix, ns):
		nsmap = dict(element.nsmap)
		nsmap[prefix] = ns
		new_element = self.xml_parser.makeelement('{' + ns + '}' + element.tag, nsmap=nsmap)
		new_element.text = element.text
		new_element.tail = element.tail
		return new_element
	
	@staticmethod
	def __modify_tree(element, modify):
		children = [HTMLRender.__modify_tree(_child, modify) for _child in element]
		element = modify(element)
		element[:] = children
		return element
	
	def __xmlns(self, document):
		try:
			return document.getroot().tag.split('}')[0][1:]
		except AttributeError:
			return document.tag.split('}')[0][1:]
	
	def scan_document_links(self, document):
		"Yield all links referenced by the HTML document, including `data:` links."
		
		if self.is_html_document(document):
			def links():
				yield 'chrome:/html.css' # reset stylesheet
				#yield from document.scan_stylesheets()
				#yield from self.__xlink_hrefs(document)
				yield from self.__data_internal_links(self.__style_attrs(document))
				yield from self.__data_internal_links(self.__style_tags(document))
				yield from self.__style_links(document)
				yield from self.__script_tags(document)
			return links()
		else:
			return NotImplemented
	
	'''
	def __xlink_hrefs(self, document):
		xmlns_html = self.__xmlns(document)
		for linkedtag in chain(document.findall(f'.//*[@href]'), document.findall(f'.//*[@{{{self.xmlns_xlink}}}href]')):
			ns, tag = linkedtag.tag.split('}')
			ns = ns[1:]
			
			if ns not in [self.xmlns_html, self.xmlns_html2]:
				continue
			elif tag in ['a', 'link']:
				continue
			
			try:
				href = linkedtag.attrib[f'{{{self.xmlns_xlink}}}href']
			except KeyError:
				href = linkedtag.attrib['href']
			
			yield href
	'''
	
	def __data_internal_links(self, urls):
		"Recursively examine provided urls for internal urls they may reference."
		
		for url in urls:
			yield url
			if url.startswith('data:'):
				try:
					doc = self.get_document(url)
				except DocumentNotFound: # document may have been part-loaded
					pass # TODO: warning
				else:
					yield from self.__data_internal_links(self.scan_document_links(doc))
	
	def __style_attrs(self, document):
		"Yield all style='...' attributes as 'data:' urls."
		
		if 'style' in document.getroot().attrib:
			style = '* {' + document.getroot().attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
		
		for styledtag in document.findall('.//*[@style]'):
			#print(styledtag.tag, styledtag.attrib)
			style = '* {' + styledtag.attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
	
	def __style_links(self, document):
		"Yield all <link rel='stylesheet' href='...'> urls."
		
		xmlns_html = self.__xmlns(document)
		for linktag in document.findall(f'.//{{{xmlns_html}}}link[@rel="stylesheet"]'):
			yield linktag.attrib['href']
	
	def __style_tags(self, document):
		"Yield all <style/> tags as 'data:' urls."
		
		xmlns_html = self.__xmlns(document)
		for styletag in document.findall(f'.//{{{xmlns_html}}}style'):
			try:
				mime = styletag.attrib['type'].lower()
			except KeyError:
				mime = 'text/css'
			style = styletag.text
			yield f'data:{mime},' + url_quote(style)
	
	def __script_tags(self, document):
		xmlns_html = self.__xmlns(document)
		for scripttag in document.findall(f'.//{{{xmlns_html}}}script'):
			try:
				yield scripttag.attrib['src']
			except KeyError:
				pass
			
			try:
				mime = scripttag.attrib['type'].lower()
			except KeyError:
				mime = 'application/javascript'
			
			script = scripttag.text
			if script:
				yield f'data:{mime},' + url_quote(script)
	
	def image_dimensions(self, view, document):
		"Return the SVG dimensions, that might depend on the view state."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		return self.get_viewport_width(view), self.get_viewport_height(view)
	
	def image_width_for_height(self, view, document, height):
		if not self.is_html_document(document):
			return NotImplemented
		w, h = self.image_dimensions(view, document)
		return w # TODO
	
	def image_height_for_width(self, view, document, width):
		if not self.is_html_document(document):
			return NotImplemented
		w, h = self.image_dimensions(view, document)
		return h # TODO
	
	def __make_tree(self, document, node, view, ctx, width, height):
		def line_break():
			nonlocal line, offset, min_height, max_height, low_line_level_max, high_line_level_max
			assert line
			assert line[0].pseudoelement == 'left-terminator', type(line[0]).__name__ + ":" + str(line[0].pseudoelement)
			assert line[-1].pseudoelement == 'right-terminator', type(line[-1]).__name__ + ":" + str(line[-1].pseudoelement)
			min_height = max(line_height, max(_word.min_height for _word in line))
			max_height = max(min_height, min(_word.max_height for _word in line))
			lines.append(Row(line, font_size, element, pseudoelement, inline=True, gravity=Gravity.BOTTOM_LEFT, min_height=min_height, max_height=max_height, y_shift=-low_line_level_max))
			line = []
			offset = 0
			low_line_level_max = low_line_level
			high_line_level_max = high_line_level
		
		spans = []
		lines = []
		line = []
		low_line_level_max = 0
		high_line_level_max = 0
		offset = 0
		
		for element, pseudoelement, text in self.__traverse_text(node, (lambda _element: self.__get_attribute(view, document, _element, None, 'display', 'none') != 'none')):
			if not lines and pseudoelement is None:
				pseudoelement = '::first-line'
			
			if line and pseudoelement in {'::before', '::after'}:
				display = self.__get_attribute(view, document, element, None, 'display', 'inline')
				if display == 'block':
					assert line[-1].pseudoelement == 'right-terminator', str(line[-1].pseudoelement)
					line_break()
			
			content = self.__get_attribute(view, document, element, pseudoelement, 'content')
			if content == 'normal':
				pass
			elif content == 'open-quote':
				quotes = self.__get_attribute(view, document, element, pseudoelement, 'quotes', '"\"" "\""')
				quotes = quotes.split() # TODO: proper parsing
				text = quotes[0][1:-1]
			elif content == 'close-quote':
				quotes = self.__get_attribute(view, document, element, pseudoelement, 'quotes', '"\"" "\""')
				quotes = quotes.split() # TODO: proper parsing
				text = quotes[1][1:-1]
			else:
				raise NotImplementedError
			
			if not text:
				continue
			
			font_size_attr = self.__get_attribute(view, document, element, pseudoelement, 'font-size')
			print(font_size_attr, element.tag, pseudoelement)
			
			text_size = 16
			if font_size_attr == 'xx-small':
				font_size = 0.6 * text_size
			elif font_size_attr == 'x-small':
				font_size = 0.75 * text_size
			elif font_size_attr == 'small':
				font_size = 0.89 * text_size
			elif font_size_attr == 'medium':
				font_size = text_size
			elif font_size_attr == 'large':
				font_size = 1.2 * text_size
			elif font_size_attr == 'x-large':
				font_size = 1.5 * text_size
			elif font_size_attr == 'xx-large':
				font_size = 2 * text_size
			elif font_size_attr == 'xxx-large':
				font_size = 3 * text_size
			else:
				font_size = float(font_size_attr)
			
			line_height = font_size * 1.2
			high_line_level = font_size * 0.2
			low_line_level = font_size * 0.2
			space_width = font_size / 4
			
			low_line_level_max = max(low_line_level_max, low_line_level)
			high_line_level_max = max(high_line_level_max, high_line_level)
			
			text = text.translate(str.maketrans({_wh:" " for _wh in HTMLRender._HTMLRender__whitespace_chars}))
			
			if not text.strip(): # whitespace separating tags
				separator = Whitespace(None, 'separator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=space_width, height=line_height)
				if line and line[-2].pseudoelement != 'separator':
					line.insert(-1, separator)
				continue
			
			display = self.__get_attribute(view, document, element, pseudoelement, 'display', 'inline')
			
			if display == 'block':
				text_align = self.__get_attribute(view, document, element, pseudoelement, 'text-align', 'left')
				
				if text_align == 'justify':
					left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
					right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
				elif text_align in {'left', 'start'}:
					left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
					right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
				elif text_align in {'right', 'end'}:
					left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
					right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
				elif text_align == 'center':
					left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
					right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
				else:
					raise ValueError
				
				if text_align == 'justify':
					separator = Whitespace(None, 'separator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=space_width, max_width=inf, height=line_height)
				else:
					separator = Whitespace(None, 'separator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=space_width, height=line_height)
			
			ctx.set_font_size(font_size)
			
			if line:
				assert line[0].pseudoelement == 'left-terminator'
				assert line[-1].pseudoelement == 'right-terminator'
				line.pop()
				if line[-1].pseudoelement != 'separator' and text.startswith(" "):
					line.append(separator)
					offset += separator.min_width
			
			for word in text.strip().split(" "):
				word = word.strip()
				if not word: continue
				
				extents = ctx.text_extents(word)
				
				if offset + extents.width + (separator.min_width if line else 0) > width:
					line.append(right_terminator)							
					line_break()
				
				if not line:
					line.append(left_terminator)
				
				y_shift = extents.height + extents.y_bearing
				line.append(Word(word, -extents.x_bearing, -extents.y_bearing, None, 'word', inline=True, gravity=Gravity.BOTTOM_LEFT, width=extents.width, height=extents.height, y_shift=y_shift))
				offset += extents.width
				line.append(separator)
				offset += separator.min_width
			
			if not text.endswith(" "):
				if line[-1].pseudoelement == 'separator':
					sep = line.pop() # remove last separator
					offset -= sep.min_width
			
			if line:
				assert line[0].pseudoelement == 'left-terminator'
				del line[0]
				if line:
					min_height = max(line_height, max(_word.min_height for _word in line))
					max_height = max(min_height, min(_word.max_height for _word in line))
					#print(min_height, max_height, line)
					row = Row(line, font_size, element, pseudoelement, inline=True, gravity=Gravity.BOTTOM_LEFT, min_height=min_height, max_height=max_height)
					line = []
					line.append(left_terminator)
					line.append(row)
					line.append(right_terminator)
					offset = row.min_width
			
			if line:
				assert line[0].pseudoelement == 'left-terminator'
				assert line[-1].pseudoelement == 'right-terminator'
		
		spans.append(Column(lines, font_size, None, None, inline=False, gravity=Gravity.TOP_LEFT))
		
		tree = Column(spans, 1, None, None, inline=False, gravity=Gravity.TOP_LEFT)
		return tree
	
	def draw_image(self, view, document, ctx, box):
		"Perform HTML rendering."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.getroot()
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		width = box[2]
		height = box[3]
		
		self.__tree = self.__make_tree(document, node, view, ctx, width, height)
		
		ctx.save()
		ctx.rectangle(*box)
		ctx.clip()
		
		self.__tree.render(None, None, ctx, (0, 0, width, height))
		ctx.restore()
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.getroot()
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		self.__tree = self.__make_tree(document, node, view, ctx, width, height)
		
		ctx.save()
		ctx.rectangle(*box)
		ctx.clip()
		
		result = self.__tree.render(None, None, ctx, (0, 0, width, height), (px, py))
		ctx.restore()
		return result
		
	def __apply_color(self, view, document, element, pseudoelement, color_attr, opacity_attr, default_color):
		"Set painting source to the color identified by provided parameters."
		
		color = self.__get_attribute(view, document, element, pseudoelement, color_attr, default_color).strip()
		target = element.getparent()
		while color in ('currentColor', 'inherit') and (target is not None):
			if color == 'currentColor':
				color = self.__get_attribute(view, document, element, pseudoelement, 'color', default_color).strip()
			elif color == 'inherit':
				color = self.__get_attribute(view, document, element, pseudoelement, color_attr, default_color).strip()
			target = target.getparent()
		
		if color == 'currentColor' or color == 'inherit': # FIXME: workaround, delete it
			color = default_color
		
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
		
		if opacity_attr is not None:
			opacity = self.__get_attribute(view, document, element, pseudoelement, opacity_attr, None)
			if opacity == 'null':
				a = None # None means 1 (full opacity), not 0 (full transparency)
			else:
				a = parse_float(opacity)
			
			if a == 0:
				return None
		else:
			a = None
		
		#if color[:4] == 'url(' and color[-1] == ')':
		#	href = color.strip()[4:-1]
		#	if href[0] == '"' and href[-1] == '"': href = href[1:-1]
		#	return self.__apply_pattern(view, document, ctx, box, node, em_size, href)
		#	# TODO: transparency
		#else:
		#	cc = self.__parse_color(color, view, node)
		#	if cc == None:
		#		return False
		#	else:
		#		r, g, b = cc
		
		cc = self.__parse_color(color, view, element)
		if cc == None:
			return None
		else:
			r, g, b = cc
		
		try:
			if a == None:
				return (r, g, b)
			else:
				return (r, g, b, a)
		except UnboundLocalError:
			pass
	
	def __parse_color(self, color, view, node):
		if color[0] == '#' and len(color) == 4:
			r, g, b = [int(_c, 16) / 15 for _c in color[1:]]
		
		elif color[0] == '#' and len(color) == 7:
			r, g, b = [int(_c, 16) / 255 for _c in (color[1:3], color[3:5], color[5:7])]
							
		elif color[:4] == 'rgb(' and color[-1] == ')':
			r, g, b = [max(0, min(1, (parse_float(_c) / 255 if _c.strip()[-1] != '%' else parse_float(_c.strip()[:-1]) / 100))) for _c in color[4:-1].split(',')]
		
		elif color[:4] == 'hsl(' and color[-1] == ')':
			cc = color[4:-1].split(',')
			
			h = max(0, min(360, (parse_float(cc[0])))) / 360
			s = max(0, min(100, (parse_float(cc[1] if cc[1][-1] != '%' else cc[1][:-1])))) / 100
			l = max(0, min(100, (parse_float(cc[2] if cc[2][-1] != '%' else cc[2][:-1])))) / 100
			
			r, g, b = hls_to_rgb(h, l, s)
		
		else:
			self.emit_warning(view, f"Unsupported color specification: {color}.", node)
			return None
		
		return r, g, b
		
	def __get_attribute(self, view, document, node, pseudoelement, attr, default=None):
		value = self.__search_attribute(view, document, node, pseudoelement, attr)
		
		try:
			namespace, tag = node.tag.split('}')
		except ValueError:
			raise ValueError(f"Tag without namespace: <{node.tag}/>")
		namespace = namespace[1:]
		
		if namespace == self.__xmlns(document):
			if value is None:
				try:
					if pseudoelement:
						try:
							value = self.__default_attribute[tag + pseudoelement][attr]
						except KeyError:
							value = self.__default_attribute[tag][attr]
					else:
						value = self.__default_attribute[tag][attr]
				except KeyError:
					value = 'initial'
			
			if value == 'initial':
				value = self.__initial_attribute.get(attr, (None, None))[0]
		
		if value is None:
			value = default
		
		return value
	
	def __media_test(self, view, media):
		return False
	
	def __pseudoelement_test(self, view, pelem):
		return False
	
	def __get_pseudoclasses(self, view, node):
		#pseudoclasses = set()
		#if hasattr(self, 'get_pointed'):
		#	pointed = self.get_pointed(view)
		#	if pointed is not None and self.are_nodes_ordered(node, pointed):
		#		pseudoclasses.add('hover')
		#return pseudoclasses
		return []
	
	def __get_classes(self, node):
		if 'class' in node.attrib:
			return frozenset(node.attrib['class'].split(' '))
		else:
			return []
	
	def __get_id(self, node):
		if 'id' in node.attrib:
			return node.attrib['id']
		else:
			return None
	
	def __search_attribute(self, view, document, node, pseudoelement, attr):
		#if node.tag == '{http://www.w3.org/1999/xhtml}body':
		#	print("search_attribute", node.tag, pseudoelement, attr)
		
		xmlns_html = self.__xmlns(document)
		
		try:
			return view.__attr_cache[node, pseudoelement][attr]
		except KeyError:
			pass
		except AttributeError:
			view.__attr_cache = defaultdict(dict)
		
		if pseudoelement is None:
			"inline style='...' attribute"
			try:
				style = node.attrib['style']
			except (KeyError, AttributeError):
				pass
			else:
				css = self.get_document('data:text/css,' + url_quote('* {' + style + '}'))
				if self.is_css_document(css):
					if css not in self.__css_matcher:
						self.__css_matcher[css] = self.create_css_matcher(view, css, None, self.__get_id, None, None, None, node.tag.split('}')[1:] if node.tag[0] == '}' else '')
					css_attrs = self.__css_matcher[css](node)
					if attr in css_attrs:
						raw_value = css_attrs[attr][0]({})
						result = view.__attr_cache[node, pseudoelement][attr] = self.eval_css_value(raw_value) # TODO: css vars
						assert isinstance(result, str)
						return result
		
		"regular stylesheet (<style/> tag or external)"
		try:
			stylesheets = document.__stylesheets
		except AttributeError:
			stylesheets = list(self.__stylesheets(document))
			document.__stylesheets = stylesheets
		
		css_value = None
		css_priority = None
		
		for stylesheet in stylesheets:
			if stylesheet not in self.__css_matcher:
				self.__css_matcher[stylesheet] = self.create_css_matcher(view, stylesheet, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), None, self.__xmlns(document))
			
			css_attrs = self.__css_matcher[stylesheet](node)
			if attr in css_attrs:
				value, priority = css_attrs[attr]
				if css_priority == None or priority >= css_priority:
					raw_value = value({})
					css_value = self.eval_css_value(raw_value) # TODO: css vars
					assert isinstance(css_value, str)
					css_priority = priority
		
		if css_value is not None:
			view.__attr_cache[node, pseudoelement][attr] = css_value
			return css_value
		
		if attr in self.__inherited_attributes:
			if pseudoelement:
				result = self.__search_attribute(view, document, node, None, attr)
				view.__attr_cache[node, None][attr] = result
				return result
			else:
				parent = node.getparent()
				if parent is not None:
					result = self.__search_attribute(view, document, parent, None, attr)
					view.__attr_cache[node, pseudoelement][attr] = result
					return result
				else:
					return None
		else:
			return None
	
	def __stylesheets(self, document):
		myurl = self.get_document_url(document)
		
		doc = self.get_document('chrome:/html.css')
		if hasattr(self, 'is_css_document') and self.is_css_document(doc):
			yield doc
		
		for link in chain(self.__data_internal_links(self.__style_tags(document)), self.__style_links(document)): # document.scan_stylesheets()
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc


if __debug__ and __name__ == '__main__':
	import sys
	test_type = 0
	if len(sys.argv) != 2:
		print("Provide one of the arguments: --test-1, --test-2, --test-3, --test-4")
		sys.exit(1)
	elif sys.argv[1] == '--test-1':
		test_type = 1
	elif sys.argv[1] == '--test-2':
		test_type = 2
	elif sys.argv[1] == '--test-3':
		test_type = 3
	elif sys.argv[1] == '--test-4':
		test_type = 4
	else:
		print("Unknown argument combination.")
		sys.exit(1)


if __debug__ and __name__ == '__main__' and test_type == 1:
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	from pathlib import Path
	from urllib.parse import unquote as url_unquote
	
	from lxml.etree import fromstring as xml_frombytes
	
	from guixmpp.format.xml import XMLFormat, XMLDocument
	from guixmpp.format.css import CSSFormat, CSSDocument
	from guixmpp.format.null import NullFormat
	from guixmpp.download.data import DataDownload
	from guixmpp.download.chrome import ChromeDownload
	
	print("html render")
	
	class PseudoContext:
		def __init__(self, name):
			self.__name = name
			self.print_out = False
			self.balance = 0
			self.font_size = 16
		
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
			if self.print_out: print(f'{self.__name}.text_extents("{txt}")')
			return cairo.TextExtents(0, 0, len(txt) * self.font_size, self.font_size, len(txt) * self.font_size, 0)
		
		def font_extents(self):
			if self.print_out: print(f'{self.__name}.font_extents()')
			prop = 0.8
			return (self.font_size * prop, self.font_size * (1 - prop), self.font_size, 0, self.font_size * 2, 0) # cairo.FontExtents
		
		def set_dash(self, dashes, offset):
			if self.print_out: print(f'{self.__name}.set_dash({repr(dashes)}, {repr(offset)})')
			pass
		
		def device_to_user(self, x, y):
			if self.print_out: print(f'{self.__name}.device_to_user({x}, {y})')
			return x, y
		
		def set_font_size(self, size):
			self.font_size = size
		
		def __getattr__(self, attr):
			if self.print_out: return lambda *args: print(self.__name + '.' + attr + '(' + ', '.join(repr(_arg) for _arg in args) + ')')
			return lambda *args: None
	
	class HTMLRenderModel(HTMLRender, CSSFormat, XMLFormat, DataDownload, ChromeDownload, NullFormat):
		def __init__(self):
			HTMLRender.__init__(self)
			CSSFormat.__init__(self)
			XMLFormat.__init__(self)
			DataDownload.__init__(self)
			ChromeDownload.__init__(self)
			NullFormat.__init__(self)
		
		def scan_document_links(self, document):
			if HTMLRender.is_html_document(self, document):
				return HTMLRender.scan_document_links(self, document)
			elif CSSFormat.is_css_document(self, document):
				return CSSFormat.scan_document_links(self, document)
			elif XMLFormat.is_xml_document(self, document):
				return XMLFormat.scan_document_links(self, document)
			elif NullFormat.is_null_document(self, document):
				return NullFormat.scan_document_links(self, document)
			else:
				raise NotImplementedError(f"Could not scan links in unsupported document type: {type(document)}")
		
		def create_document(self, data, mime_type):
			if mime_type in {'application/xml', 'application/sgml', 'text/xml', 'text/sgml'}:
				return XMLFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/css':
				return CSSFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/html' or mime_type == 'application/xhtml+xml':
				return HTMLRender.create_document(self, data, mime_type)
			else:
				raise NotImplementedError(f"Could not create unsupported document type {mime_type}.")
		
		def resolve_url(self, rel_url, base_url):
			return rel_url
		
		def emit_warning(self, view, message, target):
			print(message)
		
		def is_html_document(self, document):
			return hasattr(document, 'getroot')
		
		def get_document_url(self, document):
			return ''
		
		def get_document(self, url):
			if url.startswith('#'):
				return XMLDocument(self.tree.findall(f".//*[@id='{url[1:]}']")[0])
			elif url.startswith('data:text/css'):
				return CSSDocument(url_unquote(url[14:]).encode('utf-8'))
			elif url == 'chrome:/html.css':
				print("global css")
				return CSSDocument(Path('chrome/html.css').read_bytes())
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
		
		def get_viewport_width(self, view):
			return 1000
		
		def get_viewport_height(self, view):
			return 500
	
	class PseudoView:
		def __init__(self):
			pass
	
	
	html_piece = xml_frombytes(b'''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>litehtml * Fast and lightweight HTML/CSS rendering engine</title>
  <!-- base xhtml4 -->
	<base href="http://www.litehtml.com/" />
	<meta name="robots" content="index, follow" />
	<link rel="canonical" href="http://www.litehtml.com/" />
	<meta http-equiv="content-language" content="en" />
	<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
	<meta http-equiv="pragma" content="cache" />
	<meta http-equiv="cache-control" content="cache" />
	<meta http-equiv="Content-Style-Type" content="text/css" />
	<meta http-equiv="Content-Script-Type" content="text/javascript" />
<!-- meta -->
	<meta name="keywords" content="launch bar,true launch bar,quick launch bar,windows,launcher,taskbar,toolbar, html,css,css3,render,engine,library,open source,free" />
	
	<meta name="abstract" content="fast and lightweight HTML/CSS open source rendering engine" />
	<meta http-equiv="last-modified" content="Sun, 16 Sep 2018 22:15:58 MSK" />
	<meta name="author" content="Yuri Kobets" />
	<meta name="copyright" content="Copyright (c) 2024 by litehtml" />
	<meta name="generator" content="MODX CMS" />
	<!--[if IE]><meta http-equiv="imagetoolbar" content="no" /><![endif]-->
<!-- Dublin Core -->
	<link rel="schema.DC" href="http://purl.org/dc/elements/1.1/" />
	<meta name="DC.contributor" content="litehtml" />
	<meta name="DC.creator" content="Yuri Kobets" />
	<meta name="DC.date" content="2018-09-16" />
	<meta name="DC.format" content="text/html" />
	<meta name="DC.identifier" content="Fast and lightweight HTML/CSS rendering engine - 1288" />
	<meta name="DC.language" content="en" />
	<meta name="DC.publisher" content="litehtml" />
	<meta name="DC.rights" content="Copyright (c) 2024 by litehtml" />
	<meta name="DC.rightsHolder" content="litehtml" />
	<meta name="DC.title" content="Fast and lightweight HTML/CSS rendering engine" />
<!-- icons/rss/css -->

<!-- end MetaX output -->
  <link rel="stylesheet" type="text/css" href="assets/templates/litehtml/style.css"/>
</head>
<body>
<div class="header">
	<div style="float:right;width:728px;height:90px">
	<script type="text/javascript"><!--
google_ad_client = "ca-pub-1229827911986752";
/* litehtml-benner */
google_ad_slot = "1947231680";
google_ad_width = 728;
google_ad_height = 90;
//-->
</script>
<script type="text/javascript"
src="http://pagead2.googlesyndication.com/pagead/show_ads.js">
</script>
	</div>
	<div class="logo">lite<strong>html</strong></div>
    <div class="slogan">fast and lightweight HTML/CSS rendering engine</div>
</div>
<div class="topmenu">
	<div class="nav">
		<ul>
		  <li class="first"><a href="http://www.litehtml.com/">Home</a></li>

<li><a href="download.html">Download</a></li>

<li><a href="wiki.html">Wiki</a></li>

<li><a href="get-the-code.html">Get the code</a></li>

<li><a href="donate.html">Donate</a></li>

		</ul>
	</div>
    <div class="search-outer">
        <div class="search">
            <div class="search-input">
                <input type="text" name="search" />
            </div>
        	<div class="go">
        		<input type="button" name="go" />
    		</div>
		</div>
	</div>
</div>
<div class="content">
<!-- BEGIN content -->
<h1>What is litehtml?</h1>
<p>litehtml is lightweight HTML/CSS rendering engine. The main goal of the litehtml library is to give the developers the easy way to show the HTML pages in theirs applications. The popular HTML engines like WebKit are too complicated for some tasks. For example, it may be too cumbersome to use WebKit to show some tooltips or pages in HTML format.</p>
<h1>What web standards are supported by litehtml?</h1>
<p>I tried to make the support of HTML5/CSS3 in the litehtml. It is far from perfect, but the most HTML/CSS features are supported. Actually the appearance of HTML elements are defined by master CSS. The source code contains the master.css file as example, but you are free to use your own css. The list of the main HTML/CSS features supported by litehtml: text formating, tables, floating elements, absolute positioning, anchors, embedded styles, CSS classes, most CSS selectors etc.</p>
<h1>What litehtml uses to draw text and images?</h1>
<p>Nothing! litehtml gives you a full freedom for using any of your favorite libraries to draw text, images and other elements. litehtml calculates the position of the HTML elements, then it calls some functions from the user implemented class to draw elements and request some imformation required for rendering. This class is very simple and the source code have some implementations of this class to show how this works.</p>
<h1>What platforms are supported by litehtml?</h1>
<p>Initially litehtml was developed for Windows and was tested hard on this platform. But litehtml does not depends of any library except STL. So it is possible to use litehtml on any platform. litehtml can be compiled on linux - you can find the example in the sources.</p>
<h1>What encodings are supported by litehtml?</h1>
<p>litehtml does not handle the encodings. litehtml works with wchar_t (Windows) or utf-8 strings. Your application have to convert the HTML page before passing it into litehtml.</p>
<h1>Where to download litehtml?</h1>
<p>Please visit <a href="https://github.com/litehtml">litehtml on GitHub</a> to download the litehtml source code.</p>
<p> </p>
<!-- END content -->
</div>
  <!-- Piwik -->
<script type="text/javascript"> 
  var _paq = _paq || [];
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function() {
    var u=(("https:" == document.location.protocol) ? "https" : "http") + "://piwik.tordex.com//";
    _paq.push(['setTrackerUrl', u+'piwik.php']);
    _paq.push(['setSiteId', 6]);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0]; g.type='text/javascript';
    g.defer=true; g.async=true; g.src=u+'piwik.js'; s.parentNode.insertBefore(g,s);
  })();

</script>
<noscript><p><img src="//piwik.tordex.com/piwik.php?idsite=1" style="border:0" alt="" /></p></noscript>
<!-- End Piwik Code -->

</body>
</html>
	''')
	
	
	
	#box = create_box(html_piece)
	#ctx = PseudoContext('ctx')
	#ctx.print_out = True
	#box.calculate_dimensions(ctx)
	#box.x = 0
	#box.y = 0
	#box.width = 1000
	#box.height = 2000
	#box.calculate_positions(ctx)
	
	#box.render(ctx)
	
	#quit()
	
	#nn = 0
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		
		for filepath in example.iterdir():
			if filepath.suffix not in ('.html', '.xhtml'): continue
			#if filepath.name != 'simple.html': continue
			print(filepath)
			#if filepath.name != 'animated-text-fine-cravings.svg': continue
			#nn += 1
			#if nn > 1: break
			
			#profiler = PyCallGraph(output=GraphvizOutput(output_file=f'profile/svg_{example.name}_{filepath.name}.png'))
			#profiler.start()
			
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			ctx.print_out = True
			rnd = HTMLRenderModel()
			view = PseudoView()
			
			if filepath.suffix == '.html':
				mime = 'text/html'
			else:
				mime = 'application/xhtml+xml'
			
			document = rnd.create_document(filepath.read_bytes(), mime)
			l = list(rnd.scan_document_links(document))
			#assert 'chrome:/html.css' in l
			
			if filepath.name == 'simple.html':
				h1 = document.find('.//html:h1', {'html':rnd.xmlns_html})
				assert rnd._HTMLRender__get_attribute(view, document, h1, None, 'display', None) == 'block'
			
			rnd.tree = document
			rnd.draw_image(view, document, ctx, (0, 0, 1000, 800))
				
			#profiler.done()


if __debug__ and __name__ == '__main__' and test_type == 2:
	from asyncio import run, get_running_loop
	
	import gi
	gi.require_version('Gtk', '4.0')
	from gi.repository import Gtk
	
	from guixmpp.mainloop import *
	from guixmpp.domevents import *
	DOMEvent = Event
	
	loop_init()
	
	window = Gtk.Window()
	window.set_title("HTML test widget")
	widget = Gtk.DrawingArea()
	window.set_child(widget)
	window.connect('close-request', lambda *_: loop_quit())
	
	#tree = ColorfulBox("root", [ColorfulBox("left", [], None, Gravity.LEFT, max_width=300, max_height=300), ColorfulBox("right", [], None, Gravity.RIGHT, max_width=300, max_height=300, x_shift=100, y_shift=-100)], None, Gravity.CENTER)
	#tree = Row([ColorfulBox("1", [], None, None, True, Gravity.BOTTOM_LEFT, min_width=10, max_width=250, grow_width=1, height=30), ColorfulBox("2", [], None, None, True, Gravity.BOTTOM_LEFT, min_width=20, max_width=200, grow_width=5, height=40), ColorfulBox("3", [], None, None, True, Gravity.BOTTOM_LEFT, min_width=30, max_width=150, grow_width=1, height=20), ColorfulBox("4", [], None, None, True, Gravity.BOTTOM_LEFT, min_width=40, max_width=100, grow_width=1, height=30)], None, None, False, Gravity.CENTER)
	
	text = """
		When the last days were upon me, and the ugly trifles of existence began to drive me to madness like the small drops of water that torturers let fall ceaselessly upon one spot of their victim’s body, I loved the irradiate refuge of sleep. In my dreams I found a little of the beauty I had vainly sought in life, and wandered through old gardens and enchanted woods.
		Once when the wind was soft and scented I heard the south calling, and sailed endlessly and languorously under strange stars.
		Once when the gentle rain fell I glided in a barge down a sunless stream under the earth till I reached another world of purple twilight, iridescent arbours, and undying roses.
		And once I walked through a golden valley that led to shadowy groves and ruins, and ended in a mighty wall green with antique vines, and pierced by a little gate of bronze.
		Many times I walked through that valley, and longer and longer would I pause in the spectral half-light where the giant trees squirmed and twisted grotesquely, and the grey ground stretched damply from trunk to trunk, sometimes disclosing the mould-stained stones of buried temples. And always the goal of my fancies was the mighty vine-grown wall with the little gate of bronze therein.
		After a while, as the days of waking became less and less bearable from their greyness and sameness, I would often drift in opiate peace through the valley and the shadowy groves, and wonder how I might seize them for my eternal dwelling-place, so that I need no more crawl back to a dull world stript of interest and new colours. And as I looked upon the little gate in the mighty wall, I felt that beyond it lay a dream-country from which, once it was entered, there would be no return.
		So each night in sleep I strove to find the hidden latch of the gate in the ivied antique wall, though it was exceedingly well hidden. And I would tell myself that the realm beyond the wall was not more lasting merely, but more lovely and radiant as well.
		Then one night in the dream-city of Zakarion I found a yellowed papyrus filled with the thoughts of dream-sages who dwelt of old in that city, and who were too wise ever to be born in the waking world. Therein were written many things concerning the world of dream, and among them was lore of a golden valley and a sacred grove with temples, and a high wall pierced by a little bronze gate. When I saw this lore, I knew that it touched on the scenes I had haunted, and I therefore read long in the yellowed papyrus.
		Some of the dream-sages wrote gorgeously of the wonders beyond the irrepassable gate, but others told of horror and disappointment. I knew not which to believe, yet longed more and more to cross forever into the unknown land; for doubt and secrecy are the lure of lures, and no new horror can be more terrible than the daily torture of the commonplace. So when I learned of the drug which would unlock the gate and drive me through, I resolved to take it when next I awaked.
		Last night I swallowed the drug and floated dreamily into the golden valley and the shadowy groves; and when I came this time to the antique wall, I saw that the small gate of bronze was ajar. From beyond came a glow that weirdly lit the giant twisted trees and the tops of the buried temples, and I drifted on songfully, expectant of the glories of the land from whence I should never return.
		But as the gate swung wider and the sorcery of drug and dream pushed me through, I knew that all sights and glories were at an end; for in that new realm was neither land nor sea, but only the white void of unpeopled and illimitable space. So, happier than I had ever dared hoped to be, I dissolved again into that native infinity of crystal oblivion from which the daemon Life had called me for one brief and desolate hour.		
	"""
	
	tree = None
	last_width = last_height = None
	
	@widget.set_draw_func
	def render(widget, ctx, width, height):
		global tree, last_width, last_height
		if tree is None or last_width != width or last_height != height:
			justify = 'left'
			font_size = 15
			
			ctx.set_font_size(font_size)
			lines = []
			line = []
			
			extents = ctx.text_extents("bp")
			line_height = extents.height
			line_level = -extents.y_bearing
			
			if justify == 'justify':
				left_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, width=0)
				right_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, width=0)
			elif justify == 'left':
				left_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, width=0)
				right_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf)
			elif justify == 'right':
				left_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf)
				right_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, width=0)
			elif justify == 'center':
				left_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf)
				right_terminator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf)
			else:
				raise ValueError
			
			if justify == 'justify':
				separator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=4, max_width=inf)
			else:
				separator = Box(None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, width=4)
			
			offset = 0
			for word in text.translate(str.maketrans({_wh:" " for _wh in HTMLRender._HTMLRender__whitespace_chars})).split(" "):
				word = word.strip()
				if not word: continue
				extents = ctx.text_extents(word)
				if offset + extents.width + (separator.min_width if line else 0) > width:
					line.append(right_terminator)
					row = Row(line, font_size, None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, height=line_height)
					lines.append(row)
					line = []
					offset = 0
				offset += extents.width
				if line:
					line.append(separator)
					offset += separator.min_width
				else:
					line.append(left_terminator)
				y_shift = extents.height + extents.y_bearing - line_height + line_level
				line.append(Word(word, -extents.x_bearing, -extents.y_bearing, None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, width=extents.width, height=extents.height, y_shift=y_shift))
			
			if line:
				line.append(right_terminator)
				row = Row(line, font_size, None, None, inline=True, gravity=Gravity.BOTTOM_LEFT, height=line_height)
				lines.append(row)
			
			tree = Column(lines, font_size, None, None, inline=False, gravity=Gravity.TOP_LEFT)
			
			last_width = width
			last_height = height
		
		tree.render(None, None, ctx, (0, 0, width, height))
	
	async def main():
		DOMEvent._time = get_running_loop().time
		window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
	
	run(main())


if __debug__ and __name__ == '__main__' and test_type == 3:
	from asyncio import run, get_running_loop
	from lxml.etree import fromstring as xml_frombytes, tostring as xml_tounicode
	from lxml.html import document_fromstring as html_frombytes, tostring as html_tobytes
	from guixmpp.format.xml import XMLDocument
	
	import gi
	gi.require_version('Gtk', '4.0')
	gi.require_version('PangoCairo', '1.0')
	from gi.repository import Gtk
	
	from guixmpp.mainloop import *
	from guixmpp.domevents import *
	DOMEvent = Event
	
	loop_init()
	
	window = Gtk.Window()
	window.set_title("HTML test widget")
	widget = Gtk.DrawingArea()
	window.set_child(widget)
	window.connect('close-request', lambda *_: loop_quit())
	
	class HTMLRenderTest(HTMLRender):
		def create_document(self, data, mime):
			if mime == 'text/xml' or mime == 'application/xml' or mime.endswith('+xml'):
				document = XMLDocument(xml_frombytes(data))
				return document
			elif mime == 'text/sgml' or mime == 'application/sgml':
				sgml_text = data
				sgml_doc = html_frombytes(sgml_text)
				xml_text = html_tobytes(sgml_doc, encoding='utf-8', method='xml')
				document = self.create_document(xml_text, 'application/xml')
				return document
			elif mime == 'application/xhtml' or mime == 'application/xhtml+xml' or mime == 'text/html':
				return super().create_document(data, mime)
			else:
				return NotImplemented
		
		def get_document_url(self, document):
			return '.'
		
		def get_document(self, url):
			return None
		
		def is_xml_document(self, document):
			return hasattr(document, 'getroot')
		
		def test_render(self, view, ctx, width, height):
			global tree, last_width, last_height
			if tree is None or last_width != width: #not (tree.min_width <= width <= tree.max_width):
				
				def line_break():
					nonlocal line, offset, min_height, max_height, low_line_level_max, high_line_level_max
					assert line
					assert line[0].pseudoelement == 'left-terminator', type(line[0]).__name__ + ":" + str(line[0].pseudoelement)
					assert line[-1].pseudoelement == 'right-terminator', type(line[-1]).__name__ + ":" + str(line[-1].pseudoelement)
					min_height = max(line_height, max(_word.min_height for _word in line))
					max_height = max(min_height, min(_word.max_height for _word in line))
					lines.append(Row(line, font_size, element, pseudoelement, inline=True, gravity=Gravity.BOTTOM_LEFT, min_height=min_height, max_height=max_height, y_shift=-low_line_level_max))
					line = []
					offset = 0
					low_line_level_max = low_line_level
					high_line_level_max = high_line_level
				
				spans = []
				lines = []
				line = []
				low_line_level_max = 0
				high_line_level_max = 0
				offset = 0
				
				for element, pseudoelement, text in self._HTMLRender__traverse_text(document.getroot(), (lambda _element: self._HTMLRender__get_attribute(view, document, _element, None, 'display', 'none') != 'none')):
					if line and pseudoelement in {'::before', '::after'}:
						display = self._HTMLRender__get_attribute(view, document, element, None, 'display', 'inline')
						if display == 'block':
							assert line[-1].pseudoelement == 'right-terminator', str(line[-1].pseudoelement)
							line_break()
					
					content = self._HTMLRender__get_attribute(view, document, element, pseudoelement, 'content')
					if content == 'normal':
						pass
					elif content == 'open-quote':
						text = '"'
					elif content == 'close-quote':
						text = '"'
					else:
						raise NotImplementedError
					
					if not text:
						continue
					
					font_size_attr = self._HTMLRender__get_attribute(view, document, element, pseudoelement, 'font-size')
					
					if font_size_attr == 'xx-small':
						font_size = 0.6 * 16
					elif font_size_attr == 'x-small':
						font_size = 0.75 * 16
					elif font_size_attr == 'small':
						font_size = 0.89 * 16
					elif font_size_attr == 'medium':
						font_size = 16
					elif font_size_attr == 'large':
						font_size = 1.2 * 16
					elif font_size_attr == 'x-large':
						font_size = 1.5 * 16
					elif font_size_attr == 'xx-large':
						font_size = 2 * 16
					elif font_size_attr == 'xxx-large':
						font_size = 3 * 16
					else:
						font_size = float(font_size_attr)

					line_height = font_size * 1.2
					high_line_level = font_size * 0.2
					low_line_level = font_size * 0.2
					space_width = font_size / 4
					
					low_line_level_max = max(low_line_level_max, low_line_level)
					high_line_level_max = max(high_line_level_max, high_line_level)
					
					text = text.translate(str.maketrans({_wh:" " for _wh in HTMLRender._HTMLRender__whitespace_chars}))
					
					if not text.strip(): # whitespace separating tags
						separator = Whitespace(None, 'separator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=space_width, height=line_height)
						if line and line[-2].pseudoelement != 'separator':
							line.insert(-1, separator)
						continue
					
					display = self._HTMLRender__get_attribute(view, document, element, pseudoelement, 'display', 'inline')
					
					if display == 'block':
						text_align = self._HTMLRender__get_attribute(view, document, element, pseudoelement, 'text-align', 'left')
						
						if text_align == 'justify':
							left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
							right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
						elif text_align in {'left', 'start'}:
							left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
							right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
						elif text_align in {'right', 'end'}:
							left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
							right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=0, height=line_height)
						elif text_align == 'center':
							left_terminator = Whitespace(None, 'left-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
							right_terminator = Whitespace(None, 'right-terminator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=0, max_width=inf, height=line_height)
						else:
							raise ValueError
						
						if text_align == 'justify':
							separator = Whitespace(None, 'separator', inline=True, gravity=Gravity.BOTTOM_LEFT, min_width=space_width, max_width=inf, height=line_height)
						else:
							separator = Whitespace(None, 'separator', inline=True, gravity=Gravity.BOTTOM_LEFT, width=space_width, height=line_height)
					
					ctx.set_font_size(font_size)
					
					if line:
						assert line[0].pseudoelement == 'left-terminator'
						assert line[-1].pseudoelement == 'right-terminator'
						line.pop()
						if line[-1].pseudoelement != 'separator' and text.startswith(" "):
							line.append(separator)
							offset += separator.min_width
					
					for word in text.strip().split(" "):
						word = word.strip()
						if not word: continue
						
						extents = ctx.text_extents(word)
						
						if offset + extents.width + (separator.min_width if line else 0) > width:
							line.append(right_terminator)							
							line_break()
						
						if not line:
							line.append(left_terminator)
						
						y_shift = extents.height + extents.y_bearing
						line.append(Word(word, -extents.x_bearing, -extents.y_bearing, None, 'word', inline=True, gravity=Gravity.BOTTOM_LEFT, width=extents.width, height=extents.height, y_shift=y_shift))
						offset += extents.width
						line.append(separator)
						offset += separator.min_width
					
					if not text.endswith(" "):
						if line[-1].pseudoelement == 'separator':
							sep = line.pop() # remove last separator
							offset -= sep.min_width
					
					if line:
						assert line[0].pseudoelement == 'left-terminator'
						del line[0]
						if line:
							min_height = max(line_height, max(_word.min_height for _word in line))
							max_height = max(min_height, min(_word.max_height for _word in line))
							#print(min_height, max_height, line)
							row = Row(line, font_size, element, pseudoelement, inline=True, gravity=Gravity.BOTTOM_LEFT, min_height=min_height, max_height=max_height)
							line = []
							line.append(left_terminator)
							line.append(row)
							line.append(right_terminator)
							offset = row.min_width
					
					if line:
						assert line[0].pseudoelement == 'left-terminator'
						assert line[-1].pseudoelement == 'right-terminator'
				
				spans.append(Column(lines, font_size, None, None, inline=False, gravity=Gravity.TOP_LEFT))
				
				tree = Column(spans, 1, None, None, inline=False, gravity=Gravity.TOP_LEFT)
				
				last_width = width
				last_height = height
			
			tree.render(None, None, ctx, (0, 0, width, height))
	
	model = HTMLRenderTest()
	
	document = model.create_document("""<?xml version="1.0"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
  <title>The Secret Cave</title>
 </head>

 <body>
  <h1>The Secret Cave</h1>
  <h2>or John Lees adventure</h2>
  <h3>By H. P. Lovecraft</h3>

  <p>
   <q>Now be good children</q> said Mrs. Lee <q>While I am away &amp; dont get into mischief</q>. Mr. &amp; Mrs. Lee were going off for the day &amp; to leave the two children: John 10 yrs old &amp; Alice 2 yrs old.
   <q>Yes</q> replied John.
   As soon as the elder Lees were away the younger Lees went down cellar &amp; began to rummage among the rubbish. Little Alice leaned against the wall watching John. As John was making a boat of barrel staves the
   little girl gave a piercing cry as the bricks behind her crumbled away. He rushed up to her &amp; lifted her out screaming loudly. As soon as her screams subsided she said: <q>The wall went away</q>. John went up &amp;
   saw that there was a passage. He said to the little girl <q>Let's come &amp; see what this is</q>. <q>Yes</q> she said. They entered the place. They could stand up it. The passage was farther than they could see. Then John
   went back upstairs &amp; went to the kitchen drawer &amp; got 2 candles &amp; some matches &amp; then they went back to the cellar passage. The two once more entered. There was plastering on the walls, ceiling &amp; floor.
   Nothing was visible but a box. This was for a seat. Nevertheless they examined it &amp; found it to contain nothing. They walked on farther &amp; pretty soon the plastering left off &amp; they were in a cave. Little Alice
   was frightened at first but at her brothers assurance that it was <q>all right</q> she allayed her fears. Soon they came to a small box which John took up &amp; carried within. Pretty soon they came on a boat. In it
   were two oars. He dragged it with difficulty along with him. Soon they found the passage came to an abrupt stop. He pulled the obstacle away &amp; to his dismay water rushed in in torrents. John was an expert
   swimmer &amp; long breathede. He had just taken a breath so he tried to rise but with the box &amp; his sister he found it quite impossible. Then he caught sight of the boat rising. He grasped it.&nbsp;.&nbsp;.&nbsp;.
  </p>

  <p>
   The next he knew he was on the surface clinging tightly to the body of his sister &amp; the mysterious box. He could not imagine how the water got in but a new peril menaced them: if the water continued rising it
   would rise to the top. Suddenly a thought presented itself. He could shut off the water. He speedily did this &amp; lifting the now lifeless body of his sister into the boat he himself climbed in &amp; sailed down the
   passage. It was gruesome &amp; uncanny. Absolutely dark. His candle being put out by the flood &amp; a dead body lying near. He did not gaze about him but rowed for his life. When he did look up he was floating in his
   own cellar. He quickly rushed up stairs with the body, to find his parents had come home. He told them the story.
  </p>

  <center>* * * * * *</center>

  <p>
   The funeral of Alice occupied so much time that John quite forgot about the box — but when they did open it they found it to be a solid gold chunk worth about $10,000. Enough to pay for any thing but the death
   of his sister.
  </p>

  <footer>End</footer>
 </body>
</html>
	""", 'text/html')
	
	#print(xml_tounicode(document))
	
	#text = p1.text
	tree = None
	last_width = last_height = None
	
	widget.set_draw_func(model.test_render)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
	
	run(main())


if __debug__ and __name__ == '__main__' and test_type == 4:
	from asyncio import run, get_running_loop
	from lxml.etree import fromstring as xml_frombytes, tostring as xml_tounicode, Element
	from lxml.html import document_fromstring as html_frombytes, tostring as html_tobytes
	from guixmpp.format.xml import XMLDocument
	
	import gi
	gi.require_version('Gtk', '4.0')
	gi.require_version('PangoCairo', '1.0')
	from gi.repository import Gtk
	
	from guixmpp.mainloop import *
	from guixmpp.domevents import *
	DOMEvent = Event
	
	loop_init()
	
	window = Gtk.Window()
	window.set_title("HTML test widget")
	widget = Gtk.DrawingArea()
	window.set_child(widget)
	window.connect('close-request', lambda *_: loop_quit())
	
	class HTMLRenderTest(HTMLRender):
		def create_document(self, data, mime):
			if mime == 'text/xml' or mime == 'application/xml' or mime.endswith('+xml'):
				document = XMLDocument(xml_frombytes(data))
				return document
			elif mime == 'text/sgml' or mime == 'application/sgml':
				sgml_text = data
				sgml_doc = html_frombytes(sgml_text)
				xml_text = html_tobytes(sgml_doc, encoding='utf-8', method='xml')
				document = self.create_document(xml_text, 'application/xml')
				return document
			elif mime == 'application/xhtml' or mime == 'application/xhtml+xml' or mime == 'text/html':
				return super().create_document(data, mime)
			else:
				return NotImplemented
		
		def get_document_url(self, document):
			return '.'
		
		def get_document(self, url):
			return None
		
		def is_xml_document(self, document):
			return hasattr(document, 'getroot')
		
		def _HTMLRender__add_namespace(self, element, prefix, ns):
			nsmap = dict(element.nsmap)
			nsmap[prefix] = ns
			new_element = Element('{' + ns + '}' + element.tag, nsmap=nsmap)
			new_element.text = element.text
			new_element.tail = element.tail
			return new_element
		
		def __produce_text(self, view, document, node):
			if self._HTMLRender__get_attribute(view, document, node, None, 'display') == 'none':
				return
			
			yield node, '::before', None
			
			yield node, None, node.text
			
			for child in node:
				yield from self.__produce_text(view, document, child)
				yield node, None, child.tail
			
			yield node, '::after', None
		
		__unicode_line_breaking_class = {
			'AI': [range(0x2780, 0x2794), {0x24ea}],
			'AK': [range(0x1b05, 0x1b34), range(0x1b45, 0x1b4d), range(0xa984, 0xa9b3), range(0x11005, 0x11038), range(0x11071, 0x11073), range(0x11305, 0x1130d), range(0x1130f, 0x11311), range(0x11313, 0x11329), range(0x1132a, 0x11331), range(0x11332, 0x11334), range(0x11335, 0x1133a), range(0x11360, 0x11362), range(0x11f04, 0x11f11), range(0x11f12, 0x11f34), {0x11075}],
			'AL': [range(0x600, 0x605), range(0x2061, 0x2065), {0x110bd, 0x6dd, 0x70f}],
			'AP': [range(0x11003, 0x11005), {0x11f02}],
			'AS': [range(0x1b50, 0x1b5a), range(0x1bc0, 0x1be6), range(0xa9d0, 0xa9da), range(0xaa00, 0xaa29), range(0xaa50, 0xaa5a), range(0x11066, 0x11070), range(0x1135e, 0x11360), range(0x11950, 0x1195a), range(0x11ee0, 0x11ef2), range(0x11f50, 0x11f5a), {0x11350}],
			'BA': [range(0x2e0e, 0x2e16), range(0x11ef7, 0x11ef9), range(0xaa40, 0xaa43), range(0xaa44, 0xaa4c), {0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x3000, 0x2008, 0x2009, 0x200a, 0x9, 0x1804, 0x1805, 0x10a57, 0xa60d, 0x2010, 0xa60f, 0x2012, 0x2013, 0x2e17, 0x2e19, 0x2027, 0x2e2a, 0x2e2b, 0x2e2c, 0x2e2d, 0x2e30, 0x1c3b, 0x1c3c, 0x1c3d, 0x1c3e, 0x1c3f, 0x104a, 0x104b, 0x10a50, 0x10a51, 0x10a52, 0x10a53, 0x10a54, 0x10a55, 0x2056, 0x10a56, 0x2058, 0x2059, 0x205a, 0x205b, 0xe5a, 0xaa5d, 0xaa5e, 0x205d, 0x205f, 0x205e, 0xe5b, 0xaa5f, 0x12470, 0x7c, 0x1c7e, 0x1c7f, 0x1680, 0xad, 0xa8ce, 0xa8cf, 0x16eb, 0x16ec, 0x16ed, 0x11ef2, 0x2cfa, 0x2cfb, 0x2cfc, 0x2cff, 0x10100, 0x10101, 0x10102, 0xf0b, 0x1091f, 0xa92e, 0xa92f, 0xf34, 0x1735, 0x1736, 0x1133d, 0x1b5a, 0x1b5b, 0x1b5d, 0x1b5e, 0x1b5f, 0x1b60, 0x1361, 0x1135d, 0x964, 0x965, 0xf7f, 0xf85, 0x58a, 0x1039f, 0x5be, 0xfbe, 0xfbf, 0xa9cf, 0x103d0, 0xfd2, 0x17d4, 0x17d5, 0x17d8, 0x17da}],
			'BB': [{0xf01, 0xf02, 0xf03, 0xf04, 0xf06, 0xf07, 0x1806, 0xf09, 0xf0a, 0xb4, 0x2c8, 0x2cc, 0xfd0, 0xfd1, 0xfd3, 0x2df, 0xa874, 0xa875, 0x1ffd}],
			'B2': [{0x2014}],
			'BK': [{0x2028, 0x2029, 0xb, 0xc}],
			'CB': [{0xfffc}],
			'CJ': [range(0xff67, 0xff71), {0x3041, 0x30a1, 0x3043, 0x30a3, 0x3045, 0x30a5, 0x30fc}],
			'CL': [range(0x3001, 0x3003), {0xff61, 0xff64, 0xff0c, 0xff0e, 0xfe10, 0xfe11, 0xfe12, 0xfe50, 0xfe52}],
			'CM': [],
			'CP': [{0x29, 0x2e56, 0x2e58, 0x2e5a, 0x2e5c, 0x5d}],
			'CR': [{0xd}],
			'EB': [{0x1f478, 0x1f6b4, 0x1f466}],
			'EM': [range(0x1f3fb, 0x1f400)],
			'EX': [{0x21, 0xff01, 0x5c6, 0x61f, 0xf0d, 0x6d4, 0xff1f, 0x7f9, 0x61b, 0x61e, 0x3f}],
			'GL': [range(0x13430, 0x13437), range(0x13439, 0x1343c), range(0x35c, 0x363), {0xa0, 0x16fe4, 0x2007, 0xf08, 0xf0c, 0x180e, 0x202f, 0x34f, 0x2011, 0xf12, 0x1107f}],
			'H2': [],
			'H3': [],
			'HY': [{0x2d}],
			'ID': [range(0x2e80, 0x3000), range(0x3040, 0x30a0), range(0x30a2, 0x30fb), range(0x3400, 0x4dc0), range(0x4e00, 0xa000), range(0xf900, 0xfb00), range(0x3130, 0x3190)],
			'HL': [],
			'IN': [{0xfe19, 0x2024, 0x2025, 0x2026}],
			'IS': [{0x2044, 0x589, 0x2c, 0x60c, 0x2e, 0x60d, 0x7f8, 0x3a, 0x3b, 0x37e}],
			'JL': [],
			'JT': [],
			'JV': [],
			'LF': [{0xa}],
			'NL': [{0x85}],
			'NS': [range(0x309b, 0x309f), range(0x30fd, 0x30ff), range(0xfe54, 0xfe56), range(0xff1a, 0xff1c), range(0xff9e, 0xffa0), {0x30a0, 0x3005, 0xff65, 0x2047, 0x2048, 0x2049, 0x301c, 0x303c, 0x30fb, 0xfe10, 0xfe13, 0x17d6, 0x303b, 0x203c, 0x203d}],
			'NU': [{0x66b, 0x66c}],
			'OP': [{0x2e18, 0xa1, 0xbf}],
			'PO': [range(0x2032, 0x2038), {0xffe0, 0xa2, 0x2103, 0x25, 0xff05, 0x20a7, 0x2109, 0x66a, 0x60b, 0xfe6a, 0xb0, 0x2030, 0x2031, 0xfdfc}],
			'PR': [{0x2b, 0xb1, 0x2212, 0x2213, 0x2116, 0x5c}],
			'QU': [range(0x2e00, 0x2e02), range(0x2e06, 0x2e09), {0x22, 0x27, 0x2e0b, 0x275b, 0x275c, 0x275d, 0x275e}],
			'RI': [range(0x1f1e6, 0x1f200)],
			'SA': [range(0xe00, 0xe80), range(0xe80, 0xf00), range(0x1000, 0x10a0), range(0x1780, 0x1800), range(0x1950, 0x1980), range(0x1980, 0x19e0), range(0x1a20, 0x1ab0), range(0xa9e0, 0xaa00), range(0xaa60, 0xaa80), range(0xaa80, 0xaae0), range(0x11700, 0x11740)],
			'SG': [],
			'SP': [{0x20}],
			'SY': [{0x2f}],
			'VF': [range(0x1bf2, 0x1bf4)],
			'VI': [{0xa9c0, 0x11f42, 0x1b44, 0x11046, 0x1134d}],
			'WJ': [{0x2060, 0xfeff}],
			'XX': [],
			'ZW': [{0x200b}],
			'ZWJ': [{0x200d}]
		}
		
		def unicode_line_break_class(self, character):
			"Return Unicode line break class as defined here: https://www.unicode.org/reports/tr14/"
			
			if len(character) != 1:
				raise ValueError("Character must be a 1-char string.")
			codepoint = ord(character)
			for category, ranges in self.__unicode_line_breaking_class.items():
				if any((codepoint in _range) for _range in ranges):
					return category
			
			if unicodedata.category(character) in {'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Sm', 'Sk', 'So', 'Nl', 'No', 'Pc', 'Pd', 'Po'}:
				return 'AL'
			
			# TODO: support other characters
			
			raise NotImplementedError("The character {repr(character)} does not belong to any line break class.")
		
		def __split_text(self, text):
			m = 0
			pbc = None
			for n, ch in enumerate(text):
				lbc = self.unicode_line_break_class(ch)
				if pbc is not None and lbc != pbc:
					if n > m:
						yield text[m:n]
					m = n + 1
				pbc = lbc
			if n > m:
				yield text[m:n]
		
		Marker = Enum('Marker', 'mandatory_break optional_break prohibited_break begin_box end_box begin_span end_span')
		
		#__whitespace_codepoints = set(range(0x20)) | {0x0020, 0x00A0, 0x1680, 0x180E, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200A, 0x200B, 0x202F, 0x205F, 0x3000, 0xFEFF}
		
		def __produce_words(self, view, document, node):
			for element, pseudoelement, text in self.__produce_text(view, document, node):
				display = self._HTMLRender__get_attribute(view, document, element, None, 'display')
				
				if pseudoelement == '::before':
					if display == 'block':
						yield element, pseudoelement, self.Marker.begin_box
					elif display == 'inline':
						yield element, pseudoelement, self.Marker.begin_span
					else:
						raise NotImplementedError(str(display))
				
				content = self._HTMLRender__get_attribute(view, document, element, None, 'content')
				if content == 'normal':
					pass
				elif (content.startswith("\"") and content.endswith("\"")) or (content.startswith("\'") and content.endswith("\'")):
					text = content[1:-1]
				
				if text:
					for word in self.__split_text(text):
						if len(word) == 1:
							yield element, pseudoelement, self.Marker.separator
						else:
							yield element, pseudoelement, word
				
				if pseudoelement == '::after':
					if display == 'block':
						yield element, pseudoelement, self.Marker.end_box
					elif display == 'inline':
						yield element, pseudoelement, self.Marker.end_span
					else:
						raise NotImplementedError(str(display))
		
		#def _HTMLRender__make_text(self, view, document, node, ctx, width, height):
		#	...
	
	model = HTMLRenderTest()
	
	document = model.create_document("""<!DOCTYPE html>
<html>
 <head>
  <title>text</title>
 </head>
 <body>
  <p>
	aaaa aaaa aaaa aaaa<br/>
	<span>no margin spaces</span><br/>
	<span> left margin space</span><br/>
	<span>right margin space </span><br/>
	<span> both margin spaces </span><br/>
	bbbb bbbb bbbb bbbb<br/>
	<span>no space</span><span>between spans</span><br/>
	cccc cccc cccc cccc<br/>
	<span>space present</span> <span>between spans</span><br/>
	dddd dddd dddd dddd<br/>
  </p>
  
  <p>
   aaaa aaaa aaaa aaaa<br/>
   bbbb bbbb bbbb bbbb<br/>
   cccc cccc cccc cccc<br/>
   dddd dddd dddd dddd<br/>
  </p>
  
 </body>
</html>
	""", 'text/html')
	
	node = document.getroot()
	
	for element, pseudoelement, word in model._HTMLRenderTest__produce_words(widget, document, node):
		print(element.tag.split('}')[1], pseudoelement, repr(word) if isinstance(word, str) else word.name)
	
	quit()
	
	def render(widget, ctx, width, height):
		#tree = model._HTMLRender__make_tree(document, node, widget, ctx, width, height)
		#tree.render(model, widget, ctx, (0, 0, width, height))
		...
	
	widget.set_draw_func(render)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
	
	run(main())

