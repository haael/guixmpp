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

#Extending to UIEvent
class Event():
    """#~ ToDo Doc String"""
    NONE = 0
    CAPTURING_PHASE = 1
    AT_TARGET = 2
    BUBBLING_PHASE = 3

    _EVENTS = { "load": {},
                "unload": {},
                "abort": {},
                "error": {},
                "select": {},
                "blur": {"composed":True},
                "focus": {"composed":True},
                "focusin": {"bubbles":True, "composed":True},
                "focusout": {"bubbles":True, "composed":True},
                "click": {"bubbles":True, "composed":True, "cancelable":True},
                "dblclick": {"bubbles":True, "composed":True, "cancelable":True},
                "mousedown": {"bubbles":True, "composed":True, "cancelable":True},
                "mouseenter": {"composed":True},
                "mouseleave": {"composed":True},
                "mousemove": {"bubbles":True, "composed":True, "cancelable":True},
                "mouseout": {"bubbles":True, "composed":True, "cancelable":True},
                "mouseover": {"bubbles":True, "composed":True, "cancelable":True},
                "mouseup": {"bubbles":True, "composed":True, "cancelable":True},
                "wheel": {"bubbles":True, "composed":True, "cancelable":True},
                "beforeinput": {"bubbles":True, "composed":True, "cancelable":True},
                "input": {"bubbles":True, "composed":True},
                "keydown": {"bubbles":True, "composed":True, "cancelable":True},
                "keyup": {"bubbles":True, "composed":True, "cancelable":True},
                "compositionstart": {"bubbles":True, "composed":True, "cancelable":True},
                "compositionupdate": {"bubbles":True, "composed":True, "cancelable":True},
                "compositionend": {"bubbles":True, "composed":True, "cancelable":True}}
                #DEFAULTS >> bubbles = False | cancelable = False | composed = False

    def __init__(self, type_, **kwargs):
        if type_ in EVENTS:
            WriteAccess(self).type_ = type_
            WriteAccess(self).composed = EVENTS.get(type_).get("composed", False)
            WriteAccess(self).cancelable = EVENTS.get(type_).get("cancelable", False)
            WriteAccess(self).bubbles = EVENTS.get(type_).get("bubbles", False)
        else:
            raise AttributeError("Type is not defined.")

        WriteAccess(self).target = None
        WriteAccess(self).isTrusted = False
        WriteAccess(self).srcElement = None
        WriteAccess(self).currentTarget = None

        self.eventPhase = None
        self.defaultPrevented = None
        self.timeStamp = time() #~ ToDo DOMHighResTimeStamp
        if kwargs != {}: #If kwargs isn't empty.
            raise TypeError("Check arguments names or remove surplus.")

    def __setattr__(self, attr, value):
        if attr in ("eventPhase", "defaultPrevented", "timeStamp"):
            self.__dict__[attr] = value
        else:
            raise AccessError("Attribute can't be overwritted")

    def __delattr__(self, val):
        raise AccessError("Attribute can't be deleted.")

    def __private_setattr(self, attr, value):
        super().__setattr__(attr, value)

    def stopPropagation(self): #~ ToDo
        """#~ ToDo Doc String"""
        #When dispatched in a tree, invoking this method prevents event from reaching any
        #objects other than the current object.

    def stopImmediatePropagation(self): #~ ToDo
        """#~ ToDo Doc String"""
        #Invoking this method prevents event from reaching any registered event listeners after
        #the current one finishes running and, when dispatched in a tree, also prevents
        #event from reaching any other objects.

    def preventDefault(self): #~ ToDo
        """#~ ToDo||Set defaultPrevented to True if cancelation is indicated else set to False."""
        #~ If cancelation is succesful
        #~ self.defaultPrevented = True
        #~ Else
        #~ self.defaultPrevented = False

    def composedPath(self): #~ ToDo
        """#~ ToDo Doc String"""
            #Returns the item objects of event’s path (objects on which listeners will be invoked),
        #except for any nodes in shadow trees of which the shadow root’s mode is "closed" that
        #are not reachable from event’s currentTarget.


#Extending to MouseEvent, InputEvent, KeyboardEvent, CompositionEvent, FocusEvent
class UIEvent(Event):
    """#~ ToDo Doc String"""

    def __init__(self, type_, **kwargs):
        WriteAccess(self).view = kwargs.pop("view", None)
        WriteAccess(self).detail = kwargs.pop("detail", 0)
        super().__init__(self, type_, **kwargs)


#Extending to WheelEvent
class MouseEvent(UIEvent):
    """#~ ToDo Doc String"""

    def __init__(self, type_, **kwargs):
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
        super().__init__(self, type_, **kwargs)

    def getModifierState(self, keyArg):
        pass
        #ToDo Returns true if it is a modifier key and the modifier is activated, false otherwise.

class WheelEvent(MouseEvent):
    """#~ ToDo Doc String"""
    DOM_DELTA_PIXEL = 0x00
    DOM_DELTA_LINE = 0x01
    DOM_DELTA_PAGE = 0x02

    def __init__(self, type_, **kwargs):
        WriteAccess(self).deltaX = kwargs.pop("deltaX", 0.0)
        WriteAccess(self).deltaY = kwargs.pop("deltaY", 0.0)
        WriteAccess(self).deltaZ = kwargs.pop("deltaZ", 0.0)
        WriteAccess(self).deltaMode = kwargs.pop("deltaMode", 0.0)
        super().__init__(self, type_, **kwargs)

class InputEvent(UIEvent):
    """#~ ToDo Doc String"""

    def __init__(self, type_, **kwargs):
        WriteAccess(self).data = kwargs.pop("data", "")
        WriteAccess(self).isComposing = kwargs.pop("isComposing", False)
        super().__init__(self, type_, **kwargs)

class KeyboardEvent(UIEvent):
    """#~ ToDo Doc String"""
    DOM_KEY_LOCATION_STANDARD = 0x00
    DOM_KEY_LOCATION_LEFT = 0x01
    DOM_KEY_LOCATION_RIGHT = 0x02
    DOM_KEY_LOCATION_NUMPAD = 0x03

    def __init__(self, type_, **kwargs):
        WriteAccess(self).key = kwargs.pop("key", "")
        WriteAccess(self).code = kwargs.pop("code", "")
        WriteAccess(self).location = kwargs.pop("location", 0)

        WriteAccess(self).ctrlKey = kwargs.pop("ctrlKey", False)
        WriteAccess(self).shiftKey = kwargs.pop("shiftKey", False)
        WriteAccess(self).altKey = kwargs.pop("altKey", False)
        WriteAccess(self).metaKey = kwargs.pop("metaKey", False)

        WriteAccess(self).repeat = kwargs.pop("repeat", False)
        WriteAccess(self).isComposing = kwargs.pop("isComposing", False)
        super().__init__(self, type_, **kwargs)

class CompositionEvent(UIEvent):
    """#~ ToDo Doc String"""

    def __init__(self, type_, **kwargs):
        WriteAccess(self).data = kwargs.pop("data", "")
        super().__init__(self, type_, **kwargs)

class FocusEvent(UIEvent):
    """#~ ToDo Doc String"""

    def __init__(self, type_, **kwargs):
        WriteAccess(self).relatedTarget = kwargs.pop("relatedTarget", None)
        super().__init__(self, type_, **kwargs)

