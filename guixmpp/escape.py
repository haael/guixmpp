#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'Escape',


from enum import Enum, auto


class Escape(Enum):
	begin_draw = auto() # draw function
	end_draw = auto()
	begin_poke = auto() # "poke" (pointer event) function
	end_poke = auto()
	begin_tag = auto() # opening XML tag
	end_tag = auto() # closing XML tag
	begin_filter = auto() # apply filter
	end_filter = auto()
	begin_transform = auto() # apply transformation
	end_transform = auto()
	begin_measure = auto() # text measurements
	end_measure = auto()
	begin_escape = auto() # esape sequence
	end_escape = auto()
	begin_line = auto() # text line
	end_line = auto()
	begin_text = auto() # render text string
	end_text = auto()
	begin_print = auto() # render text string
	end_print = auto()

