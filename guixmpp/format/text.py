#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PlainFormat',


from io import BytesIO
from math import ceil, sqrt
import cairo
from re import split as re_split, finditer
from base64 import b64encode
import unicodedata
from collections import defaultdict, deque
from itertools import chain
from enum import Enum
from pyphen import Pyphen
from inspect import isgeneratorfunction


if __name__ == '__main__':
	from guixmpp.escape import Escape
else:
	from ..escape import Escape


def cached(old_method):
	if isgeneratorfunction(old_method):
		def new_method(self, *args, **kwargs):
			try:
				method_cache = self.__method_cache
			except AttributeError:
				method_cache = self.__method_cache = {}
			
			try:
				cache = method_cache[old_method.__name__]
			except KeyError:
				cache = method_cache[old_method.__name__] = {}
			
			try:
				series, error = cache[args, frozenset(kwargs.items())]
			except KeyError:
				try:
					series = []
					for value in old_method(self, *args, **kwargs):
						series.append(value)
						yield value
				except Exception as error:
					cache[args, frozenset(kwargs.items())] = (series, error)
				else:
					cache[args, frozenset(kwargs.items())] = (series, None)
			else:
				yield from series
				if error is not None:
					raise error
	else:
		def new_method(self, *args, **kwargs):
			try:
				method_cache = self.__method_cache
			except AttributeError:
				method_cache = self.__method_cache = {}
			
			try:
				cache = method_cache[old_method.__name__]
			except KeyError:
				cache = method_cache[old_method.__name__] = {}
			
			try:
				result, value = cache[args, frozenset(kwargs.items())]
			except KeyError:
				try:
					value = old_method(self, *args, **kwargs)
				except Exception as error:
					cache[args, frozenset(kwargs.items())] = (False, error)
					raise
				else:
					cache[args, frozenset(kwargs.items())] = (True, value)
					return value
			else:
				if result:
					return value
				else:
					raise value
	
	return new_method


class ParseTree:
	def __init__(self, production, arguments):
		self.production = production
		self.arguments = arguments
	
	def __repr__(self):
		return f"{self.__class__.__name__}({self.production}, {self.arguments})"
	
	def __str__(self):
		if isinstance(self.arguments, str):
			return self.arguments
		else:
			return " ".join(str(_arg) for _arg in self.arguments)
	
	def print_tree(self, level=0):
		yield level, self.production
		if isinstance(self.arguments, str):
			yield (level + 1), repr(self.arguments)
		else:
			for arg in self.arguments:
				yield from arg.print_tree(level + 1)
	
	def __call__(self, context, text, position, direction=None):
		if self.production == 'RULE ::= EXPR OP EXPR':
			if self.arguments[0](context, text, position - 1, -1) and self.arguments[2](context, text, position, +1):
				return self.arguments[1](None, None, None)
		elif self.production == 'RULE ::= OP EXPR':
			if self.arguments[1](context, text, position, +1):
				return self.arguments[0](None, None, None)
		elif self.production == 'RULE ::= EXPR OP':
			if self.arguments[0](context, text, position - 1, -1):
				return self.arguments[1](None, None, None)
		elif self.production == 'EXPR ::= SEQ ( "|" SEQ )*':
			m = None
			for arg in self.arguments:
				if arg.production.startswith('"'):
					continue
				if (r := arg(context, text, position, direction)) is not None:
					m = max(m, r) if m is not None else r
			return m
		elif self.production == 'SEQ ::= SIMPLE ( SIMPLE )*':
			m = 0
			#if direction == -1:
			#	m = 1
			for arg in self.arguments:
				if not 0 <= position + direction * m < len(context):
					return None
				#if arg.production.startswith('"'):
				#	continue
				if (r := arg(context, text, position + direction * m, direction)) is not None:
					m += r
				else:
					return None
			return m
		elif self.production == 'ATOM ::= "(" EXPR ")"':
			return self.arguments[1](context, text, position, direction)
		elif self.production == 'SET ::= "[" "^" EXPR "]"':
			# TODO
			return 0
			#return self.arguments[2](context, text, position, direction)
		elif self.production == 'SET ::= "[" EXPR "&" EXPR "]"':
			if self.arguments[1](context, text, position, direction) is not None and self.arguments[3](context, text, position, direction) is not None:
				return 0
			else:
				return None
		elif self.production == 'SET ::= "[" EXPR "-" EXPR "]"':
			if self.arguments[1](context, text, position, direction) is not None and self.arguments[3](context, text, position, direction) is None:
				return 0
			else:
				return None
		elif self.production == 'SIMPLE ::= ATOM "*"':
			m = 0
			while True:
				if not 0 <= position + direction * m < len(context):
					break
				if (r := self.arguments[0](context, text, position + direction * m, direction)) is not None:
					m += r
				else:
					break
			return m
		elif self.production == 'MOD ::= "\\p" "{" CHR_CLASS "}"':
			c = self.arguments[2](context, text, position, None)
			return 0
		elif self.production.startswith('"'):
			if direction == None:
				return self.arguments
			else:
				if context[position] == self.arguments:
					return 1
				else:
					return None
		elif len(self.arguments) == 1:
			return self.arguments[0](context, text, position, direction)
		else:
			raise NotImplementedError(self.production)


