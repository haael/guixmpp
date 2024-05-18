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

#import PIL.Image, PIL.ImageFilter

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


class BoxTree:
	def __init__(self, node, pseudoelement, style=None, content=None):
		self.node = node
		self.pseudoelement = pseudoelement
		self.style = {}
		if style:
			self.style.update(style)
		self.content = content
	
	def debug_print(self, level=0):
		if isinstance(self.node, str):
			print(level * " ", repr(self.node), self.style)
		else:
			print(level * " ", (self.node.tag if hasattr(self.node, 'tag') else '-') + ('::' + self.pseudoelement if self.pseudoelement else ''), self.style)
		
		if self.content is not None:
			for child in self.content:
				child.debug_print(level + 1)
	
	def ensure_xywh(self):
		assert 'x' in self.style
		assert 'y' in self.style
		assert 'width' in self.style, f"{self.node}::{self.pseudoelement}"
		assert 'height' in self.style
		
		if self.content is not None:
			for child in self.content:
				child.ensure_xywh()


class HTMLRender:
	xmlns_xml = XMLFormat.xmlns_xml
	xmlns_xlink = XMLFormat.xmlns_xlink
	
	xmlns_html = 'http://www.w3.org/1999/xhtml'
	xmlns_html2 = 'http://www.w3.org/2002/06/xhtml2'
	
	#web_colors = CSSFormat.web_colors
	
	__whitespace_chars = ("\n", "\r", "\t", "\xA0", " ")
	
	def __init__(self, *args, **kwargs):
		self.__css_matcher = WeakKeyDictionary()
	
	def create_document(self, data, mime_type):
		if mime_type == 'application/xhtml' or mime_type == 'application/xhtml+xml' or mime_type == 'text/html':
			if mime_type == 'text/html':
				document = self.create_document(data, 'text/x-html-tag-soup')
			else:
				document = self.create_document(data, 'application/xml')
			
			if document.getroot().tag == 'html': # document without namespace
				del document.getroot().attrib['xmlns'] # workaround: lxml sets xmlns twice
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			if document.getroot().tag == 'html': # still without namespace
				document.getroot().attrib['xmlns'] = self.xmlns_html
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			if self.is_html_document(document):
				return document
			else:
				raise ValueError("Not an HTML document.")
		else:
			return NotImplemented
	
	def is_html_document(self, document):
		if self.is_xml_document(document):
			return document.getroot().tag.startswith('{' + self.xmlns_html + '}') or document.getroot().tag.startswith('{' + self.xmlns_html2 + '}')
		else:
			try:
				return document.tag.startswith('{' + self.xmlns_html + '}') or document.tag.startswith('{' + self.xmlns_html2 + '}')
			except AttributeError:
				return False
	
	def __xmlns(self, document):
		try:
			return document.getroot().tag.split('}')[0][1:]
		except AttributeError:
			return document.tag.split('}')[0][1:]
	
	def scan_document_links(self, document):
		"Yield all links referenced by the HTML document, including `data:` links."
		
		if self.is_html_document(document):
			def links():
				yield 'chrome://html.css'
				yield from document.scan_stylesheets()
				yield from self.__xlink_hrefs(document)
				yield from self.__data_internal_links(self.__style_attrs(document))
				yield from self.__data_internal_links(self.__style_tags(document))
				yield from self.__style_links(document)
				#yield from self.__script_tags(document)
			return links()
		else:
			return NotImplemented
	
	def __xlink_hrefs(self, document):
		xmlns_html = self.__xmlns(document)
		for linkedtag in document.findall(f'.//*[@{{{self.xmlns_xlink}}}href]'):
			if linkedtag.tag == f'{{{self.xmlns_html}}}a' or linkedtag.tag.split('}')[0][1:] not in [self.xmlns_html, self.xmlns_html2]:
				continue
			href = linkedtag.attrib[f'{{{self.xmlns_xlink}}}href']
			yield href
		for linkedtag in document.findall(f'.//*[@href]'):
			if linkedtag.tag == f'{{{xmlns_html}}}a' or linkedtag.tag.split('}')[0][1:] not in [self.xmlns_html, self.xmlns_html2]:
				continue
			href = linkedtag.attrib['href']
			yield href
	
	def __data_internal_links(self, urls):
		"Recursively examine provided urls for internal urls they may reference."
		
		for url in urls:
			yield url
			if url.startswith('data:'):		
				yield from self.__data_internal_links(self.scan_document_links(self.get_document(url)))
	
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
	
	def draw_image(self, view, document, ctx, box):
		"Perform HTML rendering."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.findall(f'.//{{{xmlns_html}}}body')[0] # FIXME
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		tree = self.__create_box(view, document, ctx, node, None, xmlns_html, 16)
		tree.style['display'] = 'block'
		self.__position_horizontal(view, ctx, document, tree, None, box[2])
		self.__position_lines(tree, None)
		self.__position_vertical(view, ctx, document, tree, None, box[3])
		tree.style['width'] = tree.style['max-width']
		#tree.debug_print()
		if __debug__: tree.ensure_xywh()
		self.__render_box(view, ctx, document, tree, None, box[0], box[1])
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		if hasattr(document, 'getroot'):
			node = document.findall(f'.//{{{xmlns_html}}}body')[0]
		else:
			document = document.getroottree().getroot().create_document()
			node = document.findall(f'.//{{{xmlns_html}}}body')[0]
		
		#return self.__render_tag(view, document, ctx, box, node, em_size, (px, py))
		return []
	
	def __split_words(self, text):
		word = []
		for ch in text:
			if ch in self.__whitespace_chars:
				if word:
					yield "".join(word)
					word.clear()
				
				if ch != " ":
					yield ch
			else:
				word.append(ch)
		
		if word:
			yield "".join(word)
	
	def __create_box(self, view, document, ctx, node, pseudoelement, xmlns, em_size):
		display = self.__get_attribute(view, document, node, None, 'display', 'inline')
		if display == 'none':
			return None
		
		visibility = self.__get_attribute(view, document, node, None, 'visibility', 'visible')
		if visibility == 'collapse':
			return None
		
		children = []
		
		font_size_attr = self.__get_attribute(view, document, node, pseudoelement, 'font-size', None)
		if font_size_attr:
			try:
				float(font_size_attr)
			except ValueError:
				em_size = self.units(view, font_size_attr, em_size=em_size)
			else:
				raise ValueError("Font size can't be a unit-less number.")
			
		word_spacing_attr = self.__get_attribute(view, document, node, pseudoelement, 'word-spacing', '0.25em')
		word_spacing = self.units(view, word_spacing_attr, em_size=em_size)
		
		if pseudoelement is None:
			before = self.__get_attribute(view, document, node, 'before', 'content', None)
			if before is not None:
				box = self.__create_box(view, document, ctx, node, 'before', xmlns, em_size)
				if box is not None:
					children.append(box)
			
			for child in chain([None], node):
				if child is None:
					text = node.text
				else:
					if isinstance(child.tag, str): # ignore processing instructions
						box = self.__create_box(view, document, ctx, child, None, xmlns, em_size)
						if box is not None:
							children.append(box)
					text = child.tail
				
				if text:
					children.extend(BoxTree(_word, None) for _word in self.__split_words(text))
			
			after = self.__get_attribute(view, document, node, 'after', 'content', None)
			if after is not None:
				box = self.__create_box(view, document, ctx, node, 'after', xmlns, em_size)
				if box is not None:
					children.append(box)
		
		else:
			text = self.__get_attribute(view, document, node, pseudoelement, 'content', None)
			if text[0] == text[-1] == '\"':
				words = [BoxTree(_word, None) for _word in self.__split_words(text)]
				box = BoxTree(node, pseudoelement, {'word-spacing':word_spacing}, words)
				children.append(box)
			else:
				raise NotImplementedError
		
		if (display == 'inline' and any(_child.style['display'] == 'block' for _child in children if 'display' in _child.style)) or \
		 (display == 'block' and any(_child.style['display'] == 'block' for _child in children if 'display' in _child.style) and any('display' not in _child.style or _child.style['display'] != 'block' for _child in children)):
			# inline element with block elements or block element with mixed inline/block content
			bchildren = []
			ichildren = []
			for child in children:
				if 'display' in child.style and child.style['display'] == 'block':
					if ichildren:
						vchild = BoxTree(None, '-guixmpp-vblock', {'em-size':em_size, 'display':'block', 'word-spacing':word_spacing}, ichildren) # virtual block element
						bchildren.append(vchild)
						ichildren = []
					bchildren.append(child)
				else:
					ichildren.append(child)
			if ichildren:
				vchild = BoxTree(None, '-guixmpp-vblock', {'em-size':em_size, 'display':'block', 'word-spacing':word_spacing}, ichildren) # virtual block element
				bchildren.append(vchild)
				ichildren = []
			box = BoxTree(node, pseudoelement, {'em-size':em_size, 'display':'block', 'visibility':visibility, 'word-spacing':word_spacing}, bchildren)
		
		else:
			box = BoxTree(node, pseudoelement, {'em-size':em_size, 'display':display, 'visibility':visibility, 'word-spacing':word_spacing}, children)
		
		font_family = self.__get_attribute(view, document, node, pseudoelement, 'font-family', None)
		if font_family:
			families = []
			for family in reversed(font_family.split(',')):
				family = family.strip()
				if family[0] in '\'\"':
					family = family[1:]
				if family[-1] in '\'\"':
					family = family[:-1]
				family = family.replace(':', '_')
				families.append(family)
			
			box.style['font-family'] = families
		
		return box
	
	def __walk_tree(self, box):
		yield True, box
		if box.content:
			for child in box.content:
				yield from self.__walk_tree(child)
		yield False, box
	
	def __produce_lines(self, in_box):
		#print("produce lines")
		out_box = BoxTree(in_box.node, in_box.pseudoelement, in_box.style, [])
		
		#src_branch = [in_box]
		dst_branch = [BoxTree(None, '-guixmpp-line', {'x':0, 'content-width':0, 'word-spacing':in_box.style['word-spacing'], 'em-size':in_box.style['em-size']}, [])]
		#out_box.content.append(dst_branch[0])
		
		progress = 0
		line_width = in_box.style['max-width']
		
		for descend, src_el in self.__walk_tree(in_box):
			if src_el is in_box or src_el.node in self.__whitespace_chars:
				continue
			
			#if descend:
			#	print(progress, src_el.node)
			
			#assert len(src_branch) == len(dst_branch)
			
			if descend:
				#src_branch.append(src_el)
				dst_el = BoxTree(src_el.node, src_el.pseudoelement, src_el.style, [] if src_el.content is not None else None)
				dst_el.style.update({'x':0, 'content-width':0})
				dst_branch.append(dst_el)
				
				if src_el.content:
					word_spacing = dst_branch[-1].style['word-spacing']
					nonempty = bool(dst_branch[-1].content)
					progress += (word_spacing if nonempty else 0)
				
				if 'width' not in dst_el.style:
					dst_el.style['width'] = dst_el.style['content-width']
			
			else:
				#del src_branch[-1]
				dst_el = dst_branch[-1]
				del dst_branch[-1]
				
				if not src_el.content:
					dst_el.style['content-width'] = src_el.style['content-width']				
				
				word_spacing = dst_branch[-1].style['word-spacing']
				nonempty = bool(dst_branch[-1].content)
				d_progress = dst_el.style['content-width'] + (word_spacing if nonempty else 0)
				
				if not src_el.content:
					if progress + d_progress <= line_width:
						dst_el.style['x'] = dst_branch[-1].style['content-width'] + (word_spacing if nonempty else 0)
						progress += d_progress
					
					else:
						#print("line", src_el.node, progress, d_progress, progress + d_progress, line_width)
						progress = d_progress = dst_el.style['content-width']
						dst_el.style['x'] = 0
						
						out_box.content.append(dst_branch[0])
						old_branch = dst_branch
						dst_branch = [BoxTree(None, '-guixmpp-line', {'x':0, 'content-width':0, 'word-spacing':in_box.style['word-spacing'], 'em-size':in_box.style['em-size']}, [])]
						
						for old_el in old_branch[1:]:
							new_el = BoxTree(old_el.node, old_el.pseudoelement, old_el.style, [])
							new_el.style.update({'x':0, 'content-width':0})
							dst_branch.append(new_el)
						
						for parent_el, old_el in reversed(list(zip(old_branch[:-1], old_branch[1:]))):
							parent_el.style['content-width'] += old_el.style['content-width'] + (parent_el.style['word-spacing'] if parent_el.content else 0)
							parent_el.style['width'] = parent_el.style['content-width']
							parent_el.content.append(old_el)
				
				else:
					dst_el.style['x'] = dst_branch[-1].style['content-width'] + (word_spacing if nonempty else 0)
				
				#print("ascend", dst_el.node, bool(dst_el.content), 'width' not in dst_el.style)
				if not dst_el.content:
					if 'width' not in dst_el.style:
						dst_el.style['width'] = dst_el.style['content-width']
				
				dst_branch[-1].content.append(dst_el)
				dst_branch[-1].style['content-width'] += d_progress
				dst_branch[-1].style['width'] = dst_branch[-1].style['content-width']
		
		#out_box.debug_print()
		#print()
		
		if dst_branch[0].content:
			out_box.content.append(dst_branch[0])
		
		if len(out_box.content) == 0:
			out_box.style['width'] = 0
		elif len(out_box.content) == 1:
			out_box.style['width'] = out_box.content[0].style['width']
		else:
			out_box.style['width'] = out_box.style['max-width']
		
		return out_box
	
	def __position_lines(self, box, parent):
		node = box.node
		pseudoelement = box.pseudoelement
		
		if node is None:
			node = parent.node
		
		if not ((box.content) and ('display' in box.style) and (box.style['display'] == 'block')):
			#print("not block", node, pseudoelement)
			pass
		
		elif any((('display' not in _child.style) or (_child.style['display'] != 'block')) and _child.node not in self.__whitespace_chars for _child in box.content):
			#print("block of inline", node, pseudoelement)
			
			lbox = self.__produce_lines(box)
			box.content = lbox.content
			box.style.update(lbox.style)
		
		elif box.content is not None:
			#print("block of block", node, pseudoelement)
			
			box.content = [_child for _child in box.content if _child.node not in self.__whitespace_chars]
			
			w = 0
			for child in box.content:
				self.__position_lines(child, box)
				w = max(w, child.style.get('width', 0))
			
			if 'width' not in box.style:
				box.style['width'] = w
	
	def __position_horizontal(self, view, ctx, document, box, parent, viewport_width):
		node = box.node
		pseudoelement = box.pseudoelement
		
		if node is None:
			node = parent.node
		
		try:
			font_family = box.style['font-family']
		except KeyError:
			pass
		else:
			for family in font_family:
				ctx.select_font_face(family)
		
		if isinstance(node, str):
			if node in self.__whitespace_chars:
				box.style['content-width'] = 0
				box.style['content-height'] = 0
				#box.style['break-before'] = 'always'
			else:
				em_size = parent.style['em-size']
				ctx.set_font_size(em_size)
				extents = ctx.text_extents(node)
				#box.style['extents'] = extents
				box.style['content-width'] = box.style['width'] = extents.width
				box.style['content-height'] = 1.25 * em_size # TODO: line height
		
		elif box.style['display'] in ('inline', 'inline-block'):
			# TODO: support various element types
			#print("inline element initial content width", node, len(box.content) if box.content is not None else None)
			if hasattr(node, 'tag') and not box.content:
				box.style['content-width'] = 0
				box.style['content-height'] = 0
				#if node.tag == f'{{{self.__xmlns(document)}}}br':
				#	box.style['content-width'] = 0
				#elif node.tag.startswith(f'{{{self.__xmlns(document)}}}'):
				#	box.style['content-width'] = 80
		
		elif box.style['display'] == 'block':
			em_size = box.style['em-size']
			
			width = self.__get_attribute(view, document, node, None, 'width', 'auto')
			width = self.units(view, width, percentage=viewport_width, em_size=em_size) if width != 'auto' else None
			
			margin = self.__get_attribute(view, document, node, None, 'margin', '')
			margins = re.split(r'[, ]+', margin) # TODO: better regex
			if len(margins) == 0:
				margin_left = margin_right = margin_top = margin_bottom = 'auto'
			elif len(margins) == 1:
				margin_left = margin_right = margin_top = margin_bottom = margins[0]
			elif 2 <= len(margins) <= 3:
				margin_left = margin_right = margins[0]
				margin_top = margin_bottom = margins[1]
			elif len(margins) >= 4:
				margin_left, margin_top, margin_right, margin_bottom, *_ = margins
			
			margin_left = self.__get_attribute(view, document, node, None, 'margin-left', margin_left)
			margin_right = self.__get_attribute(view, document, node, None, 'margin-right', margin_right)
			
			margin_left = self.units(view, margin_left, percentage=viewport_width, em_size=em_size) if margin_left != 'auto' else None
			margin_right = self.units(view, margin_right, percentage=viewport_width, em_size=em_size) if margin_right != 'auto' else None
			
			if parent is not None:
				parent_width = parent.style['max-width']
			else:
				parent_width = viewport_width
			
			if width is not None:
				box.style['width'] = width
				if margin_left is not None:
					x = margin_left
				elif margin_right is not None:
					x = parent_width - width - margin_right
				else:
					x = 0
			else:
				width = parent_width - margin_left - margin_right
				x = margin_left
			
			box.style['x'] = x
			box.style['max-width'] = width
		
		if box.content is not None:
			for child in box.content:
				self.__position_horizontal(view, ctx, document, child, box, viewport_width)
	
	def __position_vertical(self, view, ctx, document, box, parent, viewport_height):
		node = box.node
		pseudoelement = box.pseudoelement
		
		if node is None:
			node = parent.node
		
		if box.style.get('display', None) != 'block':
			if box.content is not None:
				h = 0
				for child in box.content:
					self.__position_vertical(view, ctx, document, child, box, viewport_height)
					child.style['y'] = 0
					h = max(h, child.style['height'])
				box.style['height'] = h
			
			else:
				box.style['height'] = box.style['content-height']
		
		else:
			em_size = box.style['em-size']
			
			height_attr = self.__get_attribute(view, document, node, None, 'height', 'auto')
			height = self.units(view, height_attr, percentage=viewport_height, em_size=em_size) if height_attr != 'auto' else None
			
			margin = self.__get_attribute(view, document, node, None, 'margin', '')
			margins = re.split(r'[, ]+', margin) # TODO: better regex
			if len(margins) == 0:
				margin_left = margin_right = margin_top = margin_bottom = 'auto'
			elif len(margins) == 1:
				margin_left = margin_right = margin_top = margin_bottom = margins[0]
			elif 2 <= len(margins) <= 3:
				margin_left = margin_right = margins[0]
				margin_top = margin_bottom = margins[1]
			elif len(margins) >= 4:
				margin_left, margin_top, margin_right, margin_bottom, *_ = margins
			
			margin_top = self.__get_attribute(view, document, node, None, 'margin-top', margin_top)
			margin_bottom = self.__get_attribute(view, document, node, None, 'margin-bottom', margin_bottom)
			
			margin_top = self.units(view, margin_top, percentage=viewport_height, em_size=em_size) if margin_top != 'auto' else 0
			margin_bottom = self.units(view, margin_bottom, percentage=viewport_height, em_size=em_size) if margin_bottom != 'auto' else 0
			
			y = 0 # padding_top
			if box.content is not None:
				for child in box.content:
					self.__position_vertical(view, ctx, document, child, box, viewport_height)
					#if child.style.get('display', None) == 'block' or child.pseudoelement == '-guixmpp-line':
					child.style['y'] = y + child.style.get('y', 0) + + child.style.get('margin-top', 0)
					y += child.style.get('margin-top', 0) + child.style['height'] + child.style.get('margin-bottom', 0)
					#else:
					#	if 'y' not in child.style: child.style['y'] = y
			
			box.style['margin-top'] = margin_top
			box.style['height'] = y
			box.style['margin-bottom'] = margin_bottom
			if 'y' not in box.style: box.style['y'] = 0
	
	def __render_box(self, view, ctx, document, box, parent, x, y):
		node = box.node
		pseudoelement = box.pseudoelement
		
		if node is None:
			node = parent.node
		
		try:
			font_family = box.style['font-family']
		except KeyError:
			pass
		else:
			for family in font_family:
				ctx.select_font_face(family)
		
		if isinstance(box.node, str):
			x += box.style['x']
			y += box.style['y']
			
			ctx.move_to(x, y)
			
			em_size = parent.style['em-size']
			ctx.set_font_size(em_size)
			
			ctx.set_source_rgb(0, 0, 0)
			ctx.rel_move_to(0, em_size) # TODO: baseline
			ctx.show_text(node)
		else:
			ctx.set_line_width(1)
			if 'display' not in box.style:
				ctx.set_source_rgb(1, 1, 0)
			elif box.style['display'] == 'block':
				ctx.set_source_rgb(1, 0, 0)
			elif box.style['display'] == 'inline':
				ctx.set_source_rgb(0, 0, 1)
			else:
				ctx.set_source_rgb(0, 1, 0)
			#ctx.rectangle(x + box.style['x'], y + box.style['y'], box.style['width'], box.style['height'])
			#ctx.stroke()
			
			for child in box.content:
				ctx.save()
				self.__render_box(view, ctx, document, child, box, x + box.style['x'], y + box.style['y'])
				ctx.restore()
	
	__inherited_properties = frozenset({
		'azimuth',
		'border-collapse',
		'border-spacing',
		'caption-side',
		'color',
		'cursor',
		'direction',
		'elevation',
		'empty-cells',
		'font-family',
		'font-size',
		'font-style',
		'font-variant',
		'font-weight',
		'font',
		'letter-spacing',
		'line-height',
		'list-style-image',
		'list-style-position',
		'list-style-type',
		'list-style',
		'orphans',
		'pitch-range',
		'pitch',
		'quotes',
		'richness',
		'speak-header',
		'speak-numeral',
		'speak-punctuation',
		'speak',
		'speech-rate',
		'stress',
		'text-align',
		'text-indent',
		'text-transform',
		'visibility',
		'voice-family',
		'volume',
		'white-space',
		'widows',
		'word-spacing'
	})
	
	def __get_attribute(self, view, document, node, pseudoelement, attr, default):
		value = self.__search_attribute(view, document, node, pseudoelement, attr)
		if value is None or value == 'initial':
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
						self.__css_matcher[css] = self.create_css_matcher(css, None, self.__get_id, None, None, None, node.tag.split('}')[1:] if node.tag[0] == '}' else '')
					css_attrs = self.__css_matcher[css](node)
					if attr in css_attrs:
						view.__attr_cache[node, pseudoelement][attr] = css_attrs[attr][0]
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
			if stylesheet not in self.__css_matcher:
				self.__css_matcher[stylesheet] = self.create_css_matcher(stylesheet, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), None, self.__xmlns(document))
			css_attrs = self.__css_matcher[stylesheet](node)
			
			#if node.tag == '{http://www.w3.org/1999/xhtml}body':
			#	print("", css_attrs, stylesheet)

			#if css_attrs:
			#	print("search_attribute", node.tag, pseudoelement, attr)
			#	print("", css_attrs)
			
			#css_attrs = stylesheet.match_element(document, node, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), self.__pseudoelement_test)
			if attr in css_attrs:
				value, priority = css_attrs[attr]
				if css_priority == None or priority >= css_priority:
					css_value = value
					css_priority = priority
		
		if css_value is not None:
			view.__attr_cache[node, pseudoelement][attr] = css_value
			return css_value
		
		if attr in self.__inherited_properties:
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
		
		doc = self.get_document('chrome://html.css')
		if self.is_css_document(doc):
			yield doc
		
		for link in chain(document.scan_stylesheets(), self.__data_internal_links(self.__style_tags(document)), self.__style_links(document)):
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc


