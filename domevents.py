# /usr/bin/python3
#-*- coding: utf-8 -*-

from time import time

class EventTarget():
    #~ ToDo
    def __init__(self, **kwargs):
        pass

    def addEventListener(self, _type, callback, **kwargs): #~ ToDo EventListener? // void
        if "options" in kwargs:
            options = kwargs["options"]
            if isinstance(options, EventListener) or isinstance(options, EventListener)):
                _options = kwargs["options"] #EventListener obj or bool
            else:
                _options = False
        """
            Let capture, passive, and once be the result of flattening more options.
            Add an event listener with the context object and an event listener whose type is type, callback is callback, capture is capture, passive is passive, and once is once.
        """

    def removeEventListener(self, _type, callback, **kwargs): #~ ToDo EventListener? // void
        if "options" in kwargs:
            options = kwargs["options"]
            if isinstance(options, EventListener) or isinstance(options, EventListener)):
                _options = kwargs["options"] #EventListener obj or bool
            else:
                _options = False
        """
            If the context object’s relevant global object is a ServiceWorkerGlobalScope object and its associated service worker’s script resource’s has ever been evaluated flag is set, then throw a TypeError. [SERVICE-WORKERS]
            Let capture be the result of flattening options.
            If the context object’s event listener list contains an event listener whose type is type, callback is callback, and capture is capture, then remove an event listener with the context object and that event listener.
        """

    def dispatchEvent(self, event): #~ // bool
        """
            If event’s dispatch flag is set, or if its initialized flag is not set, then throw an "InvalidStateError" DOMException.
            Initialize event’s isTrusted attribute to false.
            Return the result of dispatching event to the context object.
        """
        pass

class EventListener():


class Window(EventTarget):
    pass
    #~ ToDo

#Extending to UIEvent, CustomEvent
class Event():
    NONE = 0
    CAPTURING_PHASE = 1
    AT_TARGET = 2
    BUBBLING_PHASE = 3

    def __init__(self, _type, **kwargs):
        self._type = _type
        self._target = None #~ EventTarget?
        self._isTrusted = False #~ Bool
        self._srcElement = None #~ EventTarget?
        self._currentTarget = None #~  EventTarget?
        self._composed = kwargs["bubbles"] if "bubbles" in kwargs else False
        self._cancelable = kwargs["cancelable"] if "cancelable" in kwargs else False
        self._bubbles = kwargs["composed"] if "composed" in kwargs else False
        self.eventPhase = None
        self.defaultPrevented = None
        self.timeStamp = time() #~ ToDo DOMHighResTimeStamp

    def stopPropagation(self): #~ ToDo
        pass

    def stopImmediatePropagation(self): #~ ToDo
        pass

    def preventDefault(self): #~ ToDo
        pass

    def composedPath(self): #~ ToDo
        pass

    #~ property section:
    @property
    def type(self): return self._type;
    @property
    def target(self): return self._target;
    @property
    def srcElement(self): return self._srcElement;
    @property
    def currentTarget(self): return self._currentTarget;
    @property
    def composed(self): return self._composed;
    @property
    def cancelable(self): return self._cancelable;
    @property
    def bubbles(self): return self._bubbles;

#Extending to MouseEvent, InputEvent, KeyboardEvent, CompositionEvent, FocusEvent
class UIEvent(Event):

    def __init__(self, _type, **kwargs):
        super().__init__(self, _type, **kwargs)
        self._view = kwargs["view"] if "view" in kwargs else None #~ ToDo Window?
        self._detail = kwargs["detail"] if "detail" in kwargs else 0

    #~ property section:
    @property
    def view(self): return self._view;
    @property
    def detail(self): return self._detail;

