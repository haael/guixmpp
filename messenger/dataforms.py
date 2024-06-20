#!/usr/bin/python3


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from guixmpp import *
from builder_extension import *
from locale import gettext
from lxml.etree import fromstring, tostring
from asyncio import gather, Event


class DataForm(BuilderExtension):
	def __init__(self, parent, interface='dataforms.glade'):
		self.__interface = interface
		super().__init__(parent, ['form_main'], 'form_main')
		self.__elements = []
		self.completed = Event()
		self.proceed = False
	
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
				element = BuilderExtension(self, ['label_instructions'], 'label_instructions')
				element.label_instructions.set_text(field.text)
				
				self.box_content.pack_start(element.main_widget, False, True, 4)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and (('type' not in field.attrib) or (field.attrib['type'] == 'text-single')):
				element = BuilderExtension(self, ['form_text'], 'form_text')
				if 'label' in field.attrib:
					element.label_text.set_text(field.attrib['label'] + ":")
					element.label_text.show()
				else:
					element.label_text.hide()
				
				try:
					text = field.xpath('xep-0004:value', namespaces=XMPPClient.namespace)[0].text
					element.entry_text.set_text(text)
				except IndexError:
					pass
				
				try:
					media = field.xpath('xep-0221:media', namespaces=XMPPClient.namespace)[0]
					cid = media.xpath('xep-0221:uri', namespaces=XMPPClient.namespace)[0].text
				except IndexError:
					element.media_text.hide()
				else:
					#element.media_text.set_size_request(300, 200)
					element.media_text.show()
					#await element.media_text.open(cid)
					cids.append((element.media_text, cid))
				
				self.box_content.pack_start(element.main_widget, False, True, 4)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and field.attrib['type'] == 'fixed':
				element = BuilderExtension(self, ['form_fixed'], 'form_fixed')
				if 'label' in field.attrib:
					element.label_fixed.set_text(field.attrib['label'] + ":")
					element.label_fixed.show()
				else:
					element.label_fixed.hide()
				
				try:
					text = field.xpath('xep-0004:value', namespaces=XMPPClient.namespace)[0].text
					element.entry_fixed.set_text(text)
				except IndexError:
					pass
				
				self.box_content.pack_start(element.main_widget, False, True, 4)
				added.append(element)
			
			elif field.tag == f'{{{XMPPClient.namespace["xep-0004"]}}}field' and field.attrib['type'] == 'text-private':
				element = BuilderExtension(self, ['form_password'], 'form_password')
				if 'label' in field.attrib:
					element.label_password.set_text(field.attrib['label'] + ":")
					element.label_password.show()
				else:
					element.label_password.hide()
				
				try:
					text = field.xpath('xep-0004:value', namespaces=XMPPClient.namespace)[0].text
					element.entry_password_1.set_text(text)
					element.entry_password_2.set_text(text)
				except IndexError:
					pass
				
				self.box_content.pack_start(element.main_widget, False, True, 4)
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
		self.proceed = True
		self.completed.set()
	
	async def result(self):
		await self.completed.wait()
		return self.proceed


if __name__ == '__main__':
	from locale import bindtextdomain, textdomain
	from aiopath import Path
	from guixmpp import *
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
	
	run(main())