if __debug__ and __name__ == '__main__':
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	from pathlib import Path
	from urllib.parse import unquote as url_unquote
	
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
			#return cairo.Rectangle(0, 0, len(txt), 1)
			return cairo.TextExtents(0, 0, len(txt) * self.font_size, self.font_size, len(txt) * self.font_size, 0)
		
		def set_dash(self, dashes, offset):
			if self.print_out: print(f'{self.__name}.set_dash({repr(dashes)}, {repr(offset)})')
			pass
		
		def device_to_user(self, x, y):
			if self.print_out: print(f'{self.__name}.device_to_user({x}, {y})')
			return x, y
		
		def set_font_size(self, size):
			self.font_size = size
		
		def __getattr__(self, attr):
			if self.print_out: return lambda *args: print(self.__name + '.' + attr + str(args))
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
			if mime_type == 'application/xml' or mime_type == 'text/x-html-tag-soup':
				return XMLFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/css':
				return CSSFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/html' or mime_type == 'application/xhtml+xml':
				return HTMLRender.create_document(self, data, mime_type)
			else:
				raise NotImplementedError("Could not create unsupported document type.")
		
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
			elif url == 'chrome://html.css':
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
	
	class PseudoView:
		def __init__(self):
			pass
	
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
			rnd = HTMLRenderModel()
			view = PseudoView()
			
			if filepath.suffix == '.html':
				mime = 'text/html'
			else:
				mime = 'application/xhtml+xml'

			document = rnd.create_document(filepath.read_bytes(), mime)
			l = list(rnd.scan_document_links(document))
			print(l)
			
			rnd.tree = document
			rnd.draw_image(view, document, ctx, (0, 0, 1000, 800))
				
			#profiler.done()