#Extending to WheelEvent
class MouseEvent(UIEvent):

    def __init__(self, _type, **kwargs):
        self._screenX = kwargs["screenX"] if "screenX" in kwargs else 0
        self._screenY = kwargs["screenY"] if "screenY" in kwargs else 0
        self._clientX = kwargs["clientX"] if "clientX" in kwargs else 0
        self._clientY = kwargs["clientY"] if "clientY" in kwargs else 0

        self._ctrlKey = kwargs["ctrlKey"] if "ctrlKey" in kwargs else False
        self._shiftKey = kwargs["shiftKey"] if "shiftKey" in kwargs else False
        self._altKey = kwargs["altKey"] if "altKey" in kwargs else False
        self._metaKey = kwargs["metaKey"] if "metaKey" in kwargs else False

        self._button = kwargs["button"] if "button" in kwargs else 0
        """
            0 MUST indicate the primary button of the device (in general, the left button or the only button on single-button devices, used to activate a user interface control or select text) or the un-initialized value.
            1 MUST indicate the auxiliary button (in general, the middle button, often combined with a mouse wheel).
            2 MUST indicate the secondary button (in general, the right button, often used to display a context menu).
        """
        self._buttons = kwargs["buttons"] if "buttons" in kwargs else 0
        """ MUST indicate no button is currently active.
            1 MUST indicate the primary button of the device (in general, the left button or the only button on single-button devices, used to activate a user interface control or select text).
            2 MUST indicate the secondary button (in general, the right button, often used to display a context menu), if present.
            4 MUST indicate the auxiliary button (in general, the middle button, often combined with a mouse wheel).
        """

        self._relatedTarget = kwargs["relatedTarget"] if "relatedTarget" in kwargs else None

    def getModifierState(self, keyArg):
        pass
        #ToDo Returns true if it is a modifier key and the modifier is activated, false otherwise.

    #~ property section:
    @property
    def screenX(self): return self._screenX;
    @property
    def screenY(self): return self._screenY;
    @property
    def clientX(self): return self._clientX;
    @property
    def clientY(self): return self._clientY;
    @property
    def ctrlKey(self): return self._ctrlKey;
    @property
    def shiftKey(self): return self._shiftKey;
    @property
    def altKey(self): return self._altKey;
    @property
    def metaKey(self): return self._metaKey;
    @property
    def button(self): return self._button;
    @property
    def buttons(self): return self._buttons;
    @property
    def relatedTarget(self): return self._relatedTarget;

class WheelEvent(MouseEvent):
    DOM_DELTA_PIXEL = 0x00
    DOM_DELTA_LINE = 0x01
    DOM_DELTA_PAGE = 0x02

    def __init__(self, _type, **kwargs):
        super().__init__(self, _type, **kwargs)
        self._deltaX = kwargs["deltaX"] if "deltaX" in kwargs else 0.0
        self._deltaY = kwargs["deltaY"] if "deltaY" in kwargs else 0.0
        self._deltaZ = kwargs["deltaZ"] if "deltaZ" in kwargs else 0.0
        self._deltaMode = kwargs["deltaMode"] if "deltaMode" in kwargs else 0.0

    #~ property section:
    @property
    def deltaX(self): return self._deltaX;
    @property
    def deltaY(self): return self._deltaY;
    @property
    def deltaZ(self): return self._deltaZ;
    @property
    def deltaMode(self): return self._deltaMode;

class InputEvent(UIEvent):

    def __init__(self, _type, **kwargs):
        super().__init__(self, _type, **kwargs)
        self._data = kwargs["data"] if "data" in kwargs else "" #~ ToDo DOMString
        self._isComposing = kwargs["isComposing"] if "isComposing" in kwargs else False

    #~ property section:
    @property
    def data(self): return self._data;
    @property
    def isComposing(self): return self._isComposing;

class KeyboardEvent(UIEvent):
    DOM_KEY_LOCATION_STANDARD = 0x00
    DOM_KEY_LOCATION_LEFT = 0x01
    DOM_KEY_LOCATION_RIGHT = 0x02
    DOM_KEY_LOCATION_NUMPAD = 0x03

    def __init__(self, _type, **kwargs):
        super().__init__(self, _type, **kwargs)
        self._key = kwargs["key"] if "key" in kwargs else "" #~ ToDo DOMString
        self._code = kwargs["code"] if "code" in kwargs else "" #~ ToDo DOMString
        self._location = kwargs["location"] if "location" in kwargs else 0

        self._ctrlKey = kwargs["ctrlKey"] if "ctrlKey" in kwargs else False
        self._shiftKey = kwargs["shiftKey"] if "shiftKey" in kwargs else False
        self._altKey = kwargs["altKey"] if "altKey" in kwargs else False
        self._metaKey = kwargs["metaKey"] if "metaKey" in kwargs else False

        self._repeat = kwargs["repeat"] if "repeat" in kwargs else False
        self._isComposing = kwargs["isComposing"] if "isComposing" in kwargs else False

    #~ property section:
    @property
    def key(self): return self._key;
    @property
    def code(self): return self._code;
    @property
    def location(self): return self._location;
    @property
    def ctrlKey(self): return self._ctrlKey;
    @property
    def shiftKey(self): return self._shiftKey;
    @property
    def altKey(self): return self._altKey;
    @property
    def metaKey(self): return self._metaKey;
    @property
    def repeat(self): return self._repeat;
    @property
    def isComposing(self): return self._isComposing;

class CompositionEvent(UIEvent):
    def __init__(self, _type, **kwargs):
        super().__init__(self, _type, **kwargs)
        self._data = kwargs["data"] if "data" in kwargs else "" #~ ToDo DOMString

    #~ property section:
    @property
    def data(self): return self._data;

class FocusEvent(UIEvent):
    def __init__(self, _type, **kwargs):
        super().__init__(self, _type, **kwargs)
        self._relatedTarget = kwargs["relatedTarget"] if "relatedTarget" in kwargs else None #~ ToDo EventTarget

    #~ property section:
    @property
    def relatedTarget(self): return self._relatedTarget;

#
