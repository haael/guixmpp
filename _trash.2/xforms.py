#!/usr/bin/python3
#-*- coding:utf-8 -*-



__all__ = 'XForms',


from enum import Enum

from weakref import WeakKeyDictionary
from math import pi


class XForms:
	xmlns_xforms = 'http://www.w3.org/2002/xforms'
	
	def __init__(self):
		self.__document = None
		self.__model = None
		self.__state = WeakKeyDictionary()
	
	def clear(self):
		self.__document = None
		self.__model = None
		self.__state = WeakKeyDictionary()
	
	def scan_link(self, base_url, node):
		pass
	
	def transform_document(self, url, doc):
		return doc
	
	def xforms_event(self, handler, event):
		try:
			pseudo_selectors = self.__state[event.target]
		except KeyError:
			pseudo_selectors = self.__state[event.target] = set()
		
		if event.type_ == 'mouseenter':
			pseudo_selectors.add('hover')
			self.update()
		elif event.type_ == 'mouseleave':
			pseudo_selectors.discard('hover')
			pseudo_selectors.discard('active')
			self.update()
		elif event.type_ == 'mousedown' or (event.type_ == 'keydown' and event.code == 'space'):
			pseudo_selectors.add('active')
			self.update()
		elif event.type_ == 'mouseup' or (event.type_ == 'keyup' and event.code == 'space'):
			pseudo_selectors.discard('active')
			if event.type_ == 'keyup' and event.code == 'space':
				#print("click", event.target.tag)
				if 'checked' in pseudo_selectors:
					pseudo_selectors.discard('checked')
				else:
					pseudo_selectors.add('checked')
			self.update()
		elif event.type_ == 'focus':
			pseudo_selectors.add('focus')
			self.update()
		elif event.type_ == 'blur':
			pseudo_selectors.discard('focus')
			self.update()
		elif event.type_ == 'click':
			#print("click", event.target.tag)
			if 'checked' in pseudo_selectors:
				pseudo_selectors.discard('checked')
			else:
				pseudo_selectors.add('checked')
			self.update()
		#else:
		#	print(repr(event.type_), event.target.tag, repr(event.code))
	
	Appearance = Enum('XForms.Appearance', 'FULL HORIZONTAL VERTICAL MINIMAL')
	
	def render_xml(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		print("render_xml", node.tag)
		
		if node.tag == f'{{{self.xmlns_xforms}}}model' or node.tag == f'{{{self.xmlns_xforms}}}value': # invisible items
			return []
		
		nodes_under_pointer = []
		x, y, w, h = box
		if pointer:
			px, py = pointer
			if x <= px < x + w and y <= py < y + h:
				nodes_under_pointer.append(node)
		
		appearance = node.get(f'{{{self.xmlns_xforms}}}appearance', node.get('appearance', 'default'))
		if appearance not in ('full', 'compact', 'minimal', 'horizontal', 'vertical', 'default'):
			appearance = 'default'
		
		if node.tag == f'{{{self.xmlns_xforms}}}switch':
			label_box = self.draw_xforms_switch(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}group':
			if appearance == 'horizontal':
				label_box = self.draw_xforms_group(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_group_vertical(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}repeat':
			if appearance == 'horizontal':
				label_box = self.draw_xforms_repeat_horizontal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_repeat_vertical(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}textarea':
			if appearance == 'full':
				label_box = self.draw_xforms_textarea_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact':
				label_box = self.draw_xforms_textarea_compact(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_textarea_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_textarea_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}range':
			if appearance == 'full':
				label_box = self.draw_xforms_range_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact' or appearance == 'horizontal':
				label_box = self.draw_xforms_range_horizontal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'vertical':
				label_box = self.draw_xforms_range_vertical(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_range_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_range_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}select':
			if appearance == 'full':
				label_box = self.draw_xforms_select_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact':
				label_box = self.draw_xforms_select_compact(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_select_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_select_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}select1':
			if appearance == 'full':
				label_box = self.draw_xforms_select1_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact':
				label_box = self.draw_xforms_select1_compact(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_select1_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_select1_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}input':
			if appearance == 'full':
				label_box = self.draw_xforms_input_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact' or appearance == 'horizontal':
				label_box = self.draw_xforms_input_horizontal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'vertical':
				label_box = self.draw_xforms_input_vertical(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_input_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_input_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}output':
			if appearance == 'full':
				label_box = self.draw_xforms_output_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact' or appearance == 'horizontal':
				label_box = self.draw_xforms_output_horizontal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'vertical':
				label_box = self.draw_xforms_output_vertical(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_output_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_output_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}submit':
			if appearance == 'full':
				label_box = self.draw_xforms_submit_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact':
				label_box = self.draw_xforms_submit_compact(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_submit_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_submit_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		elif node.tag == f'{{{self.xmlns_xforms}}}trigger':
			if appearance == 'full':
				label_box = self.draw_xforms_trigger_full(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'compact':
				label_box = self.draw_xforms_trigger_compact(ctx, box, node, ancestors, current_url, level, draw, pointer)
			elif appearance == 'minimal':
				label_box = self.draw_xforms_trigger_minimal(ctx, box, node, ancestors, current_url, level, draw, pointer)
			else:
				label_box = self.draw_xforms_trigger_full(ctx, box, node, ancestors, current_url, level, draw, pointer)		
		
		else:
			self.error(f"Unsupported XForms tag: {node.tag}")
			return []
		
		if label_box == None:
			label_box = self.draw_xforms_nonimplemented(ctx, box, node, ancestors, current_url, level, draw, pointer)
		
		for child in node:
			if child.tag != f'{{{self.xmlns_xforms}}}label': continue
			nodes_under_pointer += self.render_xforms_label(ctx, label_box, child, ancestors + [node], current_url, level, draw, pointer)
			break
		
		return nodes_under_pointer
	
	def draw_xforms_nonimplemented(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		if draw:
			x, y, w, h = box
			ctx.rectangle(x, y, w, h)
			ctx.set_source_rgb(1, 0.5, 0.5)
			ctx.fill()
			
			ctx.set_source_rgb(1, 1, 1)
			sq_size = 6.5
			for m in range(int(w / sq_size) + 1):
				for n in range(int(h / sq_size) + 1):
					if (m + n) % 2: continue
					ctx.rectangle(x + m * sq_size, y + n * sq_size, sq_size, sq_size)
					ctx.fill()
			
			ctx.rectangle(x, y, w, h)
			ctx.set_source_rgb(1, 0, 0)
			ctx.set_line_width(0.8)
			ctx.stroke()
		
		return box
	
	def render_xforms_label(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		nodes_under_pointer = []
		x, y, w, h = box
		
		if pointer:
			px, py = pointer
			if x <= px < x + w and y <= py < y + h:
				nodes_under_pointer.append(node)
		
		try:
			child = node[0]
		except IndexError:
			if draw:
				self.render_text(ctx, box, node.text)
		else:
			ctx.save()
			nodes_under_pointer += self.render_xml(ctx, box, child, ancestors + [node], current_url, level, draw, pointer)
			ctx.restore()
		
		return nodes_under_pointer
	
	def draw_xforms_input_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		if draw:
			ctx.rectangle(x, y, w, h)
			ctx.set_source_rgb(1, 0.5, 0.5)
			ctx.fill()
			
			ctx.set_source_rgb(1, 1, 1)
			sq_size = 6.5
			for m in range(int(w / sq_size) + 1):
				for n in range(int(h / sq_size) + 1):
					if (m + n) % 2: continue
					ctx.rectangle(x + m * sq_size, y + n * sq_size, sq_size, sq_size)
					ctx.fill()
			
			ctx.rectangle(x, y, w, h)
			ctx.set_source_rgb(1, 0, 0)
			ctx.set_line_width(0.8)
			ctx.stroke()
			
			ctx.set_font_size(8)
			te = ctx.text_extents("input")
			ctx.move_to(x + w / 2 - te.width / 2, y + h / 2 + te.height / 2)
			ctx.text_path("input")
			ctx.set_source_rgb(0.8, 0.8, 0)
			ctx.fill()
		
		return (x + 4, y, w, 12)
	
	def draw_xforms_input_horizontal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_input_vertical(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_input_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_select1_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_select1_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass	
	
	def draw_xforms_select1_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_select_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_select_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_select_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_range_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_range_compact_horizontal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_range_compact_vertical(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_range_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_input_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_input_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_input_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_output_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_output_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_output_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_secret_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_secret_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_secret_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_textarea_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_textarea_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_textarea_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_upload_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_upload_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_upload_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_trigger_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_trigger_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_trigger_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_submit_full(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		if draw:
			ctx.rectangle(*box)
			ctx.set_source_rgb(1, 1, 1)
			ctx.fill_preserve()
			ctx.set_source_rgb(0, 0, 0)
			ctx.set_line_width(1)
			ctx.stroke()
		return box
	
	def draw_xforms_submit_compact(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_submit_minimal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_group(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_case(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_switch(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	
	def draw_xforms_repeat_horizontal(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	
	def draw_xforms_repeat_vertical(self, ctx, box, node, ancestors, current_url, level, draw, pointer):
		pass
	

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
	
	class ExtXForms(XMLModel, XForms):
		def __init__(self):
			XMLModel.__init__(self)
			XForms.__init__(self)
		
		def update(self):
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			rnd.render(ctx, (0, 0, 1024, 768))
		
		def scan_link(self, base_url, node):
			XForms.scan_link(self, base_url, node)
			XMLModel.scan_link(self, base_url, node)
		
		def render_xml(self, ctx, box, node, ancestors, url, level, draw, pointer):
			if node.tag.startswith(f'{{{self.xmlns_xforms}}}'):
				return XForms.render_xml(self, ctx, box, node, ancestors, url, level, draw, pointer)
			else:
				ancestors = ancestors + [node]
				nodes_under_pointer = []
				for child in node:
					nodes_under_pointer += self.render_xml(ctx, box, child, ancestors, url, level, draw, pointer)
				return nodes_under_pointer
		
		def transform_document(self, url, doc):
			doc = XMLModel.transform_document(self, url, doc)
			doc = XForms.transform_document(self, url, doc)
			return doc
	
	for filepath in Path('html').iterdir():
		if filepath.suffix != '.xml': continue
		print()
		print(filepath)
		rnd = ExtXForms()
		rnd.open(str(filepath))



