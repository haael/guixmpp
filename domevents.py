#!/usr/bin/python3
#-*- coding: utf-8 -*-

from time import time


class AccessError(Exception):
	def __init__(self, message):
		self.message = message


class WriteAccess():
	def __init__(self, parent):
		super().__setattr__('parent', parent)

	def __getattr__(self, attr):
		return getattr(self.parent, attr)

	def __setattr__(self, attr, value):
		self.parent._Event__private_setattr(attr, value)


class Event:
	NONE = 0
	CAPTURING_PHASE = 1
	AT_TARGET = 2
	BUBBLING_PHASE = 3

	def __init__(self, type_, **kwargs):
		if type(self) == Event:
			raise ValueError("Direct instantiation of class 'Event' is not allowed.")
		WriteAccess(self).target = kwargs.pop("target", None)
		WriteAccess(self).isTrusted = False
		WriteAccess(self).srcElement = None
		WriteAccess(self).currentTarget = None

		self.eventPhase = None
		self.defaultPrevented = None
		self.timeStamp = time() #~ ToDo DOMHighResTimeStamp
		if kwargs:
			raise TypeError("Check arguments names or remove surplus.\nNot allowed kwarguments: {}".format(list(kwargs.keys())))

	def __setattr__(self, attr, value):
		if attr in ("eventPhase", "defaultPrevented", "timeStamp"):
			self.__private_setattr(attr, value)
		else:
			raise AccessError("Attribute '{}' can't be overwritten".format(attr))

	def __delattr__(self, attr):
		raise AccessError("Attribute '{}' can't be deleted.".format(attr))

	def __private_setattr(self, attr, value):
		super().__setattr__(attr, value)

	def __repr__(self):
		rejected = ("type_", "composed", "cancelable", "bubbles", "target", "isTrusted", "srcElement", "currentTarget",\
					"eventPhase", "defaultPrevented", "timeStamp", "currentTarget")
		return "{}(\'{}\', target={}, {})".format(type(self).__name__, self.type_, repr(self.target),
				", ".join(f"{k}={repr(v)}" for (k, v) in self.__dict__.items() if k not in rejected))

	def _default_type_fields(self, type_):
		try:
			WriteAccess(self).type_ = type_
			WriteAccess(self).composed = self._EVENTS[type_].get("composed", False)
			WriteAccess(self).cancelable = self._EVENTS[type_].get("cancelable", False)
			WriteAccess(self).bubbles = self._EVENTS[type_].get("bubbles", False)
		except KeyError:
			raise ValueError("Type \"{}\" is not allowed here. Allowed types are: {}.".format(type_, list(self._EVENTS.keys())))

	def stopPropagation(self): #~ ToDo
		#When dispatched in a tree, invoking this method prevents event from reaching any
		#objects other than the current object.
		pass

	def stopImmediatePropagation(self): #~ ToDo
		#Invoking this method prevents event from reaching any registered event listeners after
		#the current one finishes running and, when dispatched in a tree, also prevents
		#event from reaching any other objects.
		pass

	def preventDefault(self): #~ ToDo
		"""#~ ToDo||Set defaultPrevented to True if cancelation is indicated else set to False."""
		#~ If cancelation is succesful
		#~ self.defaultPrevented = True
		#~ Else
		#~ self.defaultPrevented = False
		pass

	def composedPath(self): #~ ToDo
		#Returns the item objects of event’s path (objects on which listeners will be invoked),
		#except for any nodes in shadow trees of which the shadow root’s mode is "closed" that
		# are not reachable from event’s currentTarget.
		pass


class CustomEvent(Event):
	_EVENTS = { "beforeload":{},
				"beforeunload":{},
				"open":{},
				"close":{},
				"opening":{},
				"closing":{},
				"warning":{}}

	def __init__(self, type_, **kwargs):
		if type(self) == CustomEvent:
			self._default_type_fields(type_)

		WriteAccess(self).node = kwargs.pop("node", None)
		WriteAccess(self).view = kwargs.pop("view", None)
		WriteAccess(self).detail = kwargs.pop("detail", 0)
		super().__init__(type_, **kwargs)


#Extending to MouseEvent, InputEvent, KeyboardEvent, CompositionEvent, FocusEvent
class UIEvent(Event):
	_EVENTS = { "load": {},
				"unload": {},
				"abort": {},
				"error": {},
				"select": {}}

	def __init__(self, type_, **kwargs):
		if type(self) == UIEvent:
			self._default_type_fields(type_)

		WriteAccess(self).view = kwargs.pop("view", None)
		WriteAccess(self).detail = kwargs.pop("detail", 0)
		super().__init__(type_, **kwargs)


