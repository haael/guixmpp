


if __debug__:
	from time import clock_gettime, CLOCK_MONOTONIC
	
	def time():
		return clock_gettime(CLOCK_MONOTONIC)

	
	#CLICK_TIME = float("inf")
	#CLICK_RANGE = 5
	#DBLCLICK_TIME = float("inf")
	#DBLCLICK_RANGE = 5
	#COUNT_TIME = float("inf")
	#COUNT_RANGE = 5


	'''
	@classmethod
	def check_dblclick_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.DBLCLICK_RANGE \
		  and (event.get_time() - press_event.get_time()) < cls.DBLCLICK_TIME:
			return True
		return False
	
	@classmethod
	def check_count_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.COUNT_RANGE \
		  and (event.get_time() - press_event.get_time()) < cls.COUNT_TIME:
			return True
		return False
	
	@classmethod
	def check_click_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.CLICK_RANGE \
		  and (event.get_time() - press_event.get_time()) < cls.CLICK_TIME:
			return True
		return False
	'''
	
	'''
	def synthesize_enter_events(self):
		if __debug__:
			self.emitted_dom_events.clear()
		
		#load_ev = UIEvent("load", target=self.document.getroot())
		#self.emit_dom_event("content_changed_event", load_ev)
		
		#self.change_dom_focus_tabindex(self.tabindex)
		
		for idx, pointer in self.pointers.items():
			self.handle_motion_notify_event(self, namedtuple('event', 'x y x_root y_root state synthesized')(*pointer, *pointer, 0, True)) # TODO: x_root, y_root
		
		if __debug__: self.check_dom_events("content_changed_event")
	
	def synthesize_leave_events(self):
		if __debug__:
			self.emitted_dom_events.clear()
		
		#load_ev = UIEvent("load", target=self.document.getroot())
		#self.emit_dom_event("content_changed_event", load_ev)
		
		#self.change_dom_focus_tabindex(self.tabindex)
		
		if __debug__: self.check_dom_events("content_changed_event")
	
	def set_dom_focus(self, element):
		if element == self.element_in_focus:
			if __debug__: self.check_dom_events("focus_changed_event")
			return
		
		if self.element_in_focus != None:
			fc_ev = FocusEvent(	"focusout", target=self.element_in_focus, relatedTarget=element)
			self.emit_dom_event("focus_changed_event", fc_ev)
		
		if element != None:
			fc_ev = FocusEvent(	"focusin", target=element, relatedTarget=self.element_in_focus)
			self.emit_dom_event("focus_changed_event", fc_ev)
		
		self.previous_focus = self.element_in_focus
		self.element_in_focus = element
		self.tabindex = self.get_element_tabindex(element) if element != None else None
		
		if self.previous_focus != None:
			fc_ev = FocusEvent(	"blur", target=self.previous_focus, relatedTarget=self.element_in_focus)
			self.emit_dom_event("focus_changed_event", fc_ev)
		
		if self.element_in_focus != None:
			fc_ev = FocusEvent(	"focus", target=self.element_in_focus, relatedTarget=self.previous_focus)
			self.emit_dom_event("focus_changed_event", fc_ev)
		
		if __debug__: self.check_dom_events("focus_changed_event")
		
		return False
	
	def change_dom_focus_tabindex(self, index):
		#for item in self.subtree(self.document.getroot()):
		#	i = self.get_element_tabindex(item)
		#	if i != None and int(i) == index:
		#		self.set_dom_focus(item)
		#		break
		#else:
		#	self.ide(None)
		pass # TODO
	
	def change_dom_focus_next(self):
		#index = self.tabindex
		#found = False
		#for i in self.tabindex_list:
		#	if found:
		#		index = i
		#		break
		#	elif i == index:
		#		found = True
		#else:
		#	index = self.tabindex_list[0]
		#schedule(self.change_dom_focus_tabindex)(index)
		pass # TODO
	
	def change_dom_focus_prev(self):
		#index = self.tabindex
		#found = False
		#for i in reversed(self.tabindex_list):
		#	if found:
		#		index = i
		#		break
		#	elif i == index:
		#		found = True
		#else:
		#	index = self.tabindex_list[-1]
		#schedule(self.change_dom_focus_tabindex)(index)
		pass # TODO
	
	def get_element_tabindex(self, element):
		return self.model.element_tabindex(self.image, element)
	
	def parent_ids(self, element): # FIXME
		return frozenset()
	
	def is_element_focusable(self, element):
		if element == None:
			return False
		else:
			return self.get_element_tabindex(element) != None
	
	def is_focused(self, element):
		return self.element_in_focus == element
	'''
	
	'''
	def handle_motion_notify_event(self, drawingarea, event):
		if __debug__:
			assert not self.emitted_dom_events
		
		if self.last_mousedown and not self.check_click_hysteresis(self.last_mousedown, event):
			self.last_mousedown = None
			self.last_mousedown_target = None
		
		self.pointers['0'] = event.x, event.y
		self.previous_nodes_under_pointer = self.nodes_under_pointer
		self.nodes_under_pointer = self.__hover()
		if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			self.rendered_surface.finish()
			self.rendered_surface = self.draw_image()
			self.queue_draw()
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		keys = self.get_keys(event)
		
		if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			for idx in frozenset(chain(self.nodes_under_pointer.keys(), self.previous_nodes_under_pointer.keys())):
				try:
					nup = self.nodes_under_pointer[idx]
				except KeyError:
					nup = []
				
				try:
					pnup = self.previous_nodes_under_pointer[idx]
				except KeyError:
					pnup = []
				
				moved_from_parent_to_child = (nup and pnup and nup[-1] != pnup[-1] and not (self.parent_ids(pnup[-1]) - self.parent_ids(nup[-1])))
				moved_from_child_to_parent = (nup and pnup and nup[-1] != pnup[-1] and not (self.parent_ids(nup[-1]) - self.parent_ids(pnup[-1])))
				
				if pnup:
					if nup:
						if pnup[-1] != nup[-1]:
							ms_ev = MouseEvent("mouseout", target=pnup[-1], \
												clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
												shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
												altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
												buttons=mouse_buttons, relatedTarget=nup[-1])
							self.emit_dom_event("motion_notify_event", ms_ev)

							
							if not moved_from_parent_to_child:
								ms_ev = MouseEvent("mouseleave", target=pnup[-1], \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons, relatedTarget=nup[-1])
								self.emit_dom_event("motion_notify_event", ms_ev)
							
					else:
						ms_ev = MouseEvent("mouseout", target=pnup[-1], \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons)
						self.emit_dom_event("motion_notify_event", ms_ev)
						
						ms_ev = MouseEvent("mouseleave", target=pnup[-1], \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons)
						self.emit_dom_event("motion_notify_event", ms_ev)
				
				if nup:
					if pnup:
						if pnup[-1] != nup[-1]:
							ms_ev = MouseEvent("mouseover", target=nup[-1], \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons, relatedTarget=pnup[-1])
							self.emit_dom_event("motion_notify_event", ms_ev)
							
							if not moved_from_child_to_parent:
								ms_ev = MouseEvent("mouseenter", target=nup[-1], \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons, relatedTarget=pnup[-1])
								self.emit_dom_event("motion_notify_event", ms_ev)
					
					else:
						ms_ev = MouseEvent("mouseover", target=nup[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons)
						self.emit_dom_event("motion_notify_event", ms_ev)
						
						ms_ev = MouseEvent("mouseenter", target=nup[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons)
						self.emit_dom_event("motion_notify_event", ms_ev)
			
			if nup and not hasattr(event, 'synthesized'):
				ms_ev = MouseEvent("mousemove", target=nup[-1], \
								clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								buttons=mouse_buttons)
				self.emit_dom_event("motion_notify_event", ms_ev)
		
		if __debug__:
			self.check_dom_events("motion_notify_event" if not hasattr(event, 'synthesized') else 'synthesized_motion_notify_event')
			assert not self.emitted_dom_events
	
	def handle_button_press_event(self, drawingarea, event):
		if event.state & (Gdk.ModifierType.BUTTON1_MASK | Gdk.ModifierType.BUTTON2_MASK | Gdk.ModifierType.BUTTON3_MASK | Gdk.ModifierType.BUTTON4_MASK | Gdk.ModifierType.BUTTON5_MASK) == 0:
			self.last_mousedown = event.copy()
		else:
			self.last_mousedown = None
			self.last_mousedown_target = None
		
		if self.first_click and not self.check_count_hysteresis(self.first_click, event):
			self.current_click_count = 0
			self.first_click = None
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)
		
		try:
			mousedown_target = self.nodes_under_pointer['0'][-1]
		except IndexError:
			mousedown_target = None
		
		if mousedown_target != None:
			ms_ev = MouseEvent(	"mousedown", target=mousedown_target, \
								detail=self.current_click_count+1, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("button_event", ms_ev)
		
		self.last_mousedown_target = mousedown_target
		
		self.rendered_surface.finish()
		self.rendered_surface = self.draw_image()
		self.queue_draw()

		
		if __debug__: self.check_dom_events("button_event")
	
	def handle_button_release_event(self, drawingarea, event):
		if self.last_mousedown and self.last_mousedown.button.get_button().button == event.button and self.check_click_hysteresis(self.last_mousedown, event):
			event_copy = event.copy()
			schedule(self.emit)('clicked', event_copy)
		
		if self.first_click and not self.check_count_hysteresis(self.first_click, event):
			self.current_click_count = 0
			self.first_click = None
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)
		
		if self.last_mousedown_target != None:
			try:
				mouseup_target = self.nodes_under_pointer['0'][-1]
			except IndexError:
				mouseup_target = None
			ms_ev = MouseEvent(	"mouseup", target=mouseup_target, \
								detail=self.current_click_count+1, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("button_event", ms_ev)
		
		self.last_mousedown = None
		self.last_mousedown_target = None
		
		self.rendered_surface.finish()
		self.rendered_surface = self.draw_image()
		self.queue_draw()
		
		if __debug__: self.check_dom_events("button_event")
	
	def handle_clicked(self, drawingarea, event):
		if self.last_click and self.check_dblclick_hysteresis(self.last_click, event):
			event_copy = event.copy()
			schedule(self.emit)('clicked', event_copy)
			self.last_click = None
		else:
			self.last_click = event.copy()
		
		if self.first_click and self.check_count_hysteresis(self.first_click, event):
			self.current_click_count += 1
		else:
			self.current_click_count = 1
			self.first_click = event.copy()
		
		if self.nodes_under_pointer['0'] and self.is_element_focusable(self.nodes_under_pointer['0'][-1]) and not (self.is_focused(self.nodes_under_pointer['0'][-1])):
			schedule(self.set_dom_focus)(self.nodes_under_pointer['0'][-1])
		
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"click", target=self.nodes_under_pointer['0'][-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("clicked", ms_ev)
		
		if __debug__: self.check_dom_events("clicked")
	
	def handle_auxclicked(self, drawingarea, event):
		self.last_click = None
		
		if self.first_click and self.check_count_hysteresis(self.first_click, event):
			self.current_click_count += 1
		else:
			self.current_click_count = 1
			self.first_click = event.copy()
		
		#if self.nodes_under_pointer and self.is_element_focusable(self.nodes_under_pointer[-1]) and not (self.is_focused(self.nodes_under_pointer[-1])):
		#	schedule(self.set_dom_focus)(self.nodes_under_pointer[-1])
		
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"auxclick", target=self.nodes_under_pointer['0'][-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("clicked", ms_ev)
		
		if __debug__: self.check_dom_events("clicked")
	
	def handle_dblclicked(self, drawingarea, event):
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)

		if self.nodes_under_pointer:
			ms_ev = MouseEvent(	"dblclick", target=self.nodes_under_pointer['0'][-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("clicked", ms_ev)
		
		if __debug__: self.check_dom_events("clicked")
	'''
	
	'''
	def __handle_key_press_event(self, widget, event):
		if self.last_keydown and self.last_keydown.keyval == event.keyval:
			repeated = True
		else:
			self.last_keydown = event.copy()
			repeated = False
		
		#if Gdk.keyval_name(event.keyval).endswith("Tab"):
		#	if event.state & Gdk.ModifierType.SHIFT_MASK:
		#		schedule(self.change_dom_focus_prev)()
		#	else:
		#		schedule(self.change_dom_focus_next)()
		
		focused = self.element_in_focus
		event = KeyboardEvent('keydown', target=focused, key=event.string, code=Gdk.keyval_name(event.keyval), repeat=repeated, **self.__key_location(event), **self.__modifier_keys(event))
		self.emit_dom_event('key_event', event)
		if __debug__: self.check_dom_events("key_event")
	
	def __handle_key_release_event(self, widget, event):
		self.last_keydown = None
		
		focused = self.element_in_focus
		event = KeyboardEvent('keyup', target=focused, key=event.string, code=Gdk.keyval_name(event.keyval), **self.__key_location(event), **self.__modifier_keys(event))
		self.emit_dom_event('key_event', event)
		if __debug__: self.check_dom_events("key_event")
	'''
	
	'''
	def handle_scroll_event(self, widget, event):
		keys = self.get_keys(event)
		if self.nodes_under_pointer:
			wheel_target = self.nodes_under_pointer['0'][-1]
		else:
			wheel_target = None
		
		wh_ev = WheelEvent(	"wheel", target=wheel_target, \
							clientX=event.x, clientY=event.y, \
							screenX=event.x_root, screenY=event.y_root, \
							shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
							altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
							deltaX=event.delta_x, deltaY=event.delta_y, \
							deltaMode=WheelEvent.DOM_DELTA_LINE)
		
		self.emit_dom_event("scrolled_event", wh_ev)
		
		if __debug__: self.check_dom_events("scrolled_event")
	'''
	
	'''
	#def reset_after_exception(self):
	#	if __debug__:
	#		self.emitted_dom_events.clear()
	
	if __debug__:
		def check_dom_events(self, handler):
			nup = self.nodes_under_pointer
			pnup = self.previous_nodes_under_pointer
			
			cnt = Counter((_ms_ev.type_, id(_ms_ev.target)) for _ms_ev in self.emitted_dom_events)
			if cnt:
				common, common_num = cnt.most_common(1)[0]
				assert common_num < 2, "For a DOM Event `{}`, shoudn't be emitted two events with equal target and type.".format(common[0])
			
			#~ Target
			assert all(_ms_ev.target != None for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mouseover", "mouseout", "mouseenter","mouseleave", "mousedown", "click", "dblclick")), "For events of types `mouseover`, `mouseout`, `mouseenter`,`mouseleave`, `mousedown`, `click` and `dblclick` event target can't be None."
			assert all(nup and (_ms_ev.target == nup[-1]) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseover")), "For events of type `mouseover`, event target should be top `nodes_under_pointer` element"
			assert all(nup and (_ms_ev.target in nup) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseenter")), "For events of type `mouseenter`, event target should be in `nodes_under_pointer` elements"
			assert all(pnup and (_ms_ev.target == pnup[-1]) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseout")), "For events of type `mouseout`, event target should be top `previous_nodes_under_pointer` element"
			assert all(pnup and (_ms_ev.target in pnup) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseleave")), "For events of type `mouseleave`, event target should be in `previous_nodes_under_pointer` elements"
			assert all(nup and (_ms_ev.target == nup[-1]) for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mousedown", "click", "dblclick")), "For event of types `mousedown`, `mouseup`, `click` and `dblclick, event target should be top `nodes_under_pointer` element"
			assert all(_ms_ev.target == nup[-1] for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseup") if nup else all(_ms_ev.target == None for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseup"), "For event of type `mouseup` event target should be None if fired out of window border, otherwise target should be top `nodes_under_pointer` if it is over element."
			assert all(_kb_ev.target == self.element_in_focus for _kb_ev in self.emitted_dom_events if _kb_ev.type_ in ("keydown", "keyup")), "For events of type `keydown` or `keyup`, event target should be `self.document.getroot()` if no element is focused."
			assert all(_wh_ev.target == nup[-1] for _wh_ev in self.emitted_dom_events if _wh_ev.type_ == "wheel") if nup else True, "For events of type `wheel`, event target should be top node under pointer."
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusin"), "Focus Event target of type `focusin` should be focusable"
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusout"), "Focus Event target of type `focusout` should be focusable"
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focus"), "Focus Event target of type `focus` should be focusable"
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "blur"), "Focus Event target of type `blur` should be focusable"
			
			#~ Detail
			assert all(_ms_ev.detail == 0 for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mouseenter", "mouseleave", "mousemove", "mouseout", "mouseover")), "For events of types: `mouseenter`, `mouseleave`, `mousemove`, `mouseout` or `mouseover`. `detail` value should be equal to 0."
			assert all(_ms_ev.detail > 0 for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("click", "dblclick", "mousedown", "mouseup")), "For events of types: `click`, `dblclick`, `mousedown` or `mouseup`. `detail` value should be higher then 0."
			assert all(_ms_ev.detail == self.current_click_count + 1 for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mousedown", "mouseup")), "For events of types: `mousedown` or `mouseup`. `detail` value should be equal to `current_click_count` + 1."
			assert all(_ms_ev.detail == self.current_click_count for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("click", "dblclick")), "For events of types: `click` or `dblclick`. `detail` value should be equal to `current_click_count`."
			assert all(_kb_ev.detail == 0 for _kb_ev in self.emitted_dom_events if _kb_ev.type_ in ("keydown", "keyup")), "For `key_event`, all events of type `keydown` or `keyup` should be emitted with default detail."
			
			#~ Mouse event order
			mouseout_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseout"]
			mouseleave_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseleave"]
			mouseover_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseover"]
			mouseenter_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseenter"]
			mousemove_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mousemove"]
			
			for mouseout, mouseleave in itertools.product(mouseout_events, mouseleave_events):
				assert self.emitted_dom_events.index(mouseout) < self.emitted_dom_events.index(mouseleave), "For the appropriate Mouse Event order, events of type `mouseout` should happen before events of type `mouseleave`."
			for mouseleave, mouseover in itertools.product(mouseleave_events, mouseover_events):
				assert self.emitted_dom_events.index(mouseleave) < self.emitted_dom_events.index(mouseover), "For the appropriate Mouse Event order, events of type `mouseleave` should happen before events of type `mouseover`."
			for mouseover, mouseenter in itertools.product(mouseover_events, mouseenter_events):
				assert self.emitted_dom_events.index(mouseover) < self.emitted_dom_events.index(mouseenter), "For the appropriate Mouse Event order, events of type `mouseover` should happen before events of type `mouseenter`."
			for mouseenter, mousemove in itertools.product(mouseenter_events, mousemove_events):
				assert self.emitted_dom_events.index(mouseenter) < self.emitted_dom_events.index(mousemove), "For the appropriate Mouse Event order, events of type `mouseenter` should happen before events of type `mousemove`."
			
			# Focus event order
			focusin_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusin"]
			focusout_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusout"]
			focus_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focus"]
			blur_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "blur"]
			
			for focusin, focus in zip(focusin_event, focus_event):
				assert self.emitted_dom_events.index(focusin) < self.emitted_dom_events.index(focus), "For the appropriate Focus Event order, events of type `focusin` should happen before events of type `focus`."
			for focusout, blur in zip(focusout_event, blur_event):
				assert self.emitted_dom_events.index(focusout) < self.emitted_dom_events.index(blur), "For the appropriate Focus Event order, events of type `focusout` should happen before events of type `blur`."
			for focusin, focus in zip(focusin_event, blur_event):
				assert self.emitted_dom_events.index(focusin) < self.emitted_dom_events.index(blur), "For the appropriate Focus Event order, events of type `focusin` should happen before events of type `blur`."
			for focusout, blur in zip(focusout_event, focus_event):
				assert self.emitted_dom_events.index(focusout) < self.emitted_dom_events.index(focus), "For the appropriate Focus Event order, events of type `focusout` should happen before events of type `focus`."
			
			#~ Repeat
			assert all(_kb_ev.repeat == False for _kb_ev in self.emitted_dom_events if _kb_ev.type_ == "keydown") if not self.last_keydown else True, "For event of type `keydown`, repeat attribute should be False if `last_keydown` not exist."
			assert all(_kb_ev.repeat == True for _kb_ev in self.emitted_dom_events if _kb_ev.type_ == "keydown" and self.last_keydown.keyval == _kb_ev.code) if self.last_keydown else True, "For event of type `keydown`, repeat attribute should be True if `last_keydown` exist and their `keyval` is equal to `KeyboardEvent.code`."
			assert all(_kb_ev.repeat == False for _kb_ev in self.emitted_dom_events if _kb_ev.type_ == "keyup"), "For event of type `keyup`, repeat attribute should be False."
			
			#~ Delta
			assert all(_wh_ev.deltaMode in (WheelEvent.DOM_DELTA_LINE, WheelEvent.DOM_DELTA_PAGE, WheelEvent.DOM_DELTA_PIXEL) for _wh_ev in self.emitted_dom_events if _wh_ev.type_ == "wheel"), "For event of type `wheel`, deltaMode should contain value from constants of WheelEvents."
			
			if handler == "motion_notify_event" or handler == 'synthesized_motion_notify_event':
				moved_from_child_to_parent = (nup and pnup and nup[-1] != pnup[-1] and not (self.parent_ids(nup[-1]) - self.parent_ids(pnup[-1])))
				moved_from_parent_to_child = (nup and pnup and nup[-1] != pnup[-1] and not (self.parent_ids(pnup[-1]) - self.parent_ids(nup[-1])))
				
				if handler != 'synthesized_motion_notify_event':
					#~ Mousemove
					assert any(_ms_ev.type_ == "mousemove" for _ms_ev in self.emitted_dom_events) if nup else True, "For a `motion_notify_event`, when `nodes_under_pointer` are not empty, a DOM event `mousemove` should be emitted."
					assert all(_ms_ev.type_ != "mousemove" for _ms_ev in self.emitted_dom_events) if not nup else True, "For a `motion_notify_event`, when `nodes_under_pointer` are empty, a DOM event `mousemove` should not be emitted."
					assert all(_ms_ev.type_ == "mousemove" for _ms_ev in self.emitted_dom_events) if (nup and pnup and (nup[-1] == pnup[-1])) else True, "For a `motion_notify_event` when the element under pointer hasn't changed, the only emitted DOM event shoud be `mousemove`."
				
				#~ Mouseleave
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseleave` shouldn't be emitted"
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseleave` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseleave` should be emitted"
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseleave` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and not moved_from_parent_to_child) else True, "For `motion_notify_event`, when the pointer moved somewhere else than from parent to child, DOM event `mouseleave` should be emitted"
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and moved_from_parent_to_child) else True, "For `motion_notify_event`, when the pointer moved from parent to child, DOM event `mouseleave` shouldn't be emitted"
				
				#~ Mouseout
				assert all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseout` shouldn't be emitted"
				assert all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseout` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseout` should be emitted"
				assert all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseout` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are different, a DOM event 'mouseout` should be emitted"
				
				#~ Mouseenter
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseleave` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseenter` should be emitted"
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseenter` should be emitted"
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseenter` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and not moved_from_child_to_parent) else True, "For `motion_notify_event`, when the pointer moved somewhere else than from child to parent, DOM event `mouseenter` should be emitted"
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and moved_from_child_to_parent) else True, "For `motion_notify_event`, when the pointer moved from child to parent, DOM event `mouseenter` shouldn't be emitted"
				
				#~Mouseover
				assert all(_ms_ev.type_ != "mouseover" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseover` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseover" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseover` should be emitted"
				assert all(_ms_ev.type_ != "mouseover" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseover` should be emitted"
				assert all(_ms_ev.type_ != "mouseover" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseover` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseover" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are different, a DOM event 'mouseover` should be emitted"

			elif handler == "button_event":
				assert all(_ms_ev.type_ in ["mousedown", "mouseup"] for _ms_ev in self.emitted_dom_events), "For `button_press_event`, only event of type `mousedown` or `mouseup` should be emitted."

			elif handler == "clicked":
				assert all(_ms_ev.type_ in ["click", "auxclick", "dblclick"] for _ms_ev in self.emitted_dom_events), "For `clicked`, only event of type `click`, `auxclick` or `dblclick` should be emitted."
				assert any(_ms_ev.type_ in ["click", "auxclick", "dblclick"] for _ms_ev in self.emitted_dom_events) if nup else True, "For `clicked`, any event of type `click`, `auxclick` or `dblclick` should be emitted."
				
			elif handler == "key_event":
				assert all(_kb_ev.type_ in ["keyup", "keydown"] for _kb_ev in self.emitted_dom_events), "For `key_event`, only event of types `keyup` and `keydown` should be emitted."
				assert any(_kb_ev.type_ in ["keyup", "keydown"] for _kb_ev in self.emitted_dom_events), "For `key_event`, any event of types `keyup` and `keydown` should be emitted."
			
			elif handler == "scrolled_event":
				assert all(_wh_ev.type_ == "wheel" for _wh_ev in self.emitted_dom_events), "For `scrolled_event`, only event of type `wheel` should be emitted."
				assert any(_wh_ev.type_ == "wheel" for _wh_ev in self.emitted_dom_events), "For `scrolled_event`, any event of type `wheel` should be emitted."

			elif handler == "focus_changed_event":
				assert any(_fc_ev.type_ == "focusin" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) else True, "For `focus_change_event`, any event of type `focusin` should be emitted. When top `nodes_under_pointer` is focusable."
				assert any(_fc_ev.type_ == "focusout" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) and self.previous_focus else True, "For `focus_change_event`, any event of type `focusout` should be emitted. When top `nodes_under_pointer` is focusable."
				assert any(_fc_ev.type_ == "focus" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) else True, "For `focus_change_event`, any event of type `focus` should be emitted. When top `nodes_under_pointer` is focusable."
				assert any(_fc_ev.type_ == "blur" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) and self.previous_focus else True, "For `focus_change_event`, any event of type `blur` should be emitted. When top `nodes_under_pointer` is focusable."
				
			self.emitted_dom_events.clear()
	'''
