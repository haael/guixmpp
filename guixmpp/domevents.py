#!/usr/bin/python3
#-*- coding: utf-8 -*-


from collections import defaultdict
from enum import Enum
from inspect import isawaitable


class AccessError(AttributeError):
	pass


class EventTarget:
	default_handler = {}
	
	def __init__(self):
		self.__listeners = defaultdict(lambda: defaultdict(list))
	
	def addEventListener(self, type_, listener, capture=False, passive=False, once=False, signal=None):
		if not hasattr(listener, 'handleEvent') or not hasattr(listener, 'target'):
			listener = EventListener(listener)
		
		if listener.target is not None:
			raise ValueError("Listener already bound")
		
		listener.capture = capture
		listener.type_ = type_
		listener.target = self
		
		self.__listeners[type_][capture].append((listener, passive, once, signal))
		
		return listener
	
	def removeEventListener(self, type_, listener, capture=False):
		if not hasattr(listener, 'handleEvent') or not hasattr(listener, 'target'):
			listener = EventListener(listener)
			listener.capture = capture
			listener.type_ = type_
			listener.target = self
		
		if listener.type_ != type_ or listener.capture != capture:
			raise ValueError
		
		for olistener, passive, once, signal in list(reversed(self.__listeners[type_][capture])):
			if listener.callback is olistener.callback:
				self.__listeners[type_][capture].remove((olistener, passive, once, signal))
				olistener.removed = True
				break
	
	async def dispatchEvent(self, event):
		if not event._initialized:
			raise InvalidStateError("Event not initialized.")
		
		if event._dispatch:
			raise InvalidStateError("Event already dispatched.")
		
		event._dispatch = True
		
		node = self.get_event_parent()
		ancestors = []
		while node is not None:
			ancestors.append(node)
			node = node.get_event_parent()
		
		event._target = self
		event._composedPath = list(ancestors)
		cont = True
		results = []
		
		event._eventPhase = Event.CAPTURING_PHASE
		for ancestor in reversed(ancestors):
			cont &= await ancestor.__run_listeners(event)
			if not cont:
				break
		
		if cont:
			event._eventPhase = Event.AT_TARGET
			cont = await self.__run_listeners(event)
			
			if cont:
				event._eventPhase = Event.BUBBLING_PHASE
				for ancestor in ancestors:
					cont &= await ancestor.__run_listeners(event)
					if not cont:
						break
		
		event._currentTarget = None
		event._eventPhase = Event.NONE
		
		if not event._defaultPrevented and event.type_ in self.default_handler:
			await self.default_handler[event.type_].handleEvent(event)
		
		event._dispatch = False
		
		return not event.defaultPrevented
	
	def __iter_listeners(self, type_):
		for capture, listeners in self.__listeners[type_].items():
			for listener, passive, once, signal in list(listeners):
				if not listener.removed:
					yield listener, capture, passive, once, signal
	
	async def __run_listeners(self, event):
		type_ = event.type_
		cont = True
		event._currentTarget = self
		
		for listener, capture, passive, once, signal in self.__iter_listeners(type_):
			match event._eventPhase:
				case Event.NONE:
					raise RuntimeError("Event phase is NONE")
				case Event.CAPTURING_PHASE:
					if capture:
						await listener.handleEvent(event)
				case Event.AT_TARGET:
					await listener.handleEvent(event)
				case Event.BUBBLING_PHASE:
					if event.bubbles and not capture:
						await listener.handleEvent(event)
				case _:
					raise RuntimeError("Expected eventPhase = 0, 1, 2 or 3")
			
			if once:
				self.removeEventListener(type_, listener, capture)
			if event._stopImmediatePropagation:
				return False
			if event._stopPropagation:
				cont = False
		
		return cont
	
	def get_event_parent(self):
		raise NotImplementedError


class EventListener:
	def __init__(self, callback):
		self.callback = callback
		self.target = None
		self.type_ = None
		self.capture = None
		self.removed = False
	
	async def handleEvent(self, event):
		result = self.callback(event)
		if isawaitable(result):
			await result
	
	def remove(self):
		self.target.removeEventListener(self.type_, self, self.capture)


