#!/usr/bin/python3
#-*- coding: utf-8 -*-


from time import time


class Window:
	def __init__(self):
		self.queue = []
		self.document = None
	
	def set_document(self, document):
		self.document = document
	
	def queue_event(self, event, target):
		event.target = target
		self.queue.append(event)
	
	def process_events(self, max_time=None):
		start_time = time()
		while self.queue and ((max_time is None) or (time() < start_time + max_time)):
			event = self.queue.pop()
			self.deliver_event(event)
	
	def deliver_event(self, event):
		target = event.target
		
		event.eventPhase = Event.CAPTURING_PHASE
		for currentTarget in event.composedPath:
			event.currentTarget = currentTarget
			self.run_handler_action(currentTarget, event)
			if event.propagationStopped:
				break
		
		if not event.propagationStopped:
			event.eventPhase = Event.TARGET_PHASE
			self.run_handler_action(target, event)
			
			if event.bubbles:
				event.eventPhase = Event.BUBBLING_PHASE
				for currentTarget in reversed(event.composedPath):
					event.currentTarget = currentTarget
					self.run_handler_action(currentTarget, event)
					if event.propagationStopped:
						break
		
		if not event.cancelable or not event.defaultPrevented:
			self.run_default_action(event)
	
	def event_load(self):
		return UIEvent('load', view=self, bubbles=False, cancelable=False)
	
	def keyboard(self, key, state):
		if state:
			self.queue_event(KeyboardEvent('keydown', view=self, bubbles=True, cancelable=True, key=key), self.get_focused_element())
		else:
			self.queue_event(KeyboardEvent('keyup', view=self, bubbles=True, cancelable=True, key=key), self.get_focused_element())
	
	def mouse(self, pointer_x, pointer_y, button_left=None, button_right=None, button_middle=None):
		button_evs = []
		
		if button_left is not None:
			if not self.button_left and button_left:
				button_evs.append('mousedown_left')
			elif self.button_left and not button_left:
				button_evs.append('mouseup_left')
		
		if button_right is not None:
			if not self.button_right and button_right:
				button_evs.append('mousedown_right')
			elif self.button_right and not button_right:
				button_evs.append('mouseup_right')
		
		if button_middle is not None:
			if not self.button_middle and button_middle:
				button_evs.append('mousedown_middle')
			elif self.button_middle and not button_middle:
				button_evs.append('mouseup_middle')
		
		self.button_left = button_left
		self.button_right = button_right
		self.button_middle = button_middle
		
		buttons = (self.button_left ? 0 : 1) << 0 | (self.button_right ? 0 : 1) << 1 | (self.button_middle ? 0 : 1) << 2
		
		target = self.get_pointed_element(pointer_x, pointer_y)
		pass
	
	def wheel(self, direction):
		pass
	
	def touch(self, spots):
		self.queue_event(self.event_touch(), self.get_touched_element())
	
	def run_default_action(self, event):
		pass


class Event:
	NONE = 0
	CAPTURING_PHASE = 1
	AT_TARGET = 2
	BUBBLING_PHASE = 3
	
	def __init__(self, type_, **kwargs):
		self.type_ = type_
		self.target = None
		self.currentTarget = None
		self.eventPhase = self.NONE
		self.bubbles = (('bubbles' in kwargs) and kwargs['bubbles']) or False
		self.cancelable = (('cancelable' in kwargs) and kwargs['cancelable']) or False
		self.defaultPrevented = False
		self.composed = (('composed' in kwargs) and kwargs['composed']) or False
		self.timeStamp = time()
		self.isTrusted = False
	
	def composedPath(self):
		return []
	
	def stopPropagation(self):
		pass
	
	def stopImmediatePropagation(self):
		pass
	
	def preventDefault(self):
		self.defaultPrevented = True


class UIEvent(Event):
	def __init__(self, type_, **kwargs):
		super().__init__(self, type_, **kwargs)
		self.view = (('view' in kwargs) and kwargs['view']) or None
		self.detail = (('detail' in kwargs) and kwargs['detail']) or 0


class KeyboardEvent(UIEvent):
	DOM_KEY_LOCATION_STANDARD = 0x00
	DOM_KEY_LOCATION_LEFT = 0x01
	DOM_KEY_LOCATION_RIGHT = 0x02
	DOM_KEY_LOCATION_NUMPAD = 0x03
	
	def __init__(self, type_, **kwargs):
		super().__init__(self, type_, **kwargs)
		self.key = (('key' in kwargs) and kwargs['key']) or ''
		self.code = (('code' in kwargs) and kwargs['code']) or ''
		self.location = (('location' in kwargs) and kwargs['location']) or self.DOM_KEY_LOCATION_STANDARD
		
		self.ctrlKey = False
		self.shiftKey = False
		self.altKey = False
		self.metaKey = False
		
		self.repeat = (('repeat' in kwargs) and kwargs['repeat']) or False
		self.isComposing = (('isComposing' in kwargs) and kwargs['isComposing']) or False
	
	def getModifierState(self, keyArg):
		return False





