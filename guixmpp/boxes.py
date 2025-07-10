#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'Gravity', 'Box', 'Whitespace', 'Word', 'EscapeSeq', 'Row', 'Column', 'inf'


from enum import Enum
from os import environ


_use_pango = environ.get('GUIXMPP_USE_PANGO', '1')


import gi
if _use_pango == '1':
	if __name__ == '__main__':
		gi.require_version('Pango', '1.0')
		gi.require_version('PangoCairo', '1.0')
	from gi.repository import Pango, PangoCairo


if __name__ == '__main__':
	from guixmpp.escape import Escape
else:
	from .escape import Escape


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
	
	def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
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
		
		def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
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
				
				child.render(model, view, ctx, pango_layout, (cx, cy, cw, ch), callback, pointer)
			
			ctx.set_line_width(5)
			ctx.set_font_size(25)
			ctx.move_to(x + 10, y + 30)
			ctx.text_path(self.label)
			ctx.set_source_rgb(1, 1, 1)
			ctx.stroke_preserve()
			ctx.set_source_rgb(0, 0, 0)
			ctx.fill()


class Whitespace(Box):
	def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
		if pointer: return []
		pass


class Word(Box):
	def __init__(self, text, dx, dy, *args, **kwargs):
		self.text = text
		self.dx = dx
		self.dy = dy
		super().__init__(*args, **kwargs)
	
	def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
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
		
		if callback: callback(Escape.begin_text, (self.text, ctx, pango_layout))
		
		if pango_layout:
			#ctx.move_to(dx, dy + baseline - pango_layout.get_baseline() / Pango.SCALE)
			#pango_layout.set_text(string)
			ctx.move_to(tx + self.dx, ty + self.dy - pango_layout.get_baseline() / Pango.SCALE)
			pango_layout.set_text(self.text)
			PangoCairo.update_context(ctx, pango_layout.get_context())
			pango_layout.context_changed()
			PangoCairo.layout_path(ctx, pango_layout)
		else:
			#ctx.move_to(dx, dy + baseline)
			#ctx.text_path(string)
			ctx.move_to(tx + self.dx, ty + self.dy)
			ctx.text_path(self.text)
		
		if callback: callback(Escape.end_text, (self.text, ctx, pango_layout))
		
		if pointer:
			nodes_under_pointer = []
			px, py = ctx.device_to_user(*pointer)
			if ctx.in_clip(px, py):
				if ctx.in_fill(px, py):
					nodes_under_pointer.append(self.node)
			ctx.new_path()
			return nodes_under_pointer
		else:
			if callback: callback(Escape.begin_print, (ctx, pango_layout))
			ctx.fill()
			if callback: callback(Escape.end_print, (ctx, pango_layout))
	
	def __str__(self):
		return self.text


class EscapeSeq(Box):
	def __init__(self, escape, *args, **kwargs):
		self.escape = escape
		super().__init__(*args, **kwargs)
	
	def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
		if callback: callback(Escape.begin_escape, (self.escape, ctx, pango_layout))		
		if callback: callback(Escape.end_escape, (self.escape, ctx, pango_layout))
	
	def __str__(self):
		return "\\" + repr(self.escape)


class Row(Box):
	def __init__(self, children, number, *args, **kwargs):
		self.children = children
		self.number = number
		
		min_width = kwargs.get('min_width', sum(_child.min_width for _child in self.children) if self.children else 0)
		grow_width = kwargs.get('grow_width', sum(_child.grow_width for _child in self.children) if self.children else 0)
		max_width = kwargs.get('max_width', sum(_child.max_width for _child in self.children) if self.children else 0)
		min_height = kwargs.get('min_height', max(_child.min_height for _child in self.children) if self.children else 0)
		grow_height = kwargs.get('grow_height', sum(_child.grow_height for _child in self.children) if self.children else 0)
		max_height = kwargs.get('max_height', min(_child.max_height for _child in self.children) if self.children else 0)
		
		for arg in ['min_width', 'grow_width', 'max_width', 'min_height', 'grow_height', 'max_height']:
			kwargs.pop(arg, None)
		
		super().__init__(*args, min_width=min_width, grow_width=grow_width, max_width=max_width, min_height=min_height, grow_height=grow_height, max_height=max_height, **kwargs)
	
	def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
		assert not any(_x == inf for _x in box)
		x, y, w, h = box
		
		if pointer:
			px, py = pointer
			if not ((x <= px < x + w) and (y <= py < y + h)):
				return []
		
		#ctx.save()
		
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
			
			if callback: callback(Escape.begin_row, self.number)

			if pointer:
				nodes_under_pointer.extend(child.render(model, view, ctx, pango_layout, (cx, cy, cw, ch), callback, pointer))
			else:
				child.render(model, view, ctx, pango_layout, (cx, cy, cw, ch), callback, pointer)
			
			if callback: callback(Escape.end_row, self.number)
			
			#print((cx, cy, cw, ch))
			ax += aw
		
		if pointer and nodes_under_pointer:
			nodes_under_pointer.append(self.node)
		
		#ctx.set_line_width(1)
		#ctx.rectangle(x, y, w, h)
		#ctx.set_source_rgb(0, 1, 1)
		#ctx.stroke()
		
		#print(allocated_space)
		
		#ctx.restore()
		
		if pointer:
			return nodes_under_pointer
	
	def print_tree(self, level=0):
		yield from super().print_tree(level)
		for child in self.children:
			yield from child.print_tree(level + 1)


class Column(Box):
	def __init__(self, children, number, *args, **kwargs):
		self.children = children
		self.number = number
		
		min_width = kwargs.get('min_width', max(_child.min_width for _child in self.children) if self.children else 0)
		grow_width = kwargs.get('grow_width', sum(_child.grow_width for _child in self.children) if self.children else 0)
		max_width = kwargs.get('max_width', min(_child.max_width for _child in self.children) if self.children else 0)
		min_height = kwargs.get('min_height', sum(_child.min_height for _child in self.children) if self.children else 0)
		grow_height = kwargs.get('grow_height', sum(_child.grow_height for _child in self.children) if self.children else 0)
		max_height = kwargs.get('max_height', sum(_child.max_height for _child in self.children) if self.children else 0)
		
		for arg in ['min_width', 'grow_width', 'max_width', 'min_height', 'grow_height', 'max_height']:
			kwargs.pop(arg, None)
		
		super().__init__(*args, min_width=min_width, grow_width=grow_width, max_width=max_width, min_height=min_height, grow_height=grow_height, max_height=max_height, **kwargs)
	
	def render(self, model, view, ctx, pango_layout, box, callback, pointer=None):
		x, y, w, h = box
		
		if pointer:
			px, py = pointer
			if not ((x <= px < x + w) and (y <= py < y + h)):
				return []
		
		#ctx.save()
		
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
			
			if callback: callback(Escape.begin_column, self.number)
			
			if pointer:
				nodes_under_pointer.extend(child.render(model, view, ctx, pango_layout, (cx, cy, cw, ch), callback, pointer))
			else:
				child.render(model, view, ctx, pango_layout, (cx, cy, cw, ch), callback, pointer)
			
			if callback: callback(Escape.end_column, self.number)
			
			ay += ah
		
		if pointer and nodes_under_pointer:
			nodes_under_pointer.append(self.node)
		
		#ctx.restore()
		
		if pointer:
			return nodes_under_pointer
	
	def print_tree(self, level=0):
		yield from super().print_tree(level)
		for child in self.children:
			yield from child.print_tree(level + 1)