#Extending to WheelEvent
class MouseEvent(UIEvent):
	_EVENTS = { "click": {"bubbles":True, "composed":True, "cancelable":True},
				"auxclick": {"bubbles":True, "composed":True, "cancelable":True},
				"dblclick": {"bubbles":True, "composed":True, "cancelable":True},
				"mousedown": {"bubbles":True, "composed":True, "cancelable":True},
				"mouseenter": {"composed":True},
				"mouseleave": {"composed":True},
				"mousemove": {"bubbles":True, "composed":True, "cancelable":True},
				"mouseout": {"bubbles":True, "composed":True, "cancelable":True},
				"mouseover": {"bubbles":True, "composed":True, "cancelable":True},
				"mouseup": {"bubbles":True, "composed":True, "cancelable":True}}

	def __init__(self, type_, **kwargs):
		if type(self) == MouseEvent:
			self._default_type_fields(type_)

		WriteAccess(self).screenX = kwargs.pop("screenX", 0)
		WriteAccess(self).screenY = kwargs.pop("screenY", 0)
		WriteAccess(self).clientX = kwargs.pop("clientX", 0)
		WriteAccess(self).clientY = kwargs.pop("clientY", 0)

		WriteAccess(self).ctrlKey = kwargs.pop("ctrlKey", False)
		WriteAccess(self).shiftKey = kwargs.pop("shiftKey", False)
		WriteAccess(self).altKey = kwargs.pop("altKey", False)
		WriteAccess(self).metaKey = kwargs.pop("metaKey", False)

		WriteAccess(self).button = kwargs.pop("button", 0)
		WriteAccess(self).buttons = kwargs.pop("buttons", 0)

		WriteAccess(self).relatedTarget = kwargs.pop("relatedTarget", None)
		super().__init__(type_, **kwargs)

	def __repr__(self):
		rejected = ("type_", "composed", "cancelable", "bubbles", "target", "isTrusted", "srcElement", "currentTarget",\
					"eventPhase", "defaultPrevented", "timeStamp", "currentTarget", "clientX", "clientY")
		return "{}(\"{}\", target={}, clientX={}, clientY={}, {})".format(
				type(self).__name__, self.type_, self.target, self.clientX, self.clientY,
				", ".join(f"{k}={repr(v)}" for (k, v) in self.__dict__.items() if k not in rejected))

	def getModifierState(self, keyArg):
		pass
		#ToDo Returns true if it is a modifier key and the modifier is activated, false otherwise.


class WheelEvent(MouseEvent):
	DOM_DELTA_PIXEL = 0x00
	DOM_DELTA_LINE = 0x01
	DOM_DELTA_PAGE = 0x02

	_EVENTS = { "wheel": {"bubbles":True, "composed":True, "cancelable":True}}

	def __init__(self, type_, **kwargs):
		self._default_type_fields(type_)

		WriteAccess(self).deltaX = kwargs.pop("deltaX", 0.0)
		WriteAccess(self).deltaY = kwargs.pop("deltaY", 0.0)
		WriteAccess(self).deltaZ = kwargs.pop("deltaZ", 0.0)
		WriteAccess(self).deltaMode = kwargs.pop("deltaMode", 0.0)
		super().__init__(type_, **kwargs)


class InputEvent(UIEvent):
	_EVENTS = { "beforeinput": {"bubbles":True, "composed":True, "cancelable":True},
				"input": {"bubbles":True, "composed":True}}

	def __init__(self, type_, **kwargs):
		self._default_type_fields(type_)

		WriteAccess(self).data = kwargs.pop("data", "")
		WriteAccess(self).isComposing = kwargs.pop("isComposing", False)
		super().__init__(type_, **kwargs)


class KeyboardEvent(UIEvent):
	DOM_KEY_LOCATION_STANDARD = 0x00
	DOM_KEY_LOCATION_LEFT = 0x01
	DOM_KEY_LOCATION_RIGHT = 0x02
	DOM_KEY_LOCATION_NUMPAD = 0x03

	_EVENTS = { "keydown": {"bubbles":True, "composed":True, "cancelable":True},
				"keyup": {"bubbles":True, "composed":True, "cancelable":True}}

	def __init__(self, type_, **kwargs):
		self._default_type_fields(type_)

		WriteAccess(self).key = kwargs.pop("key", "")
		WriteAccess(self).code = kwargs.pop("code", "")
		WriteAccess(self).location = kwargs.pop("location", 0)

		WriteAccess(self).ctrlKey = kwargs.pop("ctrlKey", False)
		WriteAccess(self).shiftKey = kwargs.pop("shiftKey", False)
		WriteAccess(self).altKey = kwargs.pop("altKey", False)
		WriteAccess(self).metaKey = kwargs.pop("metaKey", False)

		WriteAccess(self).repeat = kwargs.pop("repeat", False)
		WriteAccess(self).isComposing = kwargs.pop("isComposing", False)
		super().__init__(type_, **kwargs)