class ParsingError(Exception):
	def print_tree(self, level=0):
		yield level, self.args[0]
		for err in self.args[2]:
			yield from err.print_tree(level + 1)


class Parser:
	def __init__(self, start, grammar_source, Tree=ParseTree):
		self.start = start
		
		grammar = defaultdict(list)
		for nonterminal, production in self.analyze_grammar(grammar_source):
			grammar[nonterminal].append(tuple(production))
		
		self.grammar = dict(grammar)
		self.Tree = Tree
	
	def analyze_grammar(self, grammar_source):
		for rule in grammar_source.split('\n'):
			rule = rule.strip()
			if not rule:
				continue
			nonterminal, productions_source = rule.split('::=')
			nonterminal = nonterminal.strip()
			for production in self.analyze_productions(productions_source):
				yield nonterminal, production
	
	def analyze_productions(self, productions_source):
		string = False
		symbol = False
		production = []
		for n, ch in enumerate(productions_source):
			if string:
				if ch == '"':
					production.append(productions_source[m : n + 1])
					string = False
				continue
			elif symbol:
				if ch == ' ' or ch == '|':
					production.append(productions_source[m : n])
					symbol = False
			
			if ch == ' ':
				pass
			elif ch == '"':
				string = True
				m = n
			elif ch == '|':
				yield production
				production = []
			elif not symbol:
				symbol = True
				m = n
		
		if string:
			raise ValueError("Unterminated string")
		
		if symbol:
			production.append(productions_source[m:])
			symbol = False
		
		if production:
			yield production
	
	def __call__(self, source, start=None):
		tree, length = self.process_nonterminal(source, 0, start if start is not None else self.start)
		while length < len(source) and source[length]:
			if source[length] != ' ':
				raise ParsingError(f"Garbage at the end of input: {repr(source[length:])}.", "", [])
			length += 1
		return tree
	
	@cached
	def process_production(self, source, position, nonterminal, production):
		offset = 0
		zpos = 0
		while position < len(source) and source[position] == ' ':
			position += 1
			zpos += 1
		arguments = []
		
		m = None
		
		try:
			for n, symbol in enumerate(production):
				argument = None
				
				if symbol == '(':
					m = n
				
				elif symbol == ')*':
					while True:
						try:
							tree, length = self.process_production(source, position + offset, nonterminal, production[m + 1 : n])
						except ParsingError:
							break
						else:
							arguments.extend(tree.arguments)
							offset += length
					m = None
				
				elif m is not None:
					continue
				
				elif symbol.startswith('"') and symbol.endswith('"'): # terminal
					argument, s = self.process_terminal(source, position + offset, symbol)
				
				else:
					argument, s = self.process_nonterminal(source, position + offset, symbol) # nonterminal
				
				if argument is not None:
					arguments.append(argument)
					offset += s
		
		except ParsingError as error:
			raise ParsingError(f"Production {production} doesn't match source at position {position}: {repr(source[position : position + 32])}", production, [error])
		
		else:
			return self.Tree(nonterminal + ' ::= ' + ' '.join(production), tuple(arguments)), offset + zpos
	
	@cached
	def process_terminal(self, source, position, terminal):
		zpos = 0
		while position < len(source) and source[position] == ' ':
			position += 1
			zpos += 1
		
		length = len(terminal) - 2
		value = source[position:position + length]
		if value == terminal[1:-1]:
			return self.Tree(terminal, value), length + zpos
		else:
			raise ParsingError(f"Terminal {terminal} doesn't match source at position {position}: {repr(value)}", terminal, [])
	
	@cached
	def prefixes(self, production):
		n = 0
		while production[n] == '(':
			 n += 1
		symbol = production[n]
		
		if symbol.startswith('"') and symbol.endswith('"'):
			return frozenset({symbol[1:-1]})
		else:
			pfx = set()
			for production in self.grammar[symbol]:
				pfx.update(self.prefixes(production))
			return frozenset(pfx)
	
	#def contents(self, production):
	#	pfx = set()
	#	for n, symbol in enumerate(production):
	#		if not n: continue
	#		pfx.update(self.prefixes(symbol)
	
	@cached
	def process_nonterminal(self, source, position, nonterminal):
		sp = 0
		while position + sp < len(source) and source[position + sp] == ' ':
			sp += 1
		errors = []
		results = {}
		for production in self.grammar[nonterminal]:
			#print(production, self.prefixes(production), repr(source[sp:]))
			if not any(source[position + sp : position + sp + len(_pfx)] == _pfx for _pfx in self.prefixes(production)): continue
			#print("found:", nonterminal, production)
			try:
				tree, length = self.process_production(source, position, nonterminal, production)
			except ParsingError as error:
				errors.append(error)
			else:
				results[length] = tree
		
		if results:
			length = max(results.keys())
			return results[length], length
		
		raise ParsingError(f"Nonterminal {nonterminal} doesn't match source at position {position}: {repr(source[position:position + 32])}", nonterminal, errors)