class Event:
	NONE = 0
	CAPTURING_PHASE = 1
	AT_TARGET = 2
	BUBBLING_PHASE = 3
	
	@staticmethod
	def _time():
		raise NotImplementedError("Provide time source by overriding `Event._time = time.time` or `Event._time = asyncio.get_running_loop().time`")
	
	def __init__(self, type_, composed=False, cancelable=False, bubbles=False):
		self.timeStamp = self._time()
		self.type_ = type_
		
		self.composed = composed
		self.cancelable = cancelable
		self.bubbles = bubbles
		
		self._eventPhase = self.NONE
		self._defaultPrevented = False
		
		self._target = None
		self._currentTarget = None
		
		self._inPassiveListener = False
		self._composed = False
		self._dispatch = False
		self._stopPropagation = False
		self._stopImmediatePropagation = False
		self._initialized = True
	
	def __setattr__(self, name, value):
		if hasattr(self, '_initialized') and self._initialized == True and (not name.startswith('_') or name == '_initialized'):
			raise AccessError(f"Can not modify readonly attribute: {name}.")
		super().__setattr__(name, value)
	
	def __delattr__(self, name):
		if hasattr(self, '_initialized') and self._initialized == True and (not name.startswith('_') or name == '_initialized'):
			raise AccessError(f"Can not delete readonly attribute: {name}.")
		super().__setattr__(name)
	
	def __repr__(self):
		return type(self).__name__ + '(\'' + self.type_ + '\', ' + ', '.join(_k + '=' + repr(_v) for (_k, _v) in self.__dict__.items() if not _k.startswith('_') and _k != 'type_') + ')'
	
	def stopPropagation(self):
		"""
		When dispatched in a tree, invoking this method prevents event from reaching any
		objects other than the current object.
		"""
		self._stopPropagation = True
	
	def stopImmediatePropagation(self):
		"""
		Invoking this method prevents event from reaching any registered event listeners after
		the current one finishes running and, when dispatched in a tree, also prevents
		event from reaching any other objects.
		"""
		self._stopImmediatePropagation = True
		self._stopPropagation = True
	
	def preventDefault(self):
		if self.cancelable:
			self._defaultPrevented = True
	
	@property
	def defaultPrevented(self):
		return self._defaultPrevented
	
	def composedPath(self):
		"""
		Returns the item objects of event’s path (objects on which listeners will be invoked),
		except for any nodes in shadow trees of which the shadow root’s mode is "closed" that
		are not reachable from event’s currentTarget.
		"""
		return self._composedPath
	
	@property
	def eventPhase(self):
		return self._eventPhase
	
	@property
	def target(self):
		return self._target
	
	@property
	def currentTarget(self):
		return self._currentTarget


class CustomEvent(Event):
	DEFAULTS = {
		'download': { 'cancelable':True },
		'dataload': { 'cancelable':False },
		'beforeload': { 'cancelable':True },
		'beforeunload': { 'cancelable':True },
		'open': { 'cancelable':True },
		'close': { 'cancelable':False },
		'opening': { 'cancelable':True },
		'closing': { 'cancelable':True },
		'warning': { 'cancelable':False },
		'cancelled': { 'cancelable':False },
		'parseerror': { 'cancelable':False }
	}
	
	def __init__(self, type_, detail=None, **kwargs):
		self.detail = detail
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


#Extending to MouseEvent, InputEvent, KeyboardEvent, CompositionEvent, FocusEvent
class UIEvent(Event):
	DEFAULTS = {
		'load': {},
		'unload': {},
		'abort': {},
		'error': {},
		'select': {}
	}
	
	def __init__(self, type_, view=None, detail=None, **kwargs):
		self.view = view
		self.detail = detail
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