class CompositionEvent(UIEvent):
	_EVENTS = { "compositionstart": {"bubbles":True, "composed":True, "cancelable":True},
				"compositionupdate": {"bubbles":True, "composed":True, "cancelable":True},
				"compositionend": {"bubbles":True, "composed":True, "cancelable":True}}

	def __init__(self, type_, **kwargs):
		self._default_type_fields(type_)

		WriteAccess(self).data = kwargs.pop("data", "")
		super().__init__(type_, **kwargs)


class FocusEvent(UIEvent):
	_EVENTS = { "blur": {"composed":True},
				"focus": {"composed":True},
				"focusin": {"bubbles":True, "composed":True},
				"focusout": {"bubbles":True, "composed":True}}

	def __init__(self, type_, **kwargs):
		self._default_type_fields(type_)

		WriteAccess(self).relatedTarget = kwargs.pop("relatedTarget", None)
		super().__init__(type_, **kwargs)


if __debug__ and __name__ == "__main__":
	#import unittest

	## variable tests
	ui = UIEvent("load")
	we = WheelEvent("wheel", deltaY=3.0)
	ke = KeyboardEvent("keydown")
	fe = FocusEvent("focusin")

	try: ui.composed = True;
	except AccessError: pass;
	else: assert False, "Setting attribute should raise AccessError"

	try: fe.relatedTarget = None;
	except AccessError: pass;
	else: assert False, "Setting attribute should raise AccessError"

	#print("timeStamp:", ui.timeStamp)
	ui.timeStamp = 0
	assert ui.timeStamp == 0
	#print("timeStamp overwrited:", ui.timeStamp)

	try: del ui.timeStamp;
	except AccessError: pass;
	else: assert False

	assert we.deltaX == 0.0
	assert we.deltaY == 3.0
	print("Event type default for 'load'|composed", ui.composed, "cancelable", ui.cancelable, "bubbles", ui.bubbles)
	print("Event type default for 'wheel'|composed", we.composed, "cancelable", we.cancelable, "bubbles", we.bubbles)
	print("Event type default for 'keydown'|composed", ke.composed, "cancelable", ke.cancelable, "bubbles", ke.bubbles)
	print("Event type default for 'focusin'|composed", fe.composed, "cancelable", fe.cancelable, "bubbles", fe.bubbles)


	## constants tests
	#print("\n\tConstants tests")
	we.DOM_DELTA_PIXEL
	try: we.DOM_DELTA_PIXEL = 2;
	except AccessError as exc: pass;
	else: assert False, "Setting attribute should raise AccessError"

	try: del(we.DOM_DELTA_LINE);
	except AccessError as exc: pass;
	else: assert False, "Deleting attribute should raise AccessError"

	try: we._EVENTS = { "nowy": {"bubbles":True, "composed":False, "cancelable":False}}
	except AccessError as exc: pass;
	else: assert False, "Setting attribute should raise AccessError"

	try: del(we._EVENTS);
	except AccessError as exc: pass;
	else: assert False, "Deleting attribute should raise AccessError"

	#try: we._EVENTS["nowy"] = {"bubbles":True, "composed":False, "cancelable":False};
	#except AttributeError as exc: pass;
	#else: assert False, "Atrribute should not be present in that object"


	## declaration tests
	#print("\n\tDeclaration tests")
	try: Event(); #Empty Event
	except TypeError as exc: pass;
	else: assert False

	try: Event("load"); #Event declaration
	except ValueError as exc: pass;
	else: assert False

	try: UIEvent("blur"); #Wrong type
	except ValueError as exc: pass;
	else: assert False

	try: WheelEvent(); #Empty declaration
	except TypeError as exc: pass;
	else: assert False

	try: MouseEvent("click", test=True) #Not allowed kwargs
	except TypeError as exc: pass;
	else: assert False

	try: KeyboardEvent("load") #Parent type
	except ValueError as exc: pass;
	else: assert False

	print("\n\tKontruktory repr:")
	print(repr(we), end="\n\n")
	print(repr(ke), end="\n\n")
	print(repr(fe), end="\n\n")
	print(repr(ui), end="\n\n")

	del(we, ke, fe, ui)

	'''
	## unittests
	print("\n\tUnit tests")
	we = WheelEvent("wheel", altKey=True)
	tc = unittest.TestCase('__init__')
	tc.assertEquals(we.composed, True)
	tc.assertEquals(we.altKey, True)
	del(we)

	ke = KeyboardEvent("keyup", altKey=False, key="", repeat=False, metaKey=False, detail=0, ctrlKey=False, view=None, code="", isComposing=True, shiftKey=False, location=0)
	tc.assertEquals(ke.key, "")
	tc.assertEquals(ke.code, "")
	tc.assertEquals(ke.location, 0)
	tc.assertEquals(ke.repeat, False)
	tc.assertEquals(ke.isComposing, True)
	del(ke)

	print("No error during unittest has occured.")
	'''
