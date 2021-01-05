#!/usr/bin/python3
#-*- coding: utf-8 -*-


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import GLib as glib

import cairo


from enum import Enum
from math import hypot





class XMLWidget(gtk.Widget):
	def __init__(self):
		super().__init__()
		self.__document = None
		self.__prefix_proxy = {}
	
	def set_document(self, document):
		self.__document = document
	
	def get_document(self, document):
		return self.__document
	
	class PrefixProxy:
		def __init__(self, prefix, parent, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.__prefix = prefix
			self.__parent = parent
		
		def __getattr__(self, attr):
			try:
				return getattr(self.__parent, self.__prefix + '_' + attr)
			except AttributeError:
				return getattr(self.__parent, attr)
		
		def __setattr__(self, attr, value):
			if hasattr(self.__parent, self.__prefix + '_' + attr):
				setattr(self.__parent, self.__prefix + '_' + attr, value)
			else:
				setattr(self.__parent, attr, value)
		
		def __delattr__(self, attr):
			try:
				delattr(self.__parent, self.__prefix + '_' + attr)
			except AttributeError:
				pass
			
			try:
				delattr(self.__parent, attr)
			except AttributeError:
				pass
				
	class Record:
		pass
	
	def register_namespace(self, prefix, namespace):
		self.__prefix_proxy[namespace] = PrefixProxy(prefix, self)
	
	def ns(self, namespace):
		return self.__prefix_proxy[namespace]
	
	def do_draw(self, ctx):
		document = self.get_document()
		if document == None: return
		self.render_node(document.root, ctx, Record())
	
	def render_node(self, node, ctx, style):
		self.ns(node.namespace).render_node(node, ctx, style)
	
	def validate_document(self):
		return self.validate_node(document.root, Record())
	
	def validate_node(self, node, context):
		return self.ns(node.namespace).validate_node(node, context)
	
	def process_document(self):
		self.validate_node(document.root, Record())
	
	def process_node(self, node, context):
		self.ns(node.namespace).process_node(node, context)
	



class SVGWidget(XMLWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(self)
		self.register_namespace('svg', '... svg namespace ...')
	
	def svg_validate_node(self, node, context):
		return True
	
	def svg_process_node(self, node, context):
		pass
	
	def svg_render_node(self, node, ctx, style):
		"""Draw ``node`` and its children."""
		
		assert node.namespace == self.SVG_NAMESPACE:
		
		# Parse definitions first
		#if node.tag == 'svg':
		#	self.__parse_all_defs(node)
		
		# Do not draw defs
		if node.tag == 'defs':
			return
		
		# Do not draw elements with width or height of 0
		if ((node.get('width') != None and self.__size(node.get('width')) == 0) or
		    (node.get('height') != None and self.__size(node.get('height')) == 0)):
			return
		
		# Save context and related attributes
		old_parent_node = style.__parent_node
		old_font_size = style.__font_size
		old_context_size = style.__context_width, style.__context_height
		style.__parent_node = node
		style.__font_size = self.__size(node.get('font-size', '12pt'))
		ctx.save()

		# Apply transformations
		self.__transform(node.get('transform'))

		# Find and prepare opacity, masks and filters
		mask = self.__parse_url(node.get('mask')).fragment
		filter_ = self.__parse_url(node.get('filter')).fragment
		opacity = float(node.get('opacity', 1))

		if filter_:
			self.__prepare_filter(node, filter_)

		if filter_ or mask or (opacity < 1 and len(node)):
			ctx.push_group()

		# Move to (node.x, node.y)
		ctx.move_to(self.__size(node.get('x'), 'x'), self.__size(node.get('y'), 'y'))

		# Set node's drawing informations if the ``node.tag`` method exists
		line_cap = node.get('stroke-linecap')
		if line_cap == 'square':
			ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
		if line_cap == 'round':
			ctx.set_line_cap(cairo.LINE_CAP_ROUND)

		join_cap = node.get('stroke-linejoin')
		if join_cap == 'round':
			ctx.set_line_join(cairo.LINE_JOIN_ROUND)
		if join_cap == 'bevel':
			ctx.set_line_join(cairo.LINE_JOIN_BEVEL)

		dash_array = self.__normalize(node.get('stroke-dasharray', '')).split()
		if dash_array:
			dashes = [self.__size(dash) for dash in dash_array]
			if sum(dashes):
				offset = self.__size(node.get('stroke-dashoffset'))
				ctx.set_dash(dashes, offset)

		miter_limit = float(node.get('stroke-miterlimit', 4))
		ctx.set_miter_limit(miter_limit)

		# Clip
		rect_values = self.__clip_rect(node.get('clip'))
		if len(rect_values) == 4:
			top = self.__size(rect_values[0], 'y')
			right = self.__size(rect_values[1], 'x')
			bottom = self.__size(rect_values[2], 'y')
			left = self.__size(rect_values[3], 'x')
			x = self.__size(node.get('x'), 'x')
			y = self.__size(node.get('y'), 'y')
			width = self.__size(node.get('width'), 'x')
			height = self.__size(node.get('height'), 'y')
			ctx.save()
			ctx.translate(x, y)
			ctx.rectangle(left, top, width - left - right, height - top - bottom)
			ctx.restore()
			ctx.clip()
		
		clip_path = parse_url(node.get('clip-path')).fragment
		if clip_path:
			path = self.paths.get(clip_path)
			if path:
				ctx.save()
				if path.get('clipPathUnits') == 'objectBoundingBox':
					x = self.__size(node.get('x'), 'x')
					y = self.__size(node.get('y'), 'y')
					width = self.__size(node.get('width'), 'x')
					height = self.__size(node.get('height'), 'y')
					ctx.translate(x, y)
					ctx.scale(width, height)
				path.tag = 'g'
				self.stroke_and_fill = False
				self.draw(path)
				self.stroke_and_fill = True
				ctx.restore()
				# TODO: fill rules are not handled by cairo for clips
				# if node.get('clip-rule') == 'evenodd':
				#	 ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
				ctx.clip()
				ctx.set_fill_rule(cairo.FILL_RULE_WINDING)

		# Only draw known tags
		if node.tag in TAGS:
			try:
				TAGS[node.tag](self, node)
			except PointError:
				# Error in point parsing, do nothing
				pass

		# Get stroke and fill opacity
		stroke_opacity = float(node.get('stroke-opacity', 1))
		fill_opacity = float(node.get('fill-opacity', 1))
		if opacity < 1 and not node.children:
			stroke_opacity *= opacity
			fill_opacity *= opacity

		# Manage display and visibility
		display = node.get('display', 'inline') != 'none'
		visible = display and (node.get('visibility', 'visible') != 'hidden')

		# Set font rendering properties
		ctx.set_antialias(SHAPE_ANTIALIAS.get(
			node.get('shape-rendering'), cairo.ANTIALIAS_DEFAULT))

		font_options = ctx.get_font_options()
		font_options.set_antialias(TEXT_ANTIALIAS.get(
			node.get('text-rendering'), cairo.ANTIALIAS_DEFAULT))
		font_options.set_hint_style(TEXT_HINT_STYLE.get(
			node.get('text-rendering'), cairo.HINT_STYLE_DEFAULT))
		font_options.set_hint_metrics(TEXT_HINT_METRICS.get(
			node.get('text-rendering'), cairo.HINT_METRICS_DEFAULT))
		ctx.set_font_options(font_options)

		# Fill and stroke
		if self.stroke_and_fill and visible and node.tag in TAGS:
			mouse_over = False
			if self.mouse:
				ctx.save()
				ctx.identity_matrix()
				if (ctx.in_fill(*self.mouse) or ctx.in_stroke(*self.mouse)):
					self.hover_nodes.append(node.element.etree_element)
					#mouse_over = True
				ctx.restore()

			# Fill
			ctx.save()
			paint_source, paint_color = paint(node.get('fill', 'black'))
			if not gradient_or_pattern(self, node, paint_source):
				if node.get('fill-rule') == 'evenodd':
					ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
				ctx.set_source_rgba(*color(paint_color, fill_opacity))
			ctx.fill_preserve()
			ctx.restore()

			# Stroke
			ctx.save()
			ctx.set_line_width(
				self.__size(node.get('stroke-width', '1')))
			paint_source, paint_color = paint(node.get('stroke'))
			if not gradient_or_pattern(self, node, paint_source):
				ctx.set_source_rgba(
					*color(paint_color, stroke_opacity))
			ctx.stroke()
			ctx.restore()
		elif not visible:
			ctx.new_path()

		# Draw path markers
		draw_markers(self, node)

		# Draw children
		if display and node.tag not in INVISIBLE_TAGS:
			for child in node.children:
				self.render_node(child)

		# Apply filter, mask and opacity
		if filter_ or mask or (opacity < 1 and node.children):
			ctx.pop_group_to_source()
			if filter_:
				apply_filter_before_painting(self, node, filter_)
			if mask in self.masks:
				paint_mask(self, node, mask, opacity)
			else:
				ctx.paint_with_alpha(opacity)
			if filter_:
				apply_filter_after_painting(self, node, filter_)

		# Clean cursor's position after 'text' tags
		if node.tag == 'text':
			self.cursor_position = [0, 0]
			self.cursor_d_position = [0, 0]
			self.text_path_width = 0

		ctx.restore()
		self.parent_node = old_parent_node
		self.font_size = old_font_size
		ctx_width, ctx_height = old_context_size

