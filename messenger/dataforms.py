#!/usr/bin/python3


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from guixmpp import *
from builder_extension import *
from locale import gettext
from lxml.etree import fromstring, tostring, Element
from asyncio import gather, Event


class FormField(BuilderExtension):
	VALIDATION_ICON = 'important'
	
	def get_text(self):
		return self.main_entry.get_text()
	
	def set_text(self, text):
		self.main_entry.set_text(text)
	
	@property
	def main_entry(self):
		return None
	
	@property
	def main_label(self):
		return None
	
	def required(self):
		if self.field.xpath('xep-0004:required', namespaces=XMPPClient.namespace):
			if not self.get_text():
				self.main_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
				self.main_entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("This field is required."))
				return False
			else:
				self.main_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		return True
	
	def validate(self):
		if not self.required():
			return False
		return True
	
	def read_field(self):
		if 'label' in self.field.attrib:
			self.main_label.set_text(self.field.attrib['label'] + ":")
			self.main_label.show()
		elif self.main_label:
			self.main_label.hide()
		
		try:
			value = self.field.xpath('xep-0004:value', namespaces=XMPPClient.namespace)[0]
		except IndexError:
			self.set_text("")
		else:
			self.set_text(value.text)
	
	def write_field(self):
		try:
			value = self.field.xpath('xep-0004:value', namespaces=XMPPClient.namespace)[0]
		except IndexError:
			value = Element('value') # FIXME: assumes that default namespace is xep-0004
			self.field.append(value)
		value.text = self.get_text()
	
	def set_field(self, field):
		self.field = field
		self.read_field()
	
	def entry_icon_press(self, widget, icon_pos, event):
		widget.set_icon_from_icon_name(icon_pos, None) # hide error icon when it's clicked on


class TextField(FormField):
	@property
	def main_entry(self):
		return self.entry_text
	
	@property
	def main_label(self):
		return self.label_text


class PasswordField(FormField):
	@property
	def main_entry(self):
		return self.entry_password_1
	
	@property
	def main_label(self):
		return self.label_password
	
	def get_text(self):
		return self.entry_password_1.get_text()
	
	def set_text(self, text):
		self.entry_password_1.set_text(text)
		self.entry_password_2.set_text(text)
	
	def validate(self):
		if not self.required():
			return False
		
		if self.entry_password_1.get_text() != self.entry_password_2.get_text():
			self.entry_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_password_2.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Passwords do not match."))
			return False
		else:
			self.entry_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		return True


class FixedField(FormField):
	@property
	def main_entry(self):
		return self.entry_fixed
	
	@property
	def main_label(self):
		return self.label_fixed


class InstructionsField(FormField):
	@property
	def main_entry(self):
		return self.label_instructions


class DataForm(BuilderExtension):
	def __init__(self, parent, interface='dataforms.glade'):
		self.__interface = interface
		super().__init__(parent, ['form_main'], 'form_main')
		self.__elements = []
		self.completed = Event()
		self.proceed = False
		self.field_spacing = 4
	
	@property
	def glade_interface(self):
		return self.__interface
	
	async def stop(self):
		await self.clear_data()
		await super().stop()
	
	async def clear_data(self):
		await gather(*[_element.stop() for _element in self.__elements if hasattr(_element, 'stop')])
		for element in self.__elements:
			self.box_content.remove(element.main_widget)
		self.__elements.clear()
	
	async def add_data(self, data):
		try:
			text = data.xpath('xep-0004:title', namespaces=XMPPClient.namespace)[0].text
		except IndexError:
			self.label_title.hide()
		else:
			self.label_title.set_text(text)
			self.label_title.show()
		
		cids = []
		added = []
		
		for field in data:
			if field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}instructions':
				element = InstructionsField(self, ['label_instructions'], 'label_instructions')
				element.set_field(field)
				#element.label_instructions.set_text(field.text)
				
				self.box_content.pack_start(element.main_widget, False, True, self.field_spacing)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and (('type' not in field.attrib) or (field.attrib['type'] == 'text-single')):
				element = TextField(self, ['form_text'], 'form_text')
				element.set_field(field)
				
				try:
					media = field.xpath('xep-0221:media', namespaces=XMPPClient.namespace)[0]
					cid = media.xpath('xep-0221:uri', namespaces=XMPPClient.namespace)[0].text
				except IndexError:
					element.media_text.hide()
				else:
					element.media_text.show()
					cids.append((element.media_text, cid))
				
				self.box_content.pack_start(element.main_widget, False, True, self.field_spacing)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and field.attrib['type'] == 'fixed':
				element = FixedField(self, ['form_fixed'], 'form_fixed')
				element.set_field(field)
				
				self.box_content.pack_start(element.main_widget, False, True, self.field_spacing)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and field.attrib['type'] == 'text-private':
				element = PasswordField(self, ['form_password'], 'form_password')
				element.set_field(field)
				
				self.box_content.pack_start(element.main_widget, False, True, self.field_spacing)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and field.attrib['type'] == 'hidden':
				pass
			
			else:
				print("Unsupported data field:", tostring(field).decode('utf-8'))
		
		await gather(*[_element.start() for _element in self.__elements if hasattr(_element, 'start')])
		self.__elements.extend(added)
		
		await gather(*[_domwidget.open(_cid) for (_domwidget, _cid) in cids])
		
		return self.main_widget
	
	def dataform_cancel(self, widget):
		self.proceed = False
		self.completed.set()
	
	def dataform_submit(self, widget):
		ok = True
		for element in self.__elements:
			v = element.validate()
			if not v and ok:
				element.main_entry.grab_focus() # TODO: focus the widget with error
			ok &= v
		
		if not ok:
			return
		
		for element in self.__elements:
			element.write_field()
		
		self.proceed = True
		self.completed.set()
	
	async def result(self):
		await self.completed.wait()
		return self.proceed


if __name__ == '__main__':
	from locale import bindtextdomain, textdomain
	from aiopath import Path
	from asyncio import run, get_running_loop
	from base64 import b64decode
	from guixmpp.domevents import Event as DOMEvent
	
	loop_init()
	
	translation = 'haael_svg_messenger'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		
		client = XMPPClient('haael@dw.live/discovery')
		
		iq = fromstring(await Path('registration-form.xml').read_bytes())
		form = iq.xpath('xep-0077:query/xep-0004:x', namespaces=XMPPClient.namespace)[0]
		media = iq.xpath('xep-0077:query/xep-0231:data', namespaces=XMPPClient.namespace)
		for medium in media:
			#print(medium.attrib['cid'], medium.attrib['type'], b64decode(medium.text))
			client.set_resource(medium.attrib['cid'], b64decode(medium.text), medium.attrib['type'])
		
		window = Gtk.Window()
		
		class Parent:
			gettext_translation = translation
			
			chrome_dir = Path('assets')
			
			async def create_resource(self, url):
				pass
			
			@asynchandler
			async def dom_event(self, widget, event, target):
				if event.type_ == 'open':
					image = target.model.current_document(target)
					w, h = target.model.image_dimensions(widget, image)
					widget.set_size_request(w, h)
					#target.set_image(image)
				print(event)
			
			def xmpp_client(self, domwidget):
				return client
		
		dataform = DataForm(Parent())
		await dataform.start()
		await dataform.add_data(form)
		window.add(dataform.main_widget)
		window.connect('destroy', lambda _: loop_quit())
		window.show_all()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		await dataform.stop()
		print(tostring(form).decode('utf-8'))
	
	run(main())
	