class TextFormat:
	def create_document(self, data:bytes, mime_type):
		if mime_type == 'text/plain':
			return data.decode('utf-8')
		
		elif mime_type == 'application/octet-stream':
			return data
		
		else:
			return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_text_document(document):
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_text_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			decoded = document.encode('utf-8')
			fileobj.write(decoded)
			return fileobj
		else:
			return NotImplemented
	
	def is_text_document(self, document):
		return isinstance(document, str)
	
	def scan_document_links(self, document):
		if self.is_text_document(document):
			return []
		else:
			return NotImplemented
	
	"Unicode line breaking classes for various character ranges."
	__unicode_line_breaking_class = {
		'AI': [range(0x2780, 0x2794), {0x24ea}],
		'AK': [range(0x1b05, 0x1b34), range(0x1b45, 0x1b4d), range(0xa984, 0xa9b3), range(0x11005, 0x11038), range(0x11071, 0x11073), range(0x11305, 0x1130d), range(0x1130f, 0x11311), range(0x11313, 0x11329), range(0x1132a, 0x11331), range(0x11332, 0x11334), range(0x11335, 0x1133a), range(0x11360, 0x11362), range(0x11f04, 0x11f11), range(0x11f12, 0x11f34), {0x11075}],
		'AL': [range(0x600, 0x605), range(0x2061, 0x2065), {0x110bd, 0x6dd, 0x70f}],
		'AP': [range(0x11003, 0x11005), {0x11f02}],
		'AS': [range(0x1b50, 0x1b5a), range(0x1bc0, 0x1be6), range(0xa9d0, 0xa9da), range(0xaa00, 0xaa29), range(0xaa50, 0xaa5a), range(0x11066, 0x11070), range(0x1135e, 0x11360), range(0x11950, 0x1195a), range(0x11ee0, 0x11ef2), range(0x11f50, 0x11f5a), {0x11350}],
		'BA': [range(0x2e0e, 0x2e16), range(0x11ef7, 0x11ef9), range(0xaa40, 0xaa43), range(0xaa44, 0xaa4c), {0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x3000, 0x2008, 0x2009, 0x200a, 0x9, 0x1804, 0x1805, 0x10a57, 0xa60d, 0x2010, 0xa60f, 0x2012, 0x2013, 0x2e17, 0x2e19, 0x2027, 0x2e2a, 0x2e2b, 0x2e2c, 0x2e2d, 0x2e30, 0x1c3b, 0x1c3c, 0x1c3d, 0x1c3e, 0x1c3f, 0x104a, 0x104b, 0x10a50, 0x10a51, 0x10a52, 0x10a53, 0x10a54, 0x10a55, 0x2056, 0x10a56, 0x2058, 0x2059, 0x205a, 0x205b, 0xe5a, 0xaa5d, 0xaa5e, 0x205d, 0x205f, 0x205e, 0xe5b, 0xaa5f, 0x12470, 0x7c, 0x1c7e, 0x1c7f, 0x1680, 0xad, 0xa8ce, 0xa8cf, 0x16eb, 0x16ec, 0x16ed, 0x11ef2, 0x2cfa, 0x2cfb, 0x2cfc, 0x2cff, 0x10100, 0x10101, 0x10102, 0xf0b, 0x1091f, 0xa92e, 0xa92f, 0xf34, 0x1735, 0x1736, 0x1133d, 0x1b5a, 0x1b5b, 0x1b5d, 0x1b5e, 0x1b5f, 0x1b60, 0x1361, 0x1135d, 0x964, 0x965, 0xf7f, 0xf85, 0x58a, 0x1039f, 0x5be, 0xfbe, 0xfbf, 0xa9cf, 0x103d0, 0xfd2, 0x17d4, 0x17d5, 0x17d8, 0x17da}],
		'BB': [{0xf01, 0xf02, 0xf03, 0xf04, 0xf06, 0xf07, 0x1806, 0xf09, 0xf0a, 0xb4, 0x2c8, 0x2cc, 0xfd0, 0xfd1, 0xfd3, 0x2df, 0xa874, 0xa875, 0x1ffd}],
		'B2': [{0x2014}],
		'BK': [{0x2028, 0x2029, 0xb, 0xc}],
		'CB': [{0xfffc}],
		'CJ': [range(0xff67, 0xff71), {0x3041, 0x30a1, 0x3043, 0x30a3, 0x3045, 0x30a5, 0x30fc}],
		'CL': [range(0x3001, 0x3003), {0xff61, 0xff64, 0xff0c, 0xff0e, 0xfe10, 0xfe11, 0xfe12, 0xfe50, 0xfe52}],
		'CM': [],
		'CP': [{0x29, 0x2e56, 0x2e58, 0x2e5a, 0x2e5c, 0x5d}],
		'CR': [{0xd}],
		'EB': [{0x1f478, 0x1f6b4, 0x1f466}],
		'EM': [range(0x1f3fb, 0x1f400)],
		'EX': [{0x21, 0xff01, 0x5c6, 0x61f, 0xf0d, 0x6d4, 0xff1f, 0x7f9, 0x61b, 0x61e, 0x3f}],
		'GL': [range(0x13430, 0x13437), range(0x13439, 0x1343c), range(0x35c, 0x363), {0xa0, 0x16fe4, 0x2007, 0xf08, 0xf0c, 0x180e, 0x202f, 0x34f, 0x2011, 0xf12, 0x1107f}],
		'H2': [],
		'H3': [],
		'HY': [{0x2d}],
		'ID': [range(0x2e80, 0x3000), range(0x3040, 0x30a0), range(0x30a2, 0x30fb), range(0x3400, 0x4dc0), range(0x4e00, 0xa000), range(0xf900, 0xfb00), range(0x3130, 0x3190)],
		'HL': [],
		'IN': [{0xfe19, 0x2024, 0x2025, 0x2026}],
		'IS': [{0x2044, 0x589, 0x2c, 0x60c, 0x2e, 0x60d, 0x7f8, 0x3a, 0x3b, 0x37e}],
		'JL': [],
		'JT': [],
		'JV': [],
		'LF': [{0xa}],
		'NL': [{0x85}],
		'NS': [range(0x309b, 0x309f), range(0x30fd, 0x30ff), range(0xfe54, 0xfe56), range(0xff1a, 0xff1c), range(0xff9e, 0xffa0), {0x30a0, 0x3005, 0xff65, 0x2047, 0x2048, 0x2049, 0x301c, 0x303c, 0x30fb, 0xfe10, 0xfe13, 0x17d6, 0x303b, 0x203c, 0x203d}],
		'NU': [{0x66b, 0x66c}],
		'OP': [{0x2e18, 0xa1, 0xbf}],
		'PO': [range(0x2032, 0x2038), {0xffe0, 0xa2, 0x2103, 0x25, 0xff05, 0x20a7, 0x2109, 0x66a, 0x60b, 0xfe6a, 0xb0, 0x2030, 0x2031, 0xfdfc}],
		'PR': [{0x2b, 0xb1, 0x2212, 0x2213, 0x2116, 0x5c}],
		'QU': [range(0x2e00, 0x2e02), range(0x2e06, 0x2e09), {0x22, 0x27, 0x2e0b, 0x275b, 0x275c, 0x275d, 0x275e}],
		'RI': [range(0x1f1e6, 0x1f200)],
		'SA': [range(0xe00, 0xe80), range(0xe80, 0xf00), range(0x1000, 0x10a0), range(0x1780, 0x1800), range(0x1950, 0x1980), range(0x1980, 0x19e0), range(0x1a20, 0x1ab0), range(0xa9e0, 0xaa00), range(0xaa60, 0xaa80), range(0xaa80, 0xaae0), range(0x11700, 0x11740)],
		'SG': [],
		'SP': [{0x20}],
		'SY': [{0x2f}],
		'VF': [range(0x1bf2, 0x1bf4)],
		'VI': [{0xa9c0, 0x11f42, 0x1b44, 0x11046, 0x1134d}],
		'WJ': [{0x2060, 0xfeff}],
		'XX': [],
		'ZW': [{0x200b}],
		'ZWJ': [{0x200d}]
	}
	
	@cached
	def unicode_line_break_class(self, character):
		"Return Unicode line break class as defined here: https://www.unicode.org/reports/tr14/"
		
		if len(character) != 1:
			raise ValueError("Character must be a 1-char string.")
		codepoint = ord(character)
		for category, ranges in self.__unicode_line_breaking_class.items():
			if any((codepoint in _range) for _range in ranges):
				return category
		
		if self.unicode_category(character) in {'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Sm', 'Sk', 'So', 'Nl', 'No', 'Pc', 'Pd', 'Po'}:
			return 'AL'
		elif self.unicode_category(character) in {'Pf', 'Pi'}:
			return 'QU'
		
		# TODO: support other characters
		
		raise NotImplementedError(f"The character {repr(character)} ({hex(codepoint)}) does not belong to any line break class.")
	
	@cached
	def unicode_category(self, character):
		"Return Unicode character category."
		
		if len(character) != 1:
			raise ValueError("Character must be a 1-char string.")
		return unicodedata.category(character)
	
	"Grammar for line breaking rules."
	__line_break_grammar = '''
		RULE ::= EXPR OP | OP EXPR | EXPR OP EXPR
		OP ::= "!" | "×" | "÷"
		
		EXPR ::= SEQ ( "|" SEQ )*
		SEQ ::= SIMPLE ( SIMPLE )*
		SIMPLE ::= ATOM "*" | ATOM "+" | ATOM
		ATOM ::= "(" EXPR ")" | SET | MOD
		
		SET ::= "[" EXPR "&" EXPR "]" | "[" EXPR "-" EXPR "]" | "[" "^" EXPR "]"
		MOD ::= BRK_CLASS | "\\p" "{" CHR_CLASS "}" | "$EastAsian" | "[◌]" | "sot" | "eot"
		
		BRK_CLASS ::= ''' + " | ".join("\"" + _cat + "\"" for _cat in __unicode_line_breaking_class.keys()) + '''
		CHR_CLASS ::= "Pi" | "Pf" | "Cn" | "Extended_Pictographic"
	'''
	
	"Parser of line breaking rules grammar."
	__line_break_parser = Parser('RULE', __line_break_grammar)
	
	"Line breaking rules, converted to syntax trees (callable)."
	__line_break_rules = list(map(__line_break_parser, [
		'sot ×',
		'! eot',
		'BK !',
		'CR × LF',
		'CR !',
		'LF !',
		'NL !',
		'× ( BK | CR | LF | NL )',
		'× SP',
		'× ZW',
		'ZW SP* ÷',
		'ZWJ ×',
		'× WJ',
		'WJ ×',
		'GL ×',
		'[^SP BA HY] × GL',
		'× CL',
		'× CP',
		'× EX',
		'× SY',
		'OP SP* ×',
		'(sot | BK | CR | LF | NL | OP | QU | GL | SP | ZW) [\\p{Pi}&QU] SP* ×',
		'× [\\p{Pf}&QU] ( SP | GL | WJ | CL | QU | CP | EX | IS | SY | BK | CR | LF | NL | ZW | eot)',
		'(CL | CP) SP* × NS',
		'B2 SP* × B2',
		'SP ÷',
		'× [ QU - \\p{Pi} ]',
		'[ QU - \\p{Pf} ] ×',
		'÷ CB',
		'CB ÷',
		'× BA',
		'× HY',
		'× NS',
		'BB ×',
		'HL (HY | [ BA - $EastAsian ]) × [^HL]',
		'SY × HL',
		'× IN',
		'(AL | HL) × NU',
		'NU × (AL | HL)',
		'PR × (ID | EB | EM)',
		'(ID | EB | EM) × PO',
		'(PR | PO) × (AL | HL)',
		'(AL | HL) × (PR | PO)',
		'NU ( SY | IS )* CL × PO',
		'NU ( SY | IS )* CP × PO',
		'NU ( SY | IS )* CL × PR',
		'NU ( SY | IS )* CP × PR',
		'NU ( SY | IS )*  × PO',
		'NU ( SY | IS )*  × PR',
		'PO × OP NU',
		'PO × OP IS NU',
		'PO × NU',
		'PR × OP NU',
		'PR × OP IS NU',
		'PR × NU',
		'HY × NU',
		'IS × NU',
		'NU ( SY | IS )* × NU',
		'JL × (JL | JV | H2 | H3)',
		'(JV | H2) × (JV | JT)',
		'(JT | H3) × JT',
		'(JL | JV | JT | H2 | H3) × PO',
		'PR × (JL | JV | JT | H2 | H3)',
		'(AL | HL) × (AL | HL)',
		'AP × (AK | [◌] | AS)',
		'(AK | [◌] | AS) × (VF | VI)',
		'(AK | [◌] | AS) VI × (AK | [◌])',
		'(AK | [◌] | AS) × (AK | [◌] | AS) VF',
		'IS × (AL | HL)',
		'(AL | HL | NU) × [OP-$EastAsian]',
		'[CP-$EastAsian] × (AL | HL | NU)',
		'sot (RI RI)* RI × RI',
		'[^RI] (RI RI)* RI × RI',
		'EB × EM',
		'[\\p{Extended_Pictographic}&\\p{Cn}] × EM'
	]))
	
	def __text_line_break_classes(self, text):
		"Yield a series of line breaking classes for the given text. Prepends 'sot' at the beginning and appends 'eot' at the end, so the resulting stream is 2 elements longer than the text."
		for n, ch in enumerate(chain([None], text, [None])):
			if ch is None and n == 0:
				lbc = 'sot'
			elif ch is None and n != 0:
				lbc = 'eot'
			else:
				lbc = self.unicode_line_break_class(ch)
				if lbc in {'AI', 'SG', 'XX'}:
					lbc = 'AL'
				elif lbc == 'SA' and self.unicode_category(ch) in {'Mn', 'Mc'}:
					lbc = 'CM'
				elif lbc == 'SA':
					lbc = 'AL'
				elif lbc == 'CJ':
					lbc = 'NS'
			yield lbc
	
	class Separator(Enum):
		optional_break = ""
		mandatory_break = "\n"
		space = "\x20"
		thin_space = "\xa0"
		hyphen = "\u2009"
	
	@cached
	def line_breaks(self, text, lang=None):
		if lang is not None:
			hph = Pyphen(lang=lang)
		else:
			hph = None
		
		m = 1
		lbcs = list(self.__text_line_break_classes(document))
		for n in range(len(lbcs)):
			break_ = None
			for rule in self.__line_break_rules: # TODO: sort in the order of frequency
				if (b := rule(lbcs, text, n)) is not None:
					if b == '!': # mandatory break
						break_ = self.Separator.mandatory_break
					elif b == '×': # no break
						pass
					elif b == '÷': # optional break
						break_ = self.Separator.optional_break
					else:
						raise ValueError
					break
			else: # no rule matched = optional break
				break_ = self.Separator.optional_break
			
			if break_ and n > 0:
				word = text[m - 1 : n - 1]
				m = n
				k = 0
				for l, ch in enumerate(word):
					separator = None
					if ord(ch) in {0x20, 0xA0}: # space, non-breaking space
						separator = self.Separator.space
					elif ord(ch) == 0x2009: # thin space
						separator = self.Separator.thin_space
					elif ord(ch) in {0xd, 0xa, 0x85}: # carriage return, line feed, newline
						separator = True
					
					if separator:
						if l > k:
							if hph and ("\xad" not in word[k:l]):
								p = 0
								w = word[k:l]
								for q in hph.positions(w):
									yield w[p:q]
									p = q
									yield self.Separator.hyphen
									yield self.Separator.optional_break
								yield w[p:]
							else:
								yield word[k:l]
						k = l + 1
						if separator is not True:
							yield separator
				
				else:
					if k < len(word):
						if hph and ("\xad" not in word[k:]):
							p = 0
							w = word[k:]
							for q in hph.positions(w):
								yield w[p:q]
								p = q
								yield self.Separator.hyphen
								yield self.Separator.optional_break
							yield w[p:]
						else:
							yield word[k:]
				
				if break_ is not True:
					yield break_
	
	def measure_text(self, stream, ctx, width, callback):
		width_current = 0
		line = []
		unbreakable = []
		for token in stream:
			added = 0
			
			if token == self.Separator.space:
				if unbreakable:
					line.append("".join(unbreakable))
					added += 1
					unbreakable.clear()
				line.append("\x20")
				added += 1
			elif token == self.Separator.thin_space:
				if unbreakable:
					line.append("".join(unbreakable))
					added += 1
					unbreakable.clear()
				line.append("\u2009")
				added += 1
			elif token == self.Separator.hyphen:
				unbreakable.append("\xad")
			elif isinstance(token, str):
				unbreakable.append(token)
			elif token in {self.Separator.mandatory_break, self.Separator.optional_break}:
				if unbreakable:
					line.append("".join(unbreakable))
					added += 1
					unbreakable.clear()
			else:
				raise ValueError
			
			break_ = False
			if token == self.Separator.mandatory_break:
				break_ = True
			else:
				width_added = 0
				hyphen = False
				for n in range(added):
					word = line[-added + n]
					if n == added - 1 and word.endswith("\xad"):
						word = word.replace("\xad", "") + "-"
						hyphen = True
					else:
						word = word.replace("\xad", "")
					if callback: callback(Escape.begin_measure, word)
					width_added += ctx.text_extents(word).x_advance
					if callback: callback(Escape.end_measure, word)
				width_current += width_added

				##print(line)
				##text = "".join(line).strip("\x20\u2009").replace("\xad", "")
				#word = line[-1].replace("\xad", "") + ("-" if token.endswith("\xad") else "")
				#if callback: callback(Escape.begin_measure, word)
				#width_current = ctx.text_extents(text).x_advance

				#width_token = ctx.text_extents(word).x_advance
				#width_current += width_token
				
				#if callback: callback(Escape.end_measure, word)
				
				if width_current > width:
					break_ = True
				else:
					if hyphen:
						width_current -= width_added
						
						width_added = 0
						for n in range(added):
							word = line[-added + n]
							word = word.replace("\xad", "")
							if callback: callback(Escape.begin_measure, word)
							width_added += ctx.text_extents(word).x_advance
							if callback: callback(Escape.end_measure, word)
						width_current += width_added
			
			if break_:
				tail = []
				
				if line:
					while True:
						#print(len(line), line)
						broken_line = ("".join(line).strip("\x20\u2009") + ("-" if line[-1] and line[-1][-1] == "\xad" else "")).replace("\xad", "")
						if callback: callback(Escape.begin_measure, broken_line)
						width_broken = ctx.text_extents(broken_line).x_advance
						if callback: callback(Escape.end_measure, broken_line)
						if width_broken <= width or len(line) <= 1:
							break
						l = line.pop()
						tail.insert(0, l)
					
					yield broken_line
				
				yield "\n"
				
				width_current = 0				
				line.clear()
				line.extend(tail)
				width_added = 0
				for n in range(len(line)):
					word = line[n]
					word = word.replace("\xad", "")
					if callback: callback(Escape.begin_measure, word)
					width_added += ctx.text_extents(word).x_advance
					if callback: callback(Escape.end_measure, word)
				width_current += width_added
		
		if line:
			broken_line = ("".join(line).strip("\x20\u2009") + ("-" if line[-1] and line[-1][-1] == "\xad" else "")).replace("\xad", "")
			if broken_line:
				yield broken_line
				yield "\n"
	
	def draw_image(self, view, document, ctx, box, callback):
		if self.is_text_document(document):
			if callback: callback(Escape.begin_draw, document)
			
			width = box[2]
			height = box[3]
			
			ctx.set_font_size(16)
			ctx.select_font_face('sans-serif', cairo.FontSlant.NORMAL)
			ctx.translate(box[0], box[1])
			
			if callback: callback(Escape.begin_measure, None)
			extents = ctx.font_extents()
			if callback: callback(Escape.end_measure, None)
			
			line_height = extents[2]
			line_level = extents[0]
			n = 0
			if callback: callback(Escape.begin_line, n)
			for string in self.measure_text(self.line_breaks(document, 'en_GB'), ctx, width, callback):
				if string == "\n":
					if callback: callback(Escape.end_line, n)
					n += 1
					if callback: callback(Escape.begin_line, n)
				else:
					offset = 0
					for mt in finditer(r'(\S+|\s)', string):
						word = mt.group()
						print(repr(word))
						
						if callback: callback(Escape.begin_text, word)
						ctx.move_to(offset, n * line_height + line_level)
						ctx.text_path(word)
						if callback: callback(Escape.end_text, word)
						
						if callback: callback(Escape.begin_print, word)
						ctx.fill()
						if callback: callback(Escape.end_print, word)
						
						if callback: callback(Escape.begin_measure, word)
						offset += ctx.text_extents(word).x_advance
						if callback: callback(Escape.end_measure, word)

			if callback: callback(Escape.end_line, n)
			
			if callback: callback(Escape.end_draw, document)
		
		else:
			return NotImplemented
	
	def poke_image(self, view, document, ctx, box, px, py, callback):
		if self.is_text_document(document):
			if callback:
				callback(Escape.begin_poke, document)
				callback(Escape.end_poke, document)
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		"Return text dimensions."
		
		if self.is_text_document(document):
			return self.get_viewport_width(view), self.get_viewport_height(view)
		else:
			return NotImplemented
	
	def image_height_for_width(self, view, document, width):
		if self.is_text_document(document):
			surface = cairo.RecordingSurface(cairo.Content.COLOR, None)
			ctx = cairo.Context(surface)
			ctx.select_font_face(self.__text_font)
			ctx.set_font_size(self.__text_size)
			
			lines = 0
			line = []
			offset = 0
			for word in re_split(r'[\r\n\t ]+', document):
				extents = ctx.text_extents(word)
				offset += extents.x_advance + 3.4
				if offset > width:
					if line:
						lines += 1
					line.clear()
					line.append(word)
					offset = extents.x_advance
					if offset > width:
						lines += 1
						line.clear()
						offset = 0
				else:
					line.append(word)
			if line:
				lines += 1
			
			return lines * (self.__text_size + self.__text_spacing)
		
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height):
		if self.is_text_document(document):
			raise NotImplementedError
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	import sys
	test_type = 0
	if len(sys.argv) != 2:
		test_type = 0
	elif sys.argv[1] == '--test-1':
		test_type = 1
	elif sys.argv[1] == '--test-2':
		test_type = 2
	else:
		print("Unknown argument combination.")
		sys.exit(1)