#Extending to WheelEvent, PointerEvent
class MouseEvent(UIEvent):
	DEFAULTS = {
		'click': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'auxclick': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'dblclick': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'mousedown': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'mouseenter': { 'composed':True },
		'mouseleave': { 'composed':True },
		'mousemove': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'mouseout': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'mouseover': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'mouseup': { 'bubbles':True, 'composed':True, 'cancelable':True }
	}
	
	def __init__(self, type_, **kwargs):
		self.screenX = kwargs.pop('screenX', 0)
		self.screenY = kwargs.pop('screenY', 0)
		self.clientX = kwargs.pop('clientX', 0)
		self.clientY = kwargs.pop('clientY', 0)

		self.ctrlKey = kwargs.pop('ctrlKey', False)
		self.shiftKey = kwargs.pop('shiftKey', False)
		self.altKey = kwargs.pop('altKey', False)
		self.metaKey = kwargs.pop('metaKey', False)

		self.button = kwargs.pop('button', 0)
		self.buttons = kwargs.pop('buttons', 0)

		self.relatedTarget = kwargs.pop('relatedTarget', None)
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)
	
	def getModifierState(self, keyArg):
		"Returns true if it is a modifier key and the modifier is activated, false otherwise."
		raise NotImplementedError


class WheelEvent(MouseEvent):
	DOM_DELTA_PIXEL = 0x00
	DOM_DELTA_LINE = 0x01
	DOM_DELTA_PAGE = 0x02
	
	DEFAULTS = {
		'wheel': { 'bubbles':True, 'composed':True, 'cancelable':True }
	}
	
	def __init__(self, type_, **kwargs):
		self.deltaX = kwargs.pop('deltaX', 0.0)
		self.deltaY = kwargs.pop('deltaY', 0.0)
		self.deltaZ = kwargs.pop('deltaZ', 0.0)
		self.deltaMode = kwargs.pop('deltaMode', 0.0)
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


class InputEvent(UIEvent):
	DEFAULTS = {
		'beforeinput': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'input': { 'bubbles':True, 'composed':True }
	}
	
	def __init__(self, type_, **kwargs):
		self.data = kwargs.pop('data', '')
		self.isComposing = kwargs.pop('isComposing', False)
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


class KeyboardEvent(UIEvent):
	DOM_KEY_LOCATION_STANDARD = 0x00
	DOM_KEY_LOCATION_LEFT = 0x01
	DOM_KEY_LOCATION_RIGHT = 0x02
	DOM_KEY_LOCATION_NUMPAD = 0x03
	
	DEFAULTS = {
		'keydown': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'keyup': { 'bubbles':True, 'composed':True, 'cancelable':True }
	}
	
	def __init__(self, type_, **kwargs):
		self.key = kwargs.pop('key', '')
		self.code = kwargs.pop('code', '')
		self.location = kwargs.pop('location', 0)
		
		self.ctrlKey = kwargs.pop('ctrlKey', False)
		self.shiftKey = kwargs.pop('shiftKey', False)
		self.altKey = kwargs.pop('altKey', False)
		self.metaKey = kwargs.pop('metaKey', False)
		
		self.repeat = kwargs.pop('repeat', False)
		self.isComposing = kwargs.pop('isComposing', False)
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


class CompositionEvent(UIEvent):
	DEFAULTS = {
		'compositionstart': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'compositionupdate': { 'bubbles':True, 'composed':True, 'cancelable':True },
		'compositionend': { 'bubbles':True, 'composed':True, 'cancelable':True }
	}
	
	def __init__(self, type_, **kwargs):
		self.data = kwargs.pop("data", "")
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


class FocusEvent(UIEvent):
	DEFAULTS = {
		'blur': { 'composed':True },
		'focus': { 'composed':True },
		'focusin': { 'bubbles':True, 'composed':True },
		'focusout': { 'bubbles':True, 'composed':True }
	}
	
	def __init__(self, type_, **kwargs):
		self.relatedTarget = kwargs.pop('relatedTarget', None)
		
		parms = dict()
		if type_ in self.DEFAULTS:
			parms.update(self.DEFAULTS[type_])
		parms.update(kwargs)		
		super().__init__(type_, **parms)


