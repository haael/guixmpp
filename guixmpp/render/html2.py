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
	from guixmpp.format.text import TextFormat
	from guixmpp.format.css import CSSFormat
	from guixmpp.escape import Escape
	from guixmpp.caching import cached
else:
	from ..format.xml import XMLFormat
	from ..format.text import TextFormat
	from ..format.css import CSSFormat
	from ..escape import Escape
	from ..caching import cached


def parse_float(f): # TODO: move to utils
	if f is None:
		return None
	elif f == 'null':
		return 0
	else:
		return float(f)


def clamp(minimum, x, maximum):
	return max(minimum, min(x, maximum))


class Block:
	def __init__(self, document, node, pseudoelement, children=None):
		self.document = document
		self.node = node
		self.pseudoelement = pseudoelement
		self.children = children
	
	def __bool__(self):
		if self.children is None:
			return True
		else:
			return any(self.children)
	
	def wrap(self, open_, close):
		if self.children is None:
			return
		for child in self.children:
			child.wrap(open_, close)
	
	def print_tree(self, level=0):
		#self.node.tag.split('}')[1] + (('#' + self.pseudoelement) if self.pseudoelement is not None else "")
		if self.children is None:
			yield '<' + self.node.tag.split('}')[1] + '/>', level
		else:
			yield '<' + self.node.tag.split('}')[1] + '>', level
			for child in self.children:
				yield from child.print_tree(level + 1)
			yield '</' + self.node.tag.split('}')[1] + '>', level
	
	def reformat(self, model, view):
		if self.children is None:
			return
		
		new_children = []
		text = Text()
		for child in self.children:
			if isinstance(child, Text):
				text += child
			else:
				if text:
					new_children.append(text)
					text = Text()
				new_children.append(child)
		if text:
			new_children.append(text)
		
		todel = []
		
		for n, child in enumerate(new_children):
			child.reformat(model, view)
			if not child:
				todel.append(n)
		for n in reversed(todel):
			del new_children[n]
		
		self.children = new_children
	
	def measure(self, model, view, ctx, width, height, callback):
		width_attr = model._HTMLRender__get_attribute(view, self.document, self.node, self.pseudoelement, 'width')
		height_attr = model._HTMLRender__get_attribute(view, self.document, self.node, self.pseudoelement, 'height')
		
		if width_attr == 'auto':
			self.width = width
		else:
			self.width = model.units(view, width_attr, percentage=width)
		
		if height_attr == 'auto':
			self.height = height
		else:
			self.height = model.units(view, height_attr, percentage=height)
		#print(self.node.tag, self.height, width, height, height_attr)
		
		margin_bottom = 0
		offset = 0
		if self.children is not None:
			for child in self.children:				
				if not isinstance(child, Text):
					margin_top = model.units(view, model._HTMLRender__get_attribute(view, child.document, child.node, child.pseudoelement, 'margin-top'), percentage=height)
					margin_left = model.units(view, model._HTMLRender__get_attribute(view, child.document, child.node, child.pseudoelement, 'margin-left'), percentage=width)
					margin_right = model.units(view, model._HTMLRender__get_attribute(view, child.document, child.node, child.pseudoelement, 'margin-right'), percentage=width)
				else:
					margin_top = 0
					margin_left = 0
					margin_right = 0
				
				child.left = margin_left
				
				offset += max(margin_top, margin_bottom)
				
				child.top = offset
				
				offset += child.measure(model, view, ctx, self.width - margin_left - margin_right, self.height, callback)
				
				if not isinstance(child, Text):
					margin_bottom = model.units(view, model._HTMLRender__get_attribute(view, child.document, child.node, child.pseudoelement, 'margin-bottom'), percentage=height)
				else:
					margin_bottom = 0
		
		offset += margin_bottom
		
		if height_attr == 'auto':
			self.height = offset
		
		return self.height
	
	def render(self, model, view, ctx, box, callback):
		model._HTMLRender__block_enter(view, self.document, self.node, self.pseudoelement, ctx, box)
		
		if self.children is not None:
			left, top, width, height = box		
			for child in self.children:
				child.render(model, view, ctx, (left + child.left, top + child.top, child.width, child.height), callback)
		
		model._HTMLRender__block_exit(view, self.document, self.node, self.pseudoelement, ctx, box)
	
	def poke(self, model, view, ctx, box, callback, px, py):
		model._HTMLRender__block_enter(view, self.document, self.node, self.pseudoelement, ctx, box)
		
		hover_nodes = []
		if self.children is not None:
			left, top, width, height = box
			for child in self.children:
				hn = child.poke(model, view, ctx, (left + child.left, top + child.top, child.width, child.height), callback, px, py)
				hover_nodes.extend(hn)
		
		model._HTMLRender__block_exit(view, self.document, self.node, self.pseudoelement, ctx, box)
		return hover_nodes


class Text:
	def __init__(self, text=""):
		self.text = text
	
	def __bool__(self):
		return bool(self.text)
	
	def __add__(self, other):
		return self.__class__(self.text + other.text)
	
	def wrap(self, open_, close):
		self.text = open_ + self.text + close
	
	def print_tree(self, level=0):
		yield repr(self.text), level
	
	def reformat(self, model, view):
		self.text = self.text.strip(" ")
	
	def measure(self, model, view, ctx, parent_width, parent_height, callback):
		height = model.image_height_for_width(view, self.text, parent_width, callback)
		self.width = parent_width
		self.height = height
		return height
	
	def render(self, model, view, ctx, box, callback):
		model.draw_image(view, self.text, ctx, box, callback)
	
	def poke(self, model, view, ctx, box, callback, px, py):
		return model.poke_image(view, self.text, ctx, box, px, py, callback)


