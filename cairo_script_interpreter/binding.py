#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ImageModel',


from io import BytesIO
import ctypes
import cairo


FUNCTYPE = ctypes.CFUNCTYPE


csi_surface_create_func_t = FUNCTYPE(ctypes.c_void_p, ctypes.py_object, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_long)
csi_context_create_func_t = FUNCTYPE(ctypes.c_void_p, ctypes.py_object, ctypes.c_void_p)
csi_create_source_image_t = FUNCTYPE(ctypes.c_void_p, ctypes.py_object, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long)
csi_destroy_func_t = FUNCTYPE(None, ctypes.py_object, ctypes.c_void_p)
csi_show_page_func_t = FUNCTYPE(None, ctypes.py_object, ctypes.c_void_p)
csi_copy_page_func_t = FUNCTYPE(None, ctypes.py_object, ctypes.c_void_p)


class cairo_script_interpreter_hooks_t(ctypes.Structure):
	_fields_ = [
		('closure', ctypes.py_object),
		('surface_create', csi_surface_create_func_t),
		('surface_destroy', csi_destroy_func_t),
		('context_create', csi_context_create_func_t),
		('context_destroy', csi_destroy_func_t),
		('show_page', csi_show_page_func_t),
		('copy_page', csi_copy_page_func_t),
		('create_source_image', csi_create_source_image_t)
	]


class Symbols:
	def __init__(self, libcsi=None, libcairo=None, libhelper=None):
		if libcsi == None:
			self.libcsi = ctypes.cdll.LoadLibrary('libcairo-script-interpreter.so')
		else:
			self.libcsi = libcsi
		
		if libcairo == None:
			self.libcairo = ctypes.cdll.LoadLibrary('libcairo.so')
		else:
			self.libcairo = libcairo
		
		if libhelper == None:
			self.libhelper = ctypes.cdll.LoadLibrary('./cairo_script_interpreter/csi_helper.so')
		else:
			self.libphelper = libhelper
		
		self.cairo_script_interpreter_create = self.libcsi.cairo_script_interpreter_create
		self.cairo_script_interpreter_create.argtypes = []
		self.cairo_script_interpreter_create.restype = ctypes.c_void_p
		
		self.cairo_script_interpreter_install_hooks = self.libcsi.cairo_script_interpreter_install_hooks
		self.cairo_script_interpreter_install_hooks.argtypes = [ctypes.c_void_p, ctypes.POINTER(cairo_script_interpreter_hooks_t)]
		self.cairo_script_interpreter_install_hooks.restype = None
		
		self.cairo_script_interpreter_feed_string = self.libcsi.cairo_script_interpreter_feed_string
		self.cairo_script_interpreter_feed_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
		self.cairo_script_interpreter_feed_string.restype = ctypes.c_int
		
		self.cairo_script_interpreter_finish = self.libcsi.cairo_script_interpreter_finish
		self.cairo_script_interpreter_finish.argtypes = [ctypes.c_void_p]
		self.cairo_script_interpreter_finish.restype = ctypes.c_int
		
		self.cairo_script_interpreter_destroy = self.libcsi.cairo_script_interpreter_destroy
		self.cairo_script_interpreter_destroy.argtypes = [ctypes.c_void_p]
		self.cairo_script_interpreter_destroy.restype = ctypes.c_int
		
		self.get_context_ptr = self.libhelper.get_context_ptr
		self.get_context_ptr.argtypes = [ctypes.py_object]
		self.get_context_ptr.restype = ctypes.c_void_p
		
		self.get_surface_ptr = self.libhelper.get_surface_ptr
		self.get_surface_ptr.argtypes = [ctypes.py_object]
		self.get_surface_ptr.restype = ctypes.c_void_p
		
		self.cairo_reference = self.libcairo.cairo_reference
		self.cairo_reference.argtypes = [ctypes.c_void_p]
		self.cairo_reference.restype = ctypes.c_void_p
		
		self.cairo_surface_reference = self.libcairo.cairo_surface_reference
		self.cairo_surface_reference.argtypes = [ctypes.c_void_p]
		self.cairo_surface_reference.restype = ctypes.c_void_p
		
		self.cairo_get_reference_count = self.libcairo.cairo_get_reference_count
		self.cairo_get_reference_count.argtypes = [ctypes.c_void_p]
		self.cairo_get_reference_count.restype = ctypes.c_int
		
		self.cairo_surface_get_reference_count = self.libcairo.cairo_surface_get_reference_count
		self.cairo_surface_get_reference_count.argtypes = [ctypes.c_void_p]
		self.cairo_surface_get_reference_count.restype = ctypes.c_int