if __name__ == '__main__':
	from asyncio import run
	from time import time
	from lxml.etree import ElementBase, ProcessingInstruction, XMLParser, ElementDefaultClassLookup, fromstring, tostring
	from pickle import dumps, loads
	
	class Element(ElementBase, EventTarget):
		"Hack to encode event listeners in XML tree, as processing instructions. This is the only way to work with lxml.etree."
		
		PR_INSTR_TARGET = 'x-haael-eventlistener'
		__listener_callbacks = defaultdict(lambda: [None, 0])
		
		def _init(self):
			EventTarget.__init__(self)
			
			for p in list(self):
				if p.tag == ProcessingInstruction and p.target == self.PR_INSTR_TARGET:
					type_, capture, passive, once, signal, callback_id = [eval(_tt) for _tt in p.text.split(' ')]
					listener = EventListener(self.__listener_callbacks[callback_id][0])
					listener.capture = capture
					listener.type_ = type_
					listener.target = self
					self._EventTarget__listeners[type_][capture].append((listener, passive, once, signal))
		
		def get_event_parent(self):
			return self.getparent()
		
		def addEventListener(self, type_, listener, capture=False, passive=False, once=False, signal=None):
			listener = super().addEventListener(type_, listener, capture=capture, passive=passive, once=once, signal=signal)
			
			callback_id = listener.callback.__qualname__ + '@' + hex(id(listener.callback))
			
			self.__listener_callbacks[callback_id][0] = listener.callback
			self.__listener_callbacks[callback_id][1] += 1
			
			self.append(ProcessingInstruction(self.PR_INSTR_TARGET, f'"{type_}" {capture} {passive} {once} {signal} "{callback_id}"'))
			
			return listener
		
		def removeEventListener(self, type_, listener, capture=False):
			try:
				callback = listener.callback
			except AttributeError:
				callback = listener
			
			callback_id = callback.__qualname__ + '@' + hex(id(callback))
			
			self.__listener_callbacks[callback_id][1] -= 1
			if self.__listener_callbacks[callback_id][1] <= 0:
				del self.__listener_callbacks[callback_id]
			
			for p in list(self):
				if p.tag == ProcessingInstruction and p.target == self.PR_INSTR_TARGET:
					#print(p.text.split(' '))
					ttype, tcapture, tpassive, tonce, tsignal, tcallback = [eval(_tt) for _tt in p.text.split(' ')]
					if ttype == type_ and tcallback == callback_id and tcapture == capture:
						self.remove(p)
			
			super().removeEventListener(type_, listener, capture=capture)
	
	xml_parser = XMLParser()
	xml_parser.set_element_class_lookup(ElementDefaultClassLookup(element=Element))
	
	Element.default_handler['load'] = EventListener(lambda _event: print("default", _event))
	Element.default_handler['click'] = EventListener(lambda _event: print("default", _event))
	
	Event._time = time
	
	def handler2(event):
		print("2", event, event.currentTarget)
		#event.stopImmediatePropagation()
	
	async def main():
		listener1 = EventListener(lambda _event: print("1", _event, _event.currentTarget))
		listener4 = EventListener(lambda _event: print("4", _event, _event.currentTarget))
		
		one = fromstring('<one/>', xml_parser)
		two1 = fromstring('<two id="1"/>', xml_parser)
		two2 = fromstring('<two id="2"/>', xml_parser)
		two3 = fromstring('<two id="3"/>', xml_parser)
		one.append(two1)
		one.append(two2)
		one.append(two3)
		
		#print(tostring(one))
		
		listener1a = one.addEventListener('load', listener1)
		assert listener1 == listener1a
		
		listener4a = one.addEventListener('click', listener4)
		assert listener4 == listener4a
		
		listener2 = two1.addEventListener('load', handler2)
		
		def handler3(event):
			print("3", event, event.currentTarget)
			event.preventDefault()
		
		listener3 = two2.addEventListener('load', handler3)
		listener4 = two2.addEventListener('click', handler3)
		
		#print(tostring(one))
		one = fromstring(tostring(one), xml_parser) # test: reconstruct listeners
		#print(tostring(one))
		
		event = UIEvent('load', view=1, detail=2)
		await one.dispatchEvent(event)
		print()
		
		event = UIEvent('click')
		await two1.dispatchEvent(event)
		print()
		await two2.dispatchEvent(event)
		print()
		await two3.dispatchEvent(event)
		print()
		
		one.removeEventListener('load', listener1)
		two1.removeEventListener('load', handler2)
		listener3.remove()
		
		print(tostring(one))
	
	run(main())

