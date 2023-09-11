#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'XFormsFormat',


from collections import defaultdict


class XFormsFormat:
	xmlns_xforms = 'http://www.w3.org/2002/xforms'
	
	def is_xforms_document(self, document):
		try:
			return document.tag.startswith('{' + self.xmlns_xforms + '}')
		except AttributeError:
			return False
		
	def draw_image(self, view, document, ctx, box):
		"Draw a form element."
		
		if not self.is_xforms_document(document):
			return NotImplemented
		
		if document.tag == f'{{{self.xmlns_xforms}}}model':
			return
		
		for child in document:
			if not child.tag.startswith(f'{{{self.xmlns_xforms}}}'):
				try:
					self.draw_image(view, child, ctx, box)
				except NotImplementedError:
					self.emit_warning(view, f"Unsupported non-XForms element: {child.tag}", child.tag, child)
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_xforms_document(document):
			return NotImplemented
		
		hover_nodes = []
		
		if document.tag == f'{{{self.xmlns_xforms}}}model':
			return hover_nodes
		
		for child in document:
			if not child.tag.startswith(f'{{{self.xmlns_xforms}}}'):
				try:
					hover_subnodes = self.poke_image(view, child, ctx, box, px, pt)
					hover_nodes.extend(hover_subnodes)
				except NotImplementedError:
					self.emit_warning(view, f"Unsupported non-XForms element: {child.tag}", child.tag, child)
		
		qx, qy = ctx.device_to_user(px, py)
		if left <= qx <= left + width and top <= qy <= top + height and ctx.in_clip(qx, qy):
			hover_nodes.insert(0, document)
		return hover_nodes