class ScriptInterpreter:
	symbols = None
	
	def __init__(self, ctx=None):
		if ctx == None:
			self.ctx = self.symbols.cairo_script_interpreter_create()
		else:
			self.ctx = ctx
	
	def __del__(self):
		if self.ctx != None:
			self.destroy()
	
	def install_hooks(self, hooks):
		@csi_surface_create_func_t
		def surface_create(closure:HooksClosure, content_enum:int, width:float, height:float, uid:int) -> ctypes.c_void_p:
			surface = hooks.surface_create(cairo.Content(content_enum), width, height, uid)
			surface_addr = self.symbols.get_surface_ptr(surface)
			#self.symbols.cairo_surface_reference(surface_addr)
			print("created surface:", surface_addr, self.symbols.cairo_surface_get_reference_count(surface_addr))
			print({_addr:ScriptInterpreter.symbols.cairo_surface_get_reference_count(_addr) for _addr in closure.surfaces.keys()}, {_addr:ScriptInterpreter.symbols.cairo_get_reference_count(_addr) for _addr in closure.contexts.keys()})
			closure.surfaces[surface_addr] = surface, set()
			return surface_addr
		
		@csi_destroy_func_t
		def surface_destroy(closure:HooksClosure, surface_addr:int) -> None:
			print("destroying surface:", surface_addr, self.symbols.cairo_surface_get_reference_count(surface_addr))
			print({_addr:ScriptInterpreter.symbols.cairo_surface_get_reference_count(_addr) for _addr in closure.surfaces.keys()}, {_addr:ScriptInterpreter.symbols.cairo_get_reference_count(_addr) for _addr in closure.contexts.keys()})

			hooks.surface_destroy(closure.surfaces[surface_addr][0])
			#for context_addr in closure.surfaces[surface_addr][1]:
			#	self.symbols.cairo_reference(context_addr)
			#self.symbols.cairo_surface_reference(surface_addr)
			del closure.surfaces[surface_addr]
		
		@csi_context_create_func_t
		def context_create(closure:HooksClosure, surface_addr:int) -> ctypes.c_void_p:
			context = hooks.context_create(closure.surfaces[surface_addr][0])
			context_addr = self.symbols.get_context_ptr(context)
			#self.symbols.cairo_reference(context_addr)
			print("created context:", context_addr, self.symbols.cairo_get_reference_count(context_addr))
			print({_addr:ScriptInterpreter.symbols.cairo_surface_get_reference_count(_addr) for _addr in closure.surfaces.keys()}, {_addr:ScriptInterpreter.symbols.cairo_get_reference_count(_addr) for _addr in closure.contexts.keys()})
			#self.symbols.cairo_surface_reference(surface_addr)
			closure.surfaces[surface_addr][1].add(context_addr)
			closure.contexts[context_addr] = context
			return context_addr
		
		@csi_destroy_func_t
		def context_destroy(closure:HooksClosure, context_addr:int) -> None:
			print("destroying context:", context_addr, self.symbols.cairo_get_reference_count(context_addr))
			print({_addr:ScriptInterpreter.symbols.cairo_surface_get_reference_count(_addr) for _addr in closure.surfaces.keys()}, {_addr:ScriptInterpreter.symbols.cairo_get_reference_count(_addr) for _addr in closure.contexts.keys()})
			hooks.context_destroy(closure.contexts[context_addr])
			#self.symbols.cairo_reference(context_addr)
			del closure.contexts[context_addr]
		
		@csi_show_page_func_t
		def show_page(closure:HooksClosure, context_addr:int) -> None:
			closure.contexts[context_addr].show_page()
		
		@csi_copy_page_func_t
		def copy_page(closure:HooksClosure, context_addr:int) -> None:
			closure.contexts[context_addr].copy_page()
		
		@csi_create_source_image_t
		def create_source_image(closure:HooksClosure, format_enum:int, width:int, height:int, uid:int) -> ctypes.c_void_p:
			surface = hooks.create_source_image(cairo.Format(format_enum), width, height, uid)
			surface_addr = self.symbols.get_surface_ptr(surface)
			#self.symbols.cairo_surface_reference(surface_addr)
			closure.surfaces[surface_addr] = surface, set()
			return surface_addr
		
		self.hooks_closure = HooksClosure(surface_create, surface_destroy, context_create, context_destroy, show_page, copy_page, create_source_image)
		
		c_hooks = cairo_script_interpreter_hooks_t(ctypes.py_object(self.hooks_closure), surface_create, surface_destroy, context_create, context_destroy, show_page, copy_page, create_source_image)
		#c_hooks = cairo_script_interpreter_hooks_t(ctypes.py_object(self.hooks_closure), surface_create, surface_destroy)
		
		self.symbols.cairo_script_interpreter_install_hooks(self.ctx, ctypes.pointer(c_hooks))
	
	def run(self, filename:str):
		return cairo.Status(self.symbols.cairo_script_interpreter_run(self.ctx, filename.encode('utf-8'))) # filesystem path encoding
	
	#def feed_stream(self, fileobj)
	#	try:
	#		fileobj.flush()
	#		stream = self.libcssi.as_file_descriptor(fileobj)
	#		return cairo.Status(self.symbols.cairo_script_interpreter_feed_stream(self.ctx, stream)
	#	finally:
	#		self.libcssi.close_file(stream)
	
	def feed_string(self, line:bytes, len_:int):
		return cairo.Status(self.symbols.cairo_script_interpreter_feed_string(self.ctx, line, len_))
	
	def get_line_number(self):
		return cairo.Status(self.symbols.cairo_script_interpreter_get_line_number(self.ctx))
	
	def reference(self):
		return self.__class__(self.symbols.cairo_script_interpreter_reference(self.ctx))
	
	def finish(self):
		return cairo.Status(self.symbols.cairo_script_interpreter_finish(self.ctx))
	
	def destroy(self):
		result = cairo.Status(self.symbols.cairo_script_interpreter_destroy(self.ctx))
		self.ctx = None
		return result
	
	#def translate_stream(self, fileobj, write_func, closure):
	#	return cairo.Status(self.symbols.cairo_script_interpreter_translate_stream(c_stream, write_func_t(write_func), closure))