class HTMLRender:
	xmlns_xml = XMLFormat.xmlns_xml
	xmlns_xlink = XMLFormat.xmlns_xlink
	
	xmlns_html = 'http://www.w3.org/1999/xhtml'
	xmlns_html2 = 'http://www.w3.org/2002/06/xhtml2'
	
	def __init__(self, *args, **kwargs):
		self.__css_matcher = {}
		self.__cache = {}
	
	def create_document(self, data, mime):
		if mime == 'application/xhtml' or mime == 'application/xhtml+xml':
			document = self.create_document(data, 'application/xml')
		elif mime == 'text/html':
			document = self.create_document(data, 'application/sgml')
		else:
			return NotImplemented
		
		if '}' not in document.getroot().tag:
			root = document.getroot()
			root = self.__modify_tree(root, lambda _element: self.__add_namespace(_element, None, self.xmlns_html))
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
	
	async def on_open_document(self, view, document):
		if not self.is_html_document(document):
			return NotImplemented
		
		pass
	
	async def on_close_document(self, view, document):
		if not self.is_html_document(document):
			return NotImplemented
		
		self.__cache.clear()
		self.__css_matcher.clear()
	
	"css_attribute: initial_value, is_inheritable, is_animatable, css_version"
	__initial_attribute = {
		'background': ('', False, True, 'CSS1 CSS3'),
		'background-attachment': ('scroll', False, False, 'CSS1'),
		'background-color': ('transparent', False, True, 'CSS1'),
		'background-image': ('none', False, False, 'CSS1 CSS3'),
		'background-position': ('0% 0%', False, True, 'CSS1'),
		'background-repeat': ('repeat', False, False, 'CSS1'),
		'border': ('medium none currentcolor', False, True, 'CSS1'),
		'border-bottom': ('medium none currentcolor', False, True, 'CSS1'),
		'border-bottom-color': ('currentcolor', False, True, 'CSS1'),
		'border-bottom-style': ('none', False, False, 'CSS1'),
		'border-bottom-width': ('medium', False, True, 'CSS1'),
		'border-color': ('currentcolor', False, True, 'CSS1'),
		'border-left': ('medium none currentcolor', False, True, 'CSS1'),
		'border-left-color': ('currentcolor', False, True, 'CSS1'),
		'border-left-style': ('none', False, False, 'CSS1'),
		'border-left-width': ('medium', False, True, 'CSS1'),
		'border-right': ('medium none currentcolor', False, True, 'CSS1'),
		'border-right-color': ('black', False, True, 'CSS1'),
		'border-right-style': ('none', False, False, 'CSS1'),
		'border-right-width': ('medium', False, True, 'CSS1'),
		'border-style': ('none', False, False, 'CSS1'),
		'border-top': ('medium none currentcolor', False, True, 'CSS1'),
		'border-top-color': ('currentcolor', False, True, 'CSS1'),
		'border-top-style': ('none', False, False, 'CSS1'),
		'border-top-width': ('medium', False, True, 'CSS1'),
		'border-width': ('medium', False, True, 'CSS1'),
		'clear': ('none', False, False, 'CSS1'),
		'color': ('black', True, True, 'CSS1'),
		'display': ('inline', False, False, 'CSS1'),
		'float': ('none', False, False, 'CSS1'),
		'font': ('', True, True, 'CSS1'),
		'font-family': ('sans-serif', True, False, 'CSS1'),
		'font-size': ('medium', True, True, 'CSS1'),
		'font-style': ('normal', True, False, 'CSS1'),
		'font-variant': ('normal', True, False, 'CSS1'),
		'font-weight': ('normal', True, True, 'CSS1'),
		'height': ('auto', False, True, 'CSS1'),
		'letter-spacing': ('normal', True, True, 'CSS1'),
		'line-height': ('normal', True, True, 'CSS1'),
		'list-style': ('disc outside none', True, False, 'CSS1'),
		'list-style-image': ('none', True, False, 'CSS1'),
		'list-style-position': ('outside', True, False, 'CSS1'),
		'list-style-type': ('disc', True, False, 'CSS1'),
		'margin': ('0', False, True, 'CSS1'),
		'margin-bottom': ('0', False, True, 'CSS1'),
		'margin-left': ('0', False, True, 'CSS1'),
		'margin-right': ('0', False, True, 'CSS1'),
		'margin-top': ('0', False, True, 'CSS1'),
		'padding': ('0', False, True, 'CSS1'),
		'padding-bottom': ('0', False, True, 'CSS1'),
		'padding-left': ('0', False, True, 'CSS1'),
		'padding-right': ('0', False, True, 'CSS1'),
		'padding-top': ('0', False, True, 'CSS1'),
		'text-align': (None, True, False, 'CSS1'), # left if direction is ltr, and right if direction is rtl
		'text-decoration': ('none currentcolor solid auto', False, False, 'CSS1 CSS3'),
		'text-indent': ('0', True, True, 'CSS1'),
		'text-transform': ('none', True, None, 'CSS1'),
		'vertical-align': ('baseline', False, True, 'CSS1'),
		'white-space': ('normal', True, False, 'CSS1'),
		'width': ('auto', False, True, 'CSS1'),
		'word-spacing': ('normal', True, True, 'CSS1'),
		
		'border-collapse': ('separate', True, False, 'CSS2'),
		'border-spacing': ('2px', True, True, 'CSS2'),
		'bottom': ('auto', False, True, 'CSS2'),
		'caption-side': ('top', True, False, 'CSS2'),
		'clip': ('auto', False, True, 'CSS2'),
		'content': ('normal', False, False, 'CSS2'),
		'counter-increment': ('none', False, False, 'CSS2'),
		'counter-reset': ('none', False, False, 'CSS2'),
		'counter-set': ('none', False, False, 'CSS2'),
		'cursor': ('auto', True, False, 'CSS2'),
		'direction': ('ltr', True, False, 'CSS2'),
		'empty-cells': ('show', True, False, 'CSS2'),
		'left': ('auto', False, True, 'CSS2'),
		'max-height': ('none', False, True, 'CSS2'),
		'max-width': ('none', False, True, 'CSS2'),
		'min-height': ('0', False, True, 'CSS2'),
		'min-width': ('0', False, True, 'CSS2'),
		'outline': ('medium invertcolor', False, True, 'CSS2'),
		'outline-color': ('currentcolor', False, True, 'CSS2'),
		'outline-style': ('none', False, False, 'CSS2'),
		'outline-width': ('medium', False, True, 'CSS2'),
		'overflow': ('visible', False, False, 'CSS2'),
		'page-break-after': ('auto', False, False, 'CSS2'),
		'page-break-before': ('auto', False, False, 'CSS2'),
		'page-break-inside': ('auto', False, False, 'CSS2'),
		'position': ('static', False, False, 'CSS2'),
		'quotes': ('not specified', True, False, 'CSS2'),
		'right': ('auto', False, True, 'CSS2'),
		'table-layout': ('auto', False, False, 'CSS2'),
		'top': ('auto', False, True, 'CSS2'),
		'unicode-bidi': ('normal', True, False, 'CSS2'),
		'visibility': ('visible', True, True, 'CSS2'),
		'z-index': ('auto', False, True, 'CSS2'),
		
		'align-content': ('stretch', False, False, 'CSS3'),
		'align-items': ('normal', False, False, 'CSS3'),
		'align-self': ('auto', False, False, 'CSS3'),
		'all': ('none', False, False, 'CSS3'),
		'animation': ('none 0 ease 0 1 normal none running', False, False, 'CSS3'),
		'animation-delay': ('0s', False, False, 'CSS3'),
		'animation-direction': ('normal', False, False, 'CSS3'),
		'animation-duration': ('0', False, False, 'CSS3'),
		'animation-fill-mode': ('none', False, False, 'CSS3'),
		'animation-iteration-count': ('1', False, False, 'CSS3'),
		'animation-name': ('none', False, False, 'CSS3'),
		'animation-play-state': ('running', False, False, 'CSS3'),
		'animation-timing-function': ('ease', False, False, 'CSS3'),
		'aspect-ratio': ('auto', False, True, 'CSS3'),
		'backdrop-filter': ('none', False, False, 'CSS3'),
		'backface-visibility': ('visible', False, False, 'CSS3'),
		'background-blend-mode': ('normal', False, False, 'CSS3'),
		'background-clip': ('border-box', False, False, 'CSS3'),
		'background-origin': ('padding-box', False, False, 'CSS3'),
		'background-position-x': ('0%', False, True, 'CSS3'),
		'background-position-y': ('0%', False, True, 'CSS3'),
		'background-size': ('auto', False, True, 'CSS3'),
		'block-size': ('auto', False, True, 'CSS3'),
		'border-block': ('medium none currentcolor', False, True, 'CSS3'),
		'border-block-color': ('currentcolor', False, True, 'CSS3'),
		'border-block-end': ('medium none currentcolor', False, True, 'CSS3'),
		'border-block-end-color': ('currentcolor', False, True, 'CSS3'),
		'border-block-end-style': ('none', False, False, 'CSS3'),
		'border-block-end-width': ('medium', False, True, 'CSS3'),
		'border-block-start': ('medium none currentcolor', False, True, 'CSS3'),
		'border-block-start-color': ('currentcolor', False, True, 'CSS3'),
		'border-block-start-style': ('none', False, False, 'CSS3'),
		'border-block-start-width': ('medium', False, True, 'CSS3'),
		'border-block-style': ('none', False, False, 'CSS3'),
		'border-block-width': ('medium', False, True, 'CSS3'),
		'border-bottom-left-radius': ('0', False, True, 'CSS3'),
		'border-bottom-right-radius': ('0', False, True, 'CSS3'),
		'border-end-end-radius': ('0', False, True, 'CSS3'),
		'border-end-start-radius': ('0', False, True, 'CSS3'),
		'border-image': ('none 100% 1 0 stretch', False, False, 'CSS3'),
		'border-image-outset': ('0', False, False, 'CSS3'),
		'border-image-repeat': ('stretch', False, False, 'CSS3'),
		'border-image-slice': ('100%', False, False, 'CSS3'),
		'border-image-source': ('none', False, False, 'CSS3'),
		'border-image-width': ('1', False, False, 'CSS3'),
		'border-inline': ('medium none currentcolor', False, True, 'CSS3'),
		'border-inline-color': ('currentcolor', False, True, 'CSS3'),
		'border-inline-end': ('medium none currentcolor', False, True, 'CSS3'),
		'border-inline-end-color': ('currentcolor', False, True, 'CSS3'),
		'border-inline-end-style': ('none', False, False, 'CSS3'),
		'border-inline-end-width': ('medium', False, True, 'CSS3'),
		'border-inline-start': ('medium none currentcolor', False, True, 'CSS3'),
		'border-inline-start-color': ('currentcolor', False, True, 'CSS3'),
		'border-inline-start-style': ('none', False, False, 'CSS3'),
		'border-inline-start-width': ('medium', False, True, 'CSS3'),
		'border-inline-style': ('none', False, False, 'CSS3'),
		'border-inline-width': ('medium', False, True, 'CSS3'),
		'border-radius': ('0', False, True, 'CSS3'),
		'border-start-end-radius': ('0', False, True, 'CSS3'),
		'border-start-start-radius': ('0', False, True, 'CSS3'),
		'border-top-left-radius': ('0', False, True, 'CSS3'),
		'border-top-right-radius': ('0', False, True, 'CSS3'),
		'box-decoration-break': ('slice', False, False, 'CSS3'),
		'box-reflect': ('none', False, False, 'CSS3'),
		'box-shadow': ('none', False, True, 'CSS3'),
		'box-sizing': ('content-box', False, False, 'CSS3'),
		'break-after': ('auto', False, False, 'CSS3'),
		'break-before': ('auto', False, False, 'CSS3'),
		'break-inside': ('auto', False, False, 'CSS3'),
		'caret-color': ('auto', True, False, 'CSS3'),
		'column-count': ('auto', False, True, 'CSS3'),
		'column-fill': ('balance', False, False, 'CSS3'),
		'column-rule': ('medium none currentcolor', False, True, 'CSS3'),
		'column-rule-color': ('currentcolor', False, True, 'CSS3'),
		'column-rule-style': ('none', False, False, 'CSS3'),
		'column-rule-width': ('medium', False, True, 'CSS3'),
		'column-span': ('none', False, False, 'CSS3'),
		'column-width': ('auto', False, True, 'CSS3'),
		'columns': ('auto auto', False, True, 'CSS3'),
		'filter': ('none', False, True, 'CSS3'),
		'flex': ('0 1 auto', False, True, 'CSS3'),
		'flex-basis': ('auto', False, True, 'CSS3'),
		'flex-direction': ('row', False, False, 'CSS3'),
		'flex-flow': ('row nowrap', False, False, 'CSS3'),
		'flex-grow': ('0', False, True, 'CSS3'),
		'flex-shrink': ('1', False, True, 'CSS3'),
		'flex-wrap': ('nowrap', False, False, 'CSS3'),
		'font-feature-settings': ('normal', True, False, 'CSS3'),
		'font-kerning': ('auto', True, False, 'CSS3'),
		'font-size-adjust': ('none', True, True, 'CSS3'),
		'font-stretch': ('normal', True, True, 'CSS3'),
		'font-variant-caps': ('normal', True, False, 'CSS3'),
		'hanging-punctuation': ('none', True, False, 'CSS3'),
		'hyphens': ('manual', True, False, 'CSS3'),
		'image-rendering': ('auto', True, False, 'CSS3'),
		'initial-letter': ('normal', False, False, 'CSS3'),
		'inline-size': ('auto', False, True, 'CSS3'),
		'inset': ('auto', False, True, 'CSS3'),
		'inset-block': ('auto', False, True, 'CSS3'),
		'inset-block-end': ('auto', False, True, 'CSS3'),
		'inset-block-start': ('auto', False, True, 'CSS3'),
		'inset-inline': ('auto', False, True, 'CSS3'),
		'inset-inline-end': ('auto', False, True, 'CSS3'),
		'inset-inline-start': ('auto', False, True, 'CSS3'),
		'isolation': ('auto', False, False, 'CSS3'),
		'justify-content': ('flex-start', False, False, 'CSS3'),
		'justify-items': ('legacy', False, False, 'CSS3'),
		'justify-self': ('auto', False, False, 'CSS3'),
		'margin-block': ('auto', False, True, 'CSS3'),
		'margin-block-end': ('auto', False, True, 'CSS3'),
		'margin-block-start': ('auto', False, True, 'CSS3'),
		'margin-inline': ('auto', False, True, 'CSS3'),
		'margin-inline-end': ('auto', False, True, 'CSS3'),
		'margin-inline-start': ('auto', False, True, 'CSS3'),
		'marker': (None, None, None, None),
		'marker-end': (None, None, None, None),
		'marker-mid': (None, None, None, None),
		'marker-start': (None, None, None, None),
		'max-block-size': ('auto', False, True, 'CSS3'),
		'max-inline-size': ('auto', False, True, 'CSS3'),
		'min-block-size': ('auto', False, True, 'CSS3'),
		'min-inline-size': ('auto', False, True, 'CSS3'),
		'mix-blend-mode': ('normal', False, False, None),
		'object-fit': ('', False, False, 'CSS3'),
		'object-position': ('50% 50%', True, True, 'CSS3'),
		'offset': ('', False, True, 'CSS3'),
		'offset-anchor': ('auto', False, True, 'CSS3'),
		'offset-distance': ('0', False, True, 'CSS3'),
		'offset-path': ('none', False, True, 'CSS3'),
		'offset-position': ('normal', False, True, 'CSS3'),
		'offset-rotate': ('auto', False, True, 'CSS3'),
		'opacity': ('1', False, True, 'CSS3'),
		'order': ('0', False, True, 'CSS3'),
		'orphans': ('2', True, False, 'CSS3'),
		'outline-offset': ('0', False, True, 'CSS3'),
		'overflow-anchor': ('auto', False, False, 'CSS3'),
		'overflow-wrap': ('normal', True, False, 'CSS3'),
		'overflow-x': ('visible', False, False, 'CSS3'),
		'overflow-y': ('visible', False, False, 'CSS3'),
		'overscroll-behavior': ('auto', False, False, 'CSS3'),
		'overscroll-behavior-block': ('auto', False, False, 'CSS3'),
		'overscroll-behavior-inline': ('auto', False, False, 'CSS3'),
		'overscroll-behavior-x': ('auto', False, False, 'CSS3'),
		'overscroll-behavior-y': ('auto', False, False, 'CSS3'),
		'padding-block': ('auto', False, True, 'CSS3'),
		'padding-block-end': ('auto', False, True, 'CSS3'),
		'padding-block-start': ('auto', False, True, 'CSS3'),
		'padding-inline': ('auto', False, True, 'CSS3'),
		'padding-inline-end': ('auto', False, True, 'CSS3'),
		'padding-inline-start': ('auto', False, True, 'CSS3'),
		'paint-order': ('normal', True, False, 'CSS3'),
		'perspective': ('none', False, True, 'CSS3'),
		'perspective-origin': ('50% 50%', False, True, 'CSS3'),
		'place-content': ('normal', False, False, 'CSS3'),
		'place-items': ('normal legacy', False, False, 'CSS3'),
		'place-self': ('auto', False, False, 'CSS3'),
		'pointer-events': ('auto', True, False, 'CSS3'),
		'resize': ('none', False, False, 'CSS3'),
		'rotate': ('none', False, True, 'CSS3'),
		'scale': ('none', False, True, 'CSS3'),
		'scroll-margin': ('0', False, False, 'CSS3'),
		'scroll-margin-block': ('0', False, False, 'CSS3'),
		'scroll-margin-block-end': ('0', False, False, 'CSS3'),
		'scroll-margin-block-start': ('0', False, False, 'CSS3'),
		'scroll-margin-bottom': ('none', False, False, 'CSS3'),
		'scroll-margin-inline': ('0', False, False, 'CSS3'),
		'scroll-margin-inline-end': ('0', False, False, 'CSS3'),
		'scroll-margin-inline-start': ('0', False, False, 'CSS3'),
		'scroll-margin-left': ('0', False, False, 'CSS3'),
		'scroll-margin-right': ('0', False, False, 'CSS3'),
		'scroll-margin-top': ('0', False, False, 'CSS3'),
		'scroll-padding': ('auto', False, False, 'CSS3'),
		'scroll-padding-block': ('auto', False, False, 'CSS3'),
		'scroll-padding-block-end': ('auto', False, False, 'CSS3'),
		'scroll-padding-block-start': ('auto', False, False, 'CSS3'),
		'scroll-padding-bottom': ('auto', False, False, 'CSS3'),
		'scroll-padding-inline': ('auto', False, False, 'CSS3'),
		'scroll-padding-inline-end': ('auto', False, False, 'CSS3'),
		'scroll-padding-inline-start': ('auto', False, False, 'CSS3'),
		'scroll-padding-left': ('auto', False, False, 'CSS3'),
		'scroll-padding-right': ('auto', False, False, 'CSS3'),
		'scroll-padding-top': ('auto', False, False, 'CSS3'),
		'scroll-snap-align': ('none', False, False, 'CSS3'),
		'scroll-snap-stop': ('normal', False, False, 'CSS3'),
		'scroll-snap-type': ('none', False, False, 'CSS3'),
		'tab-size': ('8', True, False, 'CSS3'),
		'text-align-last': ('auto', True, False, 'CSS3'),
		'text-decoration-color': ('currentcolor', False, True, 'CSS3'),
		'text-decoration-line': ('none', False, False, 'CSS3'),
		'text-decoration-style': ('solid', False, False, 'CSS3'),
		'text-emphasis': ('none currentcolor', True, None, 'CSS3'),
		'text-emphasis-color': ('currentcolor', True, None, 'CSS3'),
		'text-emphasis-position': ('over right', True, None, 'CSS3'),
		'text-emphasis-style': ('none', True, None, 'CSS3'),
		'text-justify': ('auto', True, False, 'CSS3'),
		'text-orientation': ('mixed', True, False, 'CSS3'),
		'text-overflow': ('clip', False, False, 'CSS3'),
		'text-shadow': ('none', True, True, 'CSS3'),
		'text-underline-position': ('auto', True, False, 'CSS3'),
		'transform': ('none', False, True, 'CSS3'),
		'transform-origin': ('50% 50% 0', False, True, 'CSS3'),
		'transform-style': ('flat', False, False, 'CSS3'),
		'transition': ('all 0s ease 0s', False, False, 'CSS3'),
		'transition-delay': ('0s', False, False, 'CSS3'),
		'transition-duration': ('0s', False, False, 'CSS3'),
		'transition-property': ('all', False, False, 'CSS3'),
		'transition-timing-function': ('ease', False, False, 'CSS3'),
		'translate': ('none', False, True, 'CSS3'),
		'user-select': ('auto', False, False, 'CSS3'),
		'widows': ('2', True, False, 'CSS3'),
		'word-break': ('normal', True, False, 'CSS3'),
		'word-wrap': ('normal', True, False, 'CSS3'),
		'writing-mode': ('horizontal-tb', True, False, 'CSS3'),
		
		'column-gap': ('normal', False, True, 'CSS Box Alignment Module Level 3'),
		'gap': ('normal normal', False, True, 'CSS Box Alignment Module Level 3'),
		
		'grid': ('none none none auto auto row', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-area': ('auto / auto / auto / auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-auto-columns': ('auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-auto-flow': ('row', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-auto-rows': ('auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-column': ('auto / auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-column-end': ('auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-column-start': ('auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-row': ('auto / auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-row-end': ('auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-row-start': ('auto', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-template': ('none none none', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-template-areas': ('none', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-template-columns': ('none', False, True, 'CSS Grid Layout Module Level 1'),
		'grid-template-rows': ('none', False, True, 'CSS Grid Layout Module Level 1'),

		'clip-path': ('none', False, True, 'CSS Masking Module Level 1'),
		'mask': ('none match-source repeat 0% 0% border-box border-box auto add', False, False, 'CSS Masking Module Level 1'),
		'mask-clip': ('border-box', False, False, 'CSS Masking Module Level 1'),
		'mask-composite': ('add', False, False, 'CSS Masking Module Level 1'),
		'mask-image': ('none', False, False, 'CSS Masking Module Level 1'),
		'mask-mode': ('match-source', False, False, 'CSS Masking Module Level 1'),
		'mask-origin': ('border-box', False, False, 'CSS Masking Module Level 1'),
		'mask-position': ('0% 0%', False, False, 'CSS Masking Module Level 1'),
		'mask-repeat': ('repeat', False, False, 'CSS Masking Module Level 1'),
		'mask-size': ('auto', False, False, 'CSS Masking Module Level 1'),
		'mask-type': ('luminance', False, False, 'CSS Masking Module Level 1'),
		
		'color-scheme': ('normal', True, None, 'CSS Color Adjustment Module Level 1'),
		
		'row-gap': ('normal', False, True, 'CSS Box Alignment Module Level 3'),
		
		'scrollbar-color': ('auto', True, False, 'CSS Scrollbars Styling Module Level 1'),
		
		'shape-outside': ('none', False, True, 'CSS Shapes Module Level 1'),
		
		'zoom': ('normal', False, True, 'CSS Viewport Module Level 1'),
		
		'scroll-behavior': ('auto', False, False, 'CSSOM View Module (Working Draft)'),
		
		'accent-color': ('auto', True, False, 'CSS4'),
		'hyphenate-character': ('auto', True, False, 'CSS4'),
		'text-decoration-thickness': ('auto', False, False, 'CSS4'),
		'text-underline-offset': ('auto', True, False, 'CSS4')
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
		'b': {'font-weight':'bold'}, # 	Displays text in a bold style.
		'base': {}, # 	Defines the base URL for all relative URLs in a document.
		'basefont': {}, # 	[OBSOLETE] Specifies the base font for a page. Use CSS instead.
		'bdi': {}, # 	Represents text that is isolated from its surrounding for the purposes of bidirectional text formatting.
		'bdo': {}, # 	Overrides the current text direction.
		'big': {'font-size':'x-large'}, # 	[OBSOLETE] Displays text in a large size. Use CSS instead.
		'blockquote': {}, # 	Represents a section that is quoted from another source.
		'body': {}, # 	Defines the document's body.
		'br': {'content':"'\n'"}, # 	Produces a single line break.
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
		'hr': {'height':'2px', 'background-color':'green', 'margin-top':'5px', 'margin-bottom':'5px', 'margin-left':'15px', 'margin-right':'15px'}, # 	Produce a horizontal line.
		'html': {}, # 	Defines the root of an HTML document.
		'i': {'font-style':'italic'}, #		Displays text in an italic style.
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
		'p': {'background-color':'pink', 'margin-left':'10px', 'margin-right':'10px', 'margin-bottom':'2px', 'margin-top':'2px'}, # 	Defines a paragraph.
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
	
	__empty_elements = {
		'hr', 'img'
	}
	
	for element in __empty_elements:
		__default_attribute[element]['content'] = 'none'
	
	__inherited_attributes = frozenset(_attr for _attr, (_, _inherited, _, _) in __initial_attribute.items() if _inherited)
	
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
	
	def image_dimensions(self, view, document, callback):
		"Return the SVG dimensions, that might depend on the view state."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		return self.get_viewport_width(view), self.image_height_for_width(view, document, width, callback)
	
	def image_width_for_height(self, view, document, height, callback):
		if not self.is_html_document(document):
			return NotImplemented
		return self.get_viewport_width(view)
	
	def image_height_for_width(self, view, document, width, callback):
		if not self.is_html_document(document):
			return NotImplemented
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.getroot()
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		recreate = False
		try:
			tree, w, h = self.__cache[document]
		except KeyError:
			recreate = True
		else:
			if box[2:] != (w, h):
				recreate = True
		
		if recreate:
			new_callback = self.__make_inline_callback(view, document, callback)
			tree = self.__produce_tree(view, document, node, None)
			#tree.reformat(self, view)
			tree.measure(self, view, ctx, box[2], box[3], new_callback)
			self.__cache[document] = tree, box[2], box[3]
		
		return tree.height
	
	def __remove_whitespace(self, text):
		text = text.translate(str.maketrans({"\t":" ", "\r":" ", "\n":" "}))
		while "  " in text:
			text = text.replace("  ", " ")
		return text
	
	def __produce_tree(self, view, document, node, pseudoelement):
		if not isinstance(node.tag, str): return
		xmlns, tag = node.tag.split('}')
		xmlns = xmlns[1:]
		
		display = self.__get_attribute(view, document, node, pseudoelement, 'display')
		if display == 'none':
			return None
		
		children = []
		content = self.__get_attribute(view, document, node, pseudoelement, 'content')
		if content == 'none': # Don't recurse into elements that are defined as empty.
			children = None
		elif content.startswith('\'') or content.startswith('\"'):
			children.append(Text(content[1:-1]))
		else:
			if content != 'normal': pass # warning
			white_space = self.__get_attribute(view, document, node, pseudoelement, 'white-space')
			preserve_whitespace = white_space in {'pre', 'pre-line', 'pre-wrap'}
			
			if node.text:
				text = Text(node.text if preserve_whitespace else self.__remove_whitespace(node.text))
				children.append(text)
			
			for child in node:
				item = self.__produce_tree(view, document, child, None)
				if item:
					children.append(item)
				
				if child.tail:
					text = Text(child.tail if preserve_whitespace else self.__remove_whitespace(child.tail))
					children.append(text)
		
		if display == 'inline':
			path = document.getpath(node) # TODO: pseudoelement
			#path = tag
			
			if children is None:
				result = Text(f"\x1bX+{path}\x1b\\\x1bX-{path}\x1b\\")
			elif all(isinstance(_child, Text) for _child in children):
				result = sum(children, Text())
				if result:
					result.wrap(f"\x1bX+{path}\x1b\\", f"\x1bX-{path}\x1b\\")
					pass
				else:
					result = None
			else:
				result = Block(document, node, pseudoelement, children)
			
			return result
		
		elif display == 'block':
			path = document.getpath(node) # TODO: pseudoelement
			result = Block(document, node, pseudoelement, children)
			result.reformat(self, view)
			result.wrap(f"\x1bX+{path}\x1b\\", f"\x1bX-{path}\x1b\\")
			return result
		
		else:
			raise NotImplementedError
	
	def draw_image(self, view, document, ctx, box, callback):
		"Perform HTML rendering."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.getroot()
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		recreate = False
		try:
			tree, w, h = self.__cache[document]
		except KeyError:
			recreate = True
		else:
			if box[2:] != (w, h):
				recreate = True
		
		if recreate:
			new_callback = self.__make_inline_callback(view, document, callback)
			tree = self.__produce_tree(view, document, node, None)
			tree.measure(self, view, ctx, box[2], box[3], new_callback)
			self.__cache[document] = tree, box[2], box[3]
		
		tree.render(self, view, ctx, box, new_callback)
	
	def poke_image(self, view, document, ctx, box, px, py, callback):
		if not self.is_html_document(document):
			return NotImplemented
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.getroot()
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		recreate = False
		try:
			tree, w, h = self.__cache[document]
		except KeyError:
			recreate = True
		else:
			if box[2:] != (w, h):
				recreate = True
		
		if recreate:
			new_callback = self.__make_inline_callback(view, document, callback)
			tree = self.__produce_tree(view, document, node, None)
			tree.measure(self, view, ctx, box[2], box[3], new_callback)
			self.__cache[document] = tree, box[2], box[3]
		
		hover = tree.poke(self, view, ctx, box, new_callback, px, py)
		assert hover is not None
		return hover
	
	def __block_enter(self, view, document, node, pseudoelement, ctx, box):
		ctx.save()
		
		try:
			ctx.set_source_rgba(*self.__get_color(view, document, node, pseudoelement, 'background-color', 'opacity', 'transparent'))
		except TypeError:
			pass
		else:
			ctx.rectangle(*box)
			ctx.fill()
		
		#ctx.set_source_rgba(*self.__get_color(view, document, node, pseudoelement, 'color', 'opacity', 'black'))
		#font_family, font_size, line_height, font_style, font_variant, font_weight = self.__get_font(view, document, node, pseudoelement, 16) # TODO
		#ctx.select_font_face(font_family, font_style, font_weight)
		#ctx.set_font_size(font_size)
	
	def __block_exit(self, view, document, node, pseudoelement, ctx, box):
		ctx.restore()
	
	def __inline_enter(self, view, document, node, pseudoelement, ctx, pango_layout, stack):
		ctx.save()
		ctx.set_source_rgba(*self.__get_color(view, document, node, pseudoelement, 'color', 'opacity', 'black'))
		font_family, font_size, line_height, font_style, font_variant, font_weight = self.__get_font(view, document, node, pseudoelement, 16) # TODO
		ctx.select_font_face(font_family, font_style, font_weight)
		ctx.set_font_size(font_size)
	
	def __inline_exit(self, view, document, node, pseudoelement, ctx, pango_layout, stack):
		ctx.restore()
	
	def __make_inline_callback(self, view, document, old_callback):
		stack = []
		
		def new_callback(reason, params):
			result = False
			
			if reason == Escape.end_escape:
				result = True
			
			result |= old_callback(reason, params)
			
			if reason == Escape.begin_escape:
				path, ctx, pango_layout = params
				state = path[2]
				if state == '+':
					node = document.xpath(path[3:-2])[0]
					pseudoelement = None # TODO
					self.__inline_enter(view, document, node, pseudoelement, ctx, pango_layout, stack)
					
				elif state == '-':
					node = document.xpath(path[3:-2])[0]
					pseudoelement = None # TODO
					self.__inline_exit(view, document, node, pseudoelement, ctx, pango_layout, stack)
				
				else:
					raise ValueError
				
				result = True
			
			return result
		
		return new_callback
	
	def __get_font(self, view, document, element, pseudoelement, em_size):
		font = self.__get_attribute(view, document, element, pseudoelement, 'font')
		font_family = self.__get_attribute(view, document, element, pseudoelement, 'font-family')
		font_size = self.__get_attribute(view, document, element, pseudoelement, 'font-size')
		
		if font_size == 'xx-small':
			font_size = '10'
		elif font_size == 'x-small':
			font_size = '12'
		elif font_size == 'small':
			font_size = '14'
		elif font_size == 'medium':
			font_size = '16'
		elif font_size == 'large':
			font_size = '18'
		elif font_size == 'x-large':
			font_size = '20'
		elif font_size == 'xx-large':
			font_size = '24'
		
		line_height = self.__get_attribute(view, document, element, pseudoelement, 'line-height')
		if line_height == 'normal':
			line_height = '100%'
		
		font_style = self.__get_attribute(view, document, element, pseudoelement, 'font-style')
		font_variant = self.__get_attribute(view, document, element, pseudoelement, 'font-variant')
		font_weight = self.__get_attribute(view, document, element, pseudoelement, 'font-weight')
		#print(element.tag, font, font_family, font_size, line_height, font_style, font_variant, font_weight)
		
		#print(element.tag, font_style)
		return font_family, self.units(view, font_size, percentage=em_size), self.units(view, line_height, percentage=em_size), cairo.FontSlant.ITALIC if font_style == 'italic' else cairo.FontSlant.NORMAL, None, cairo.FontWeight.BOLD if font_weight == 'bold' else cairo.FontWeight.NORMAL	
	
	def __get_color(self, view, document, element, pseudoelement, color_attr, opacity_attr, default_color):
		"Set painting source to the color identified by provided parameters."
		
		color = self.__get_attribute(view, document, element, pseudoelement, color_attr)
		if color is None: color = default_color
		target = element.getparent()
		while color in ('currentcolor', 'inherit') and (target is not None):
			if color == 'currentcolor':
				color = self.__get_attribute(view, document, element, pseudoelement, 'color')
				if color is None: color = default_color
			elif color == 'inherit':
				color = self.__get_attribute(view, document, element, pseudoelement, color_attr)
				if color is None: color = default_color
			target = target.getparent()
		
		if color == 'currentcolor' or color == 'inherit': # FIXME: workaround, delete it
			color = default_color
		
		assert color != 'currentcolor' and color != 'inherit'
		
		try:
			color = self.web_colors[color.lower()]
		except KeyError:
			pass
		
		try:
			if not color or color.lower() in ('none', 'transparent'):
				return None
		except AttributeError:
			pass
		
		if opacity_attr is not None:
			opacity = self.__get_attribute(view, document, element, pseudoelement, opacity_attr)
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
			r, g, b = [clamp(0, parse_float(_c) / 255 if _c.strip()[-1] != '%' else parse_float(_c.strip()[:-1]) / 100, 1) for _c in color[4:-1].split(',')]
		
		elif color[:4] == 'hsl(' and color[-1] == ')':
			cc = color[4:-1].split(',')
			
			h = clamp(0, parse_float(cc[0]), 360) / 360
			s = clamp(0, parse_float(cc[1] if cc[1][-1] != '%' else cc[1][:-1]), 100) / 100
			l = clamp(0, parse_float(cc[2] if cc[2][-1] != '%' else cc[2][:-1]), 100) / 100
			
			r, g, b = hls_to_rgb(h, l, s)
		
		else:
			self.emit_warning(view, f"Unsupported color specification: {color}.", node)
			return None
		
		return r, g, b
	
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
	
	@cached
	def __get_attribute(self, view, document, node, pseudoelement, attr):
		result = self.__search_attribute(view, document, node, pseudoelement, attr)
		
		if result is None and attr in self.__inherited_attributes:
			if pseudoelement:
				result = self.__search_attribute(view, document, node, None, attr)
			ancestor = node.getparent()
			while result is None and ancestor is not None:
				result = self.__search_attribute(view, document, ancestor, None, attr)
				
				if result is None:
					xmlns, tag = ancestor.tag.split('}')
					xmlns = xmlns[1:]
					
					if xmlns == self.__xmlns(document):
						try:
							default_style = self.__default_attribute[tag]
						except KeyError:
							print(f"Unsupported tag: {tag}")
						else:
							#print(tag, default_style)
							try:
								result = default_style[attr]
							except KeyError:
								pass
				
				ancestor = ancestor.getparent()
		
		if result is None:
			xmlns, tag = node.tag.split('}')
			xmlns = xmlns[1:]
			
			if xmlns == self.__xmlns(document):
				try:
					default_style = self.__default_attribute[tag]
				except KeyError:
					print(f"Unsupported tag: {tag}")
				else:
					#print(tag, default_style)
					try:
						result = default_style[attr]
					except KeyError:
						pass
		
		if result is None:
			try:
				result = self.__initial_attribute[attr][0]
			except KeyError:
				print(f"Unsupported attribute: {attr}")
		
		#print(node.tag, attr, result)
		return result
	
	@cached
	def __search_attribute(self, view, document, node, pseudoelement, attr):
		xmlns_html = self.__xmlns(document)
		
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
						result = self.eval_css_value(raw_value) # TODO: css vars
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
			return css_value
		
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
	if len(sys.argv) == 1:
		test_type = 0
	elif len(sys.argv) != 2:
		print("Provide one of the arguments: --test-1 --test-2 --test-3 --test-4.")
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


if __debug__ and __name__ == '__main__' and test_type == 0:
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
			r = super().draw_image(view, document, ctx, box, (lambda _reason, _params: True))
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
				assert rnd._HTMLRender__get_attribute(view, document, h1, None, 'display') == 'block'
			
			rnd.tree = document
			rnd.draw_image(view, document, ctx, (0, 0, 1000, 800))
			
			#profiler.done()


if __debug__ and __name__ == '__main__' and test_type != 0:
	from asyncio import run, get_running_loop
	from lxml.html import document_fromstring as html_frombytes, tostring as html_tobytes
	from lxml.etree import fromstring as xml_frombytes, tostring as xml_tobytes, _ElementTree, XMLParser
	from urllib.parse import unquote as url_unquote
	
	import gi
	gi.require_version('Gtk', '4.0')
	from gi.repository import Gtk
	
	from guixmpp.mainloop import *
	from guixmpp.domevents import *
	
	DOMEvent = Event
	
	
	class ElementTree(_ElementTree):
		def __init__(self, element):
			self._setroot(element)
	
	
	class HTMLRenderTest(HTMLRender, TextFormat, CSSFormat):
		def __init__(self, *args, **kwargs):
			HTMLRender.__init__(self, *args, **kwargs)
			TextFormat.__init__(self, *args, **kwargs)
			self.xml_parser = XMLParser()
		
		def create_document(self, data, mime):
			if mime == 'text/xml' or mime == 'application/xml' or mime.endswith('+xml'):
				data = data.replace("&nbsp;", "\xa0")
				root = xml_frombytes(data)
				document = ElementTree(root)
				return document
			elif mime == 'text/sgml' or mime == 'application/sgml':
				sgml_text = data
				sgml_doc = html_frombytes(sgml_text)
				xml_text = html_tobytes(sgml_doc, encoding='utf-8', method='xml')
				root = xml_frombytes(xml_text)
				document = ElementTree(root)
				return document
			elif mime == 'application/xhtml' or mime == 'application/xhtml+xml' or mime == 'text/html':
				return super().create_document(data, mime)
			elif mime == 'text/css':
				return CSSFormat.create_document(self, data, mime)
			else:
				print('unsupported mime', mime)
				return NotImplemented
		
		def get_document_url(self, document):
			return '.'
		
		def get_document(self, url):
			if url.startswith('data:text/css,'):
				data = url_unquote(url[14:]).encode('utf-8')
				return self.create_document(data, 'text/css')
			else:
				return None
		
		def is_xml_document(self, document):
			return hasattr(document, 'getroot')
		
		def image_height_for_width(self, view, document, width, callback):
			if self.is_text_document(document):
				return TextFormat.image_height_for_width(self, view, document, width, callback)
			elif self.is_html_document(document):
				return HTMLRender.image_height_for_width(self, view, document, width, callback)
			else:
				return NotImplemented
		
		def draw_image(self, view, document, ctx, box, callback):
			if self.is_text_document(document):
				return TextFormat.draw_image(self, view, document, ctx, box, callback)
			elif self.is_html_document(document):
				return HTMLRender.draw_image(self, view, document, ctx, box, callback)
			else:
				return NotImplemented
		
		def get_dpi(self, view):
			return 96
	
	
	loop_init()
	
	window = Gtk.Window()
	window.set_title("HTML test widget")
	widget = Gtk.DrawingArea()
	window.set_child(widget)
	window.connect('close-request', lambda *_: loop_quit())
	
	model = HTMLRenderTest()
	
	if test_type == 1:
		document = model.create_document("""<!DOCTYPE html>
			<html>
			<head><title>Ex Oblivione</title></head>
			<body>
			<h1>Ex Oblivione</h1>
			<h2>By H. P. Lovecraft</h2>
			
			<p>When the last days were upon me, and the ugly trifles of existence began to drive me to madness like the small drops of water that torturers let fall ceaselessly upon one spot of their victim’s body, I loved the irradiate refuge of sleep. In my dreams I found a little of the beauty I had vainly sought in life, and wandered through old gardens and enchanted woods.</p>
			<p>Once when the wind was soft and scented I heard the south calling, and sailed endlessly and languorously under strange stars.</p>
			<p>Once when the gentle rain fell I glided in a barge down a sunless stream under the earth till I reached another world of purple twilight, iridescent arbours, and undying roses.</p>
			<p>And once I walked through a golden valley that led to shadowy groves and ruins, and ended in a mighty wall green with antique vines, and pierced by a little gate of bronze.</p>
			<p>Many times I walked through that valley, and longer and longer would I pause in the spectral half-light where the giant trees squirmed and twisted grotesquely, and the grey ground stretched damply from trunk to trunk, sometimes disclosing the mould-stained stones of buried temples. And always the goal of my fancies was the mighty vine-grown wall with the little gate of bronze therein.</p>
			<p>After a while, as the days of waking became less and less bearable from their greyness and sameness, I would often drift in opiate peace through the valley and the shadowy groves, and wonder how I might seize them for my eternal dwelling-place, so that I need no more crawl back to a dull world stript of interest and new colours. And as I looked upon the little gate in the mighty wall, I felt that beyond it lay a dream-country from which, once it was entered, there would be no return.</p>
			<p>So each night in sleep I strove to find the hidden latch of the gate in the ivied antique wall, though it was exceedingly well hidden. And I would tell myself that the realm beyond the wall was not more lasting merely, but more lovely and radiant as well.</p>
			<p>Then one night in the dream-city of Zakarion I found a yellowed papyrus filled with the thoughts of dream-sages who dwelt of old in that city, and who were too wise ever to be born in the waking world. Therein were written many things concerning the world of dream, and among them was lore of a golden valley and a sacred grove with temples, and a high wall pierced by a little bronze gate. When I saw this lore, I knew that it touched on the scenes I had haunted, and I therefore read long in the yellowed papyrus.</p>
			<p>Some of the dream-sages wrote gorgeously of the wonders beyond the irrepassable gate, but others told of horror and disappointment. I knew not which to believe, yet longed more and more to cross forever into the unknown land; for doubt and secrecy are the lure of lures, and no new horror can be more terrible than the daily torture of the commonplace. So when I learned of the drug which would unlock the gate and drive me through, I resolved to take it when next I awaked.</p>
			<p>Last night I swallowed the drug and floated dreamily into the golden valley and the shadowy groves; and when I came this time to the antique wall, I saw that the small gate of bronze was ajar. From beyond came a glow that weirdly lit the giant twisted trees and the tops of the buried temples, and I drifted on songfully, expectant of the glories of the land from whence I should never return.</p>
			<p>But as the gate swung wider and the sorcery of drug and dream pushed me through, I knew that all sights and glories were at an end; for in that new realm was neither land nor sea, but only the white void of unpeopled and illimitable space. So, happier than I had ever dared hoped to be, I dissolved again into that native infinity of crystal oblivion from which the daemon Life had called me for one brief and desolate hour.</p>
			</body>
			</html>
		""", 'text/html')
	
	elif test_type == 2:
		document = model.create_document("""<?xml version="1.0"?>
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
	""", 'application/xhtml+xml')

	elif test_type == 3:
		document = model.create_document("""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
 <title>A Garden</title>
</head>
<body>
<h1>A Garden</h1>
<h2>By H. P. Lovecraft</h2>
<hr/>
<p>
<span style="color:#000030;">There’s an ancient, <i>ancient</i> garden that I see sometimes in dreams,<br/>
Where the very <b>Maytime</b> sunlight plays and glows with spectral gleams;<br/>
Where the <i>gaudy-<b>tinted</b> blossoms</i> seem to wither into grey,<br/>
And the crumbling walls and pillars waken thoughts of yesterday.</span><br/>
<span style="color:#000060; font-family:serif">There are vines in nooks and crannies, and there’s moss about the pool,<br/>
And the tangled weedy thicket chokes the arbour dark and cool:<br/>
In the silent sunken pathways springs an herbage sparse and spare,<br/>
Where the musty scent of dead things dulls the fragrance of the air.</span><br/>
<span style="color:#000090; font-family:Arial">There is not a living creature in the lonely space around,<br/>
And the hedge-encompass’d quiet never echoes to a sound.</span><br/>
<span style="color:#0000c0; font-family:Tahoma">As I walk, and wait, and listen, I will often seek to find<br/>
When it was I knew that garden in an age long left behind;<br/>
I will oft conjure a vision of a day that is no more,<br/>
As I gaze upon the grey, grey scenes I feel I knew before.</span><br/>
<span style="color:#0000f0; font-size:20px">Then a sadness settles o’er me, and a tremor seems to start:<br/>
<hr/>
For I know the flow’rs are shrivell’d hopes—the garden is my heart!</span>
</p>
<hr/>
</body>
</html>
""", 'application/xhtml+xml')

	elif test_type == 4:
		document = model.create_document("""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
 <title>A Garden</title>
</head>
<body>
 aaa <i>bbb <b>ccc</b> ddd</i> eee<br/>
 aaa <b>bbb <i>ccc</i> ddd</b> eee<br/>
 aaa <b>bbb <span style="font-weight:normal">ccc</span> ddd</b> eee<br/>
 aaa <b>bbb <span style="font-style:italic">ccc</span> ddd</b> eee<br/>
</body>
</html>
""", 'application/xhtml')
	
	
	def render(widget, ctx, width, height):		
		model.draw_image(widget, document, ctx, (0, 0, width, height), (lambda _reason, _params: True))
	
	widget.set_draw_func(render)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
	
	run(main())