if __debug__ and __name__ == '__main__' and test_type == 0:
	print("plain format")
	
	model = TextFormat()
	
	a = model.create_document(b'hello,void', 'text/plain')
	assert model.save_document(a).getvalue() == b'hello,void'


if __debug__ and __name__ == '__main__' and test_type in {1, 2}:
	from asyncio import run, get_running_loop
	
	import gi
	gi.require_version('Gtk', '4.0')
	gi.require_version('PangoCairo', '1.0')
	from gi.repository import Gtk
	
	from guixmpp.mainloop import *
	from guixmpp.domevents import *
	DOMEvent = Event
	
	loop_init()
	
	window = Gtk.Window()
	window.set_title("Plain text test widget")
	widget = Gtk.DrawingArea()
	window.set_child(widget)
	window.connect('close-request', lambda *_: loop_quit())
	
	model = TextFormat()
	
	if test_type == 1:
		document = model.create_document("""The Slaying of the Monster
By R. H. Barlow
and H. P. Lovecraft

Great was the clamour in Laen; for smoke had been spied in the Hills of the Dragon. That surely meant the Stirrings of the Monster—the Monster who spat lava and shook the earth as he writhed in its depths. And when the men of Laen spoke together they swore to slay the Monster and keep his fiery breath from searing their minaret-studded city and toppling their alabaster domes.
So it was that by torch-light gathered fully a hundred of the little people, prepared to battle the Evil One in his hidden fast-hold. With the coming of night they began marching in ragged columns into the foot-hills beneath the fulgent lunar rays. Ahead a burning cloud shone clearly through the purple dusk, a guide to their goal.
For the sake of truth it is to be recorded that their spirits sank low long ere they sighted the foe, and as the moon grew dim and the coming of the dawn was heralded by gaudy clouds they wished themselves more than ever at home, dragon or no dragon. But as the sun rose they cheered up slightly, and shifting their spears, resolutely trudged the remaining distance.
Clouds of sulphurous smoke hung pall-like over the world, darkening even the new-risen sun, and always replenished by sullen puffs from the mouth of the Monster. Little tongues of hungry flame made the Laenians move swiftly over the hot stones. “But where is the dragon??” whispered one—fearfully and hoping it would not accept the query as an invitation. In vain they looked—there was nothing solid enough to slay.
So shouldering their weapons, they wearily returned home and there set up a stone tablet graven to this effect—“BEING TROUBLED BY A FIERCE MONSTER THE BRAVE CITIZENS OF LAEN DID SET UPON IT AND SLAY IT IN ITS FEARFUL LAIR SAVING THE LAND FROM A DREADFUL DOOM.”
These words were hard to read when we dug that stone from its deep, ancient layers of encrusting lava.""".encode('utf-8'), 'text/plain')
	
	elif test_type == 2:
		document = model.create_document("""The City
By H. P. Lovecraft

	It was golden and splendid,
		That City of light;
	A vision suspended
		In deeps of the night;
A region of wonder and glory, whose temples were marble and white.

	I remember the season
		It dawn’d on my gaze;
	The mad time of unreason,
		The brain-numbing days
When Winter, white-sheeted and ghastly, stalks onward to torture and craze.

	More lovely than Zion
		It shone in the sky,
	When the beams of Orion
		Beclouded my eye,
Bringing sleep that was fill’d with dim mem’ries of moments obscure and gone by.

	Its mansions were stately
		With carvings made fair,
	Each rising sedately
		On terraces rare,
And the gardens were fragrant and bright with strange miracles blossoming there.

	The avenues lur’d me
		With vistas sublime;
	Tall arches assur’d me
		That once on a time
I had wander’d in rapture beneath them, and bask’d in the Halcyon clime.

	On the plazas were standing
		A sculptur’d array;
	Long-bearded, commanding,
		Grave men in their day—
But one stood dismantled and broken, its bearded face batter’d away.

	In that city effulgent
		No mortal I saw;
	But my fancy, indulgent
		To memory’s law,
Linger’d long on the forms in the plazas, and eyed their stone features with awe.

	I fann’d the faint ember
		That glow’d in my mind,
	And strove to remember
		The aeons behind;
To rove thro’ infinity freely, and visit the past unconfin’d.

	Then the horrible warning
		Upon my soul sped
	Like the ominous morning
		That rises in red,
And in panic I flew from the knowledge of terrors forgotten and dead. 

""".encode('utf-8'), 'text/plain')
	
	def render(widget, ctx, width, height):
		model.draw_image(widget, document, ctx, (0, 0, width, height), (lambda _reason, _param: True))
	
	widget.set_draw_func(render)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
	
	run(main())