class HooksClosure:
	def __init__(self, *functions):
		self.functions = functions
		self.surfaces = {}
		self.contexts = {}


class ScriptInterpreterHooks:
	def __init__(self):
		print("__init__")
	
	def surface_create(self, content:cairo.Content, width:float, height:float, uid:int) -> cairo.Surface:
		print("surface_create", repr(content), width, height, uid)
		#surface =  cairo.RecordingSurface(content, (0, 0, width, height))
		surface = cairo.SVGSurface('result.svg', width, height)
		self.surface = surface
		return surface
	
	def surface_destroy(self, surface:cairo.Surface) -> None:
		print("surface_destroy", surface)
		surface.finish()
	
	def context_create(self, surface:cairo.Surface) -> cairo.Context:
		print("context_create", surface)
		return cairo.Context(surface)
	
	def context_destroy(self, context:cairo.Context) -> None:
		print("context_destroy", context)
	
	def show_page(self, context:cairo.Context) -> None:
		print("show_page", context)
		context.show_page()
	
	def copy_page(self, context:cairo.Context) -> None:
		print("copy_page", context)
		context.copy_page()
	
	def create_source_image(self, format_:cairo.Format, width:int, height:int, uid:int) -> cairo.ImageSurface:
		print("create_source_image", repr(format_), width, height, uid)
		return cairo.ImageSurface(format_, width, height)




def main():
	ScriptInterpreter.symbols = Symbols()
	
	test_script = b'''%!CairoScript
<< /content //COLOR_ALPHA /width 400 /height 300 >> surface context
1 1 0 rgb set-source
paint
/target get (out.png) write-to-png pop
pop
'''
	
	interp = ScriptInterpreter()
	hooks = ScriptInterpreterHooks()
	interp.install_hooks(hooks)
	for n, line in enumerate(test_script.split(b'\n')):
		print(n, {_addr:interp.symbols.cairo_surface_get_reference_count(_addr) for _addr in interp.hooks_closure.surfaces.keys()}, {_addr:interp.symbols.cairo_get_reference_count(_addr) for _addr in interp.hooks_closure.contexts.keys()})
		interp.feed_string(line, len(line))
	
	print({_addr:interp.symbols.cairo_surface_get_reference_count(_addr) for _addr in interp.hooks_closure.surfaces.keys()}, {_addr:interp.symbols.cairo_get_reference_count(_addr) for _addr in interp.hooks_closure.contexts.keys()})
	interp.finish()
	print({_addr:interp.symbols.cairo_surface_get_reference_count(_addr) for _addr in interp.hooks_closure.surfaces.keys()}, {_addr:interp.symbols.cairo_get_reference_count(_addr) for _addr in interp.hooks_closure.contexts.keys()})
	interp.destroy()
	print({_addr:interp.symbols.cairo_surface_get_reference_count(_addr) for _addr in interp.hooks_closure.surfaces.keys()}, {_addr:interp.symbols.cairo_get_reference_count(_addr) for _addr in interp.hooks_closure.contexts.keys()})
	
	print(hooks.surface)


if __name__ == '__main__':
	main()

'''
quit()


class ImageModel:
	def create_document(self, data, mime):
		if mime == 'image/x-argb32':
			w = int.from_bytes(data[0:4], byteorder='little', signed=False)
			h = int.from_bytes(data[4:8], byteorder='little', signed=False)
			assert len(data) == 4 * w * h + 8
			m = memoryview(bytearray(data))[8 : 4 * w * h + 8]
			return cairo.ImageSurface.create_for_data(m, cairo.Format.ARGB32, w, h)
		else:
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_raster_image_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(document.get_width().to_bytes(length=4, byteorder='little', signed=False))
			fileobj.write(document.get_height().to_bytes(length=4, byteorder='little', signed=False))
			fileobj.write(document.get_data())
			return fileobj
		elif self.is_vector_image_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			device = cairo.ScriptDevice(fileobj)
			device.from_recording_surface(document)
			device.finish()
			return fileobj
		else:
			return NotImplemented
	
	def is_raster_image_document(self, document):
		return isinstance(document, cairo.ImageSurface)
	
	def is_vector_image_document(self, document):
		return isinstance(document, cairo.RecordingSurface)

'''
