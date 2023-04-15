#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'CSSModel', 'CSSParser'


from collections import namedtuple
from enum import Enum


class CSSModel:
	def create_document(self, data, mime):
		if mime == 'text/css':
			return CSSParser().parse_css(data.decode('utf-8'))
		else:
			return NotImplemented
	
	def traverse_css(self, node, param, pre_function, post_function):
		if pre_function != None:
			node, param = pre_function(node, param)
		
		if hasattr(node, 'args'):
			children = []
			for child in node.args:
				child = self.traverse_css(child, param, pre_function, post_function)
				children.append(child)
		else:
			children = []
		
		if post_function != None:
			node = post_function(node, children)
		return node
	
	def print_css_tree(self, tree):
		def print_node(node, level):
			try:
				print(" " * level, node.name)
				return node, level + 1
			except AttributeError:
				print(" " * level, repr(node))
				return node, level
		
		self.traverse_css(tree, 0, print_node, None)
	
	def is_css_document(self, document):
		if hasattr(document, 'name') and hasattr(document, 'args'):
			return isinstance(document.name, str) and all(isinstance(_arg, str) or self.is_css_document(_arg) for _arg in document.args)
		else:
			return False
	
	def scan_css_syntax_errors(self, node):
		if hasattr(node, 'name') and hasattr(node, 'args'):
			if not isinstance(node.name, str):
				yield node
			
			for arg in node.args:
				yield from self.scan_css_syntax_errors(arg)
		
		elif not isinstance(node, str):
			yield node


class CSSParser:
	def parse_css(self, text):
		return self.build_block(self.build_lists(self.build_structure(self.lexer(self.StringStream(text)))))
	
	class StringStream:
		def __init__(self, s):
			self.s = s
			self.n = 0
		
		def prefix(self, n):
			return self.s[self.n : self.n+n]
		
		def shift(self, n):
			self.n += n
		
		def eof(self):
			return self.n >= len(self.s)
	
	class GeneratorStream:
		def __init__(self, g):
			self.g = g
			self.p = []
			self.e = False
		
		@staticmethod
		def join(p):
			return tuple(p)
		
		def prefix(self, n):
			if n <= len(self.p):
				return self.join(self.p[:n])
			else:
				try:
					for m in range(n - len(self.p)):
						self.p.append(next(self.g))
				except StopIteration:
					self.e = True
				return self.join(self.p[:n])
		
		def shift(self, n):
			self.prefix(n)
			del self.prefix[:n]
		
		def eof(self):
			return self.e
	
	LexerContext = Enum('LexerContext', 'comment quote dblquote variable identifier number whitespace hexnumber')
	
	def lexer(self, stream):
		context = None
		token = []
		
		while not stream.eof():
			if context == self.LexerContext.comment:
				if stream.prefix(2) == '*/':
					stream.shift(2)
					context = None
				else:
					stream.shift(1)
			
			elif context == self.LexerContext.quote:
				if stream.prefix(1) == '\\':
					stream.shift(1)
					token.append(stream.prefix(1))
					stream.shift(1)
				elif stream.prefix(1) == '\'':
					yield ''.join(['\''] + token + ['\''])
					token.clear()
					#yield '\''
					stream.shift(1)
					context = None
				else:
					token.append(stream.prefix(1))
					stream.shift(1)
			
			elif context == self.LexerContext.dblquote:
				if stream.prefix(1) == '\\':
					stream.shift(1)
					token.append(stream.prefix(1))
					stream.shift(1)
				elif stream.prefix(1) == '"':
					yield ''.join(['"'] + token + ['"'])
					token.clear()
					#yield '"'
					stream.shift(1)
					context = None
				else:
					token.append(stream.prefix(1))
					stream.shift(1)
			
			elif context == self.LexerContext.identifier:
				if ord('a') <= ord(stream.prefix(1)) <= ord('z') or ord('A') <= ord(stream.prefix(1)) <= ord('Z') or ord('0') <= ord(stream.prefix(1)) <= ord('9') or stream.prefix(1) in '_-':
					token.append(stream.prefix(1))
					stream.shift(1)
				else:
					yield ''.join(token)
					token.clear()
					context = None
			
			elif context == self.LexerContext.variable:
				if ord('a') <= ord(stream.prefix(1)) <= ord('z') or ord('A') <= ord(stream.prefix(1)) <= ord('Z') or ord('0') <= ord(stream.prefix(1)) <= ord('9') or stream.prefix(1) in '_-':
					token.append(stream.prefix(1))
					stream.shift(1)
				else:
					yield ''.join(['--'] + token)
					token.clear()
					context = None
			
			elif context == self.LexerContext.number:
				if ord('0') <= ord(stream.prefix(1)) <= ord('9') or stream.prefix(1) == '.':
					token.append(stream.prefix(1))
					stream.shift(1)
				else:
					yield ''.join(token)
					token.clear()
					context = None
			
			elif context == self.LexerContext.hexnumber:
				if ord('a') <= ord(stream.prefix(1)) <= ord('z') or ord('A') <= ord(stream.prefix(1)) <= ord('Z') or ord('0') <= ord(stream.prefix(1)) <= ord('9') or stream.prefix(1) in '_-':
					token.append(stream.prefix(1))
					stream.shift(1)
				else:
					yield ''.join(token)
					token.clear()
					context = None
			
			elif stream.prefix(2) == '/*':
				context = self.LexerContext.comment
				stream.shift(2)
			
			elif stream.prefix(1) == '\'':
				context = self.LexerContext.quote
				#yield '\''
				stream.shift(1)
			
			elif stream.prefix(1) == '\"':
				context = self.LexerContext.dblquote
				#yield '"'
				stream.shift(1)
			
			elif stream.prefix(2) == '--':
				context = self.LexerContext.variable
				#yield '--'
				stream.shift(2)
			
			elif ord('a') <= ord(stream.prefix(1)) <= ord('z') or ord('A') <= ord(stream.prefix(1)) <= ord('Z') or stream.prefix(1) in '_-':
				context = self.LexerContext.identifier
				token.append(stream.prefix(1))
				stream.shift(1)		
			
			elif ord('0') <= ord(stream.prefix(1)) <= ord('9'):
				context = self.LexerContext.number
				token.append(stream.prefix(1))
				stream.shift(1)
			
			elif stream.prefix(1) in ' \t\r\n':
				if context != self.LexerContext.whitespace:
					yield ' '
				context = self.LexerContext.whitespace
				stream.shift(1)
			
			elif stream.prefix(1) == '#':
				context = self.LexerContext.hexnumber
				yield '#'
				stream.shift(1)
			
			else:
				context = None
				yield stream.prefix(1)
				stream.shift(1)
	
	StyleNode = namedtuple('StyleNode', ['name', 'args'])
	
	ParserSymbol = Enum('ParserSymbol', 'curly square brace item')
	
	def build_structure(self, tokens):
		fence = []
		args = []
		stack = []
		
		for token in tokens:
			if token == '{':
				fence.append(self.ParserSymbol.curly)
				stack.append(args)
				args = []
			elif token == '(':
				fence.append(self.ParserSymbol.brace)
				stack.append(args)
				args = []
			elif token == '[':
				fence.append(self.ParserSymbol.square)
				stack.append(args)
				args = []
			elif token == '}':
				if fence:
					while fence[-1] != self.ParserSymbol.curly: # warning
						symbol = fence.pop()
						node = self.StyleNode(symbol, args)
						args = stack.pop()
						args.append(node)
					fence.pop()
					node = self.StyleNode(self.ParserSymbol.curly, args)
					args = stack.pop()
					args.append(node)
			elif token == ')':
				if fence:
					while fence[-1] != self.ParserSymbol.brace: # warning
						symbol = fence.pop()
						node = self.StyleNode(symbol, args)
						args = stack.pop()
						args.append(node)
					fence.pop()
					node = self.StyleNode(self.ParserSymbol.brace, args)
					args = stack.pop()
					args.append(node)
			elif token == ']':
				if fence:
					while fence[-1] != self.ParserSymbol.square: # warning
						symbol = fence.pop()
						node = self.StyleNode(symbol, args)
						args = stack.pop()
						args.append(node)
					fence.pop()
					node = self.StyleNode(self.ParserSymbol.square, args)
					args = stack.pop()
					args.append(node)
			else:
				args.append(token)
		
		while fence: # warning
			symbol = fence.pop()
			node = self.StyleNode(symbol, args)
			args = stack.pop()
			args.append(node)
		
		return self.StyleNode('stylesheet', args)
	
	def build_list(self, node):
		series = []
		args = []
		
		for arg in node.args:
			args.append(arg)
			
			if arg == ';' or (hasattr(arg, 'name') and arg.name == self.ParserSymbol.curly):
				self.strip_space(args)
				
				if args:
					series.append(self.StyleNode(self.ParserSymbol.item, args))
					args = []
		else:
			self.strip_space(args)
			
			if args:
				series.append(self.StyleNode(self.ParserSymbol.item, args))
		
		return self.StyleNode(node.name, series)
	
	def build_lists(self, node):
		if hasattr(node, 'name') and (node.name == 'stylesheet' or node.name == self.ParserSymbol.curly):
			return self.build_list(self.StyleNode(node.name, [self.build_lists(_arg) for _arg in node.args]))
		else:
			return node
	
	def build_block(self, node):
		children = []
		
		for child in node.args:
			if child.name != self.ParserSymbol.item: continue # warning
			
			if child.args[0] == '@':
				prelude = child.args[1:-1]
				self.strip_space(prelude)
				if not prelude:
					continue # warning
				
				rule_name = prelude[0]
				
				if rule_name in ['font-face', 'color-profile', 'counter-style', 'swash', 'annotation', 'ornaments', 'stylistic', 'styleset', 'character-variant', 'font-palette-values', 'page']:
					if child.args[-1].name == self.ParserSymbol.curly:
						children.append(self.StyleNode('atrule-style', [rule_name, self.parse_prelude(prelude), self.build_rules(child.args[-1])]))
					else:
						pass # warning
				elif rule_name in ['font-feature-values', 'font-palette-values', 'keyframes', 'layer', 'media', 'supports']:
					if child.args[-1].name == self.ParserSymbol.curly:
						children.append(self.StyleNode('atrule-block', [rule_name, self.parse_prelude(prelude), self.StyleNode('scope', self.build_block(child.args[-1]).args)]))
					else:
						pass # warning
				elif rule_name in ['charset', 'import',  'namespace']:
					if child.args[-1] == ';':
						children.append(self.StyleNode('atrule-simple', [rule_name, self.parse_prelude(prelude)]))
					else:
						pass # warning
				else:
					pass # warning
			
			else:
				#print(child.args)
				if child.args[-1].name == self.ParserSymbol.curly:
					children.append(self.StyleNode('style', [self.parse_selector(child.args[:-1]), self.build_rules(child.args[-1])]))
				else:
					pass # warning
		
		return self.StyleNode(node.name, children)
	
	def build_rules(self, node):
		children = []
		
		for child in node.args:
			if child.name != self.ParserSymbol.item: continue # warning
			
			colon = child.args.index(':')
			
			name = None
			for name_or_space in child.args[:colon]:
				if name_or_space == ' ':
					pass
				elif name == None:
					name = name_or_space
				else: # warning
					continue
			
			if name == None: # warning
				continue
			
			value = self.parse_values(child.args[colon + 1 : -1])
			
			if name.startswith('--'):
				children.append(self.StyleNode('var_decl', [name, value]))
			else:
				children.append(self.StyleNode('rule', [name, value]))
		
		return self.StyleNode('rules', children)
	
	def strip_space(self, tokens):
		try:
			while tokens[0] == ' ': del tokens[0]
			while tokens[-1] == ' ': del tokens[-1]
		except IndexError:
			pass
		
		n = 0
		while n < len(tokens):
			if tokens[n] == ' ':
				if space:
					del tokens[n]
				else:
					space = True
					n += 1
			else:
				space = False
				n += 1
	
	def parse_values(self, tokens):
		self.strip_space(tokens)
		
		result = []
		seq = []
		for token in tokens:
			if token in [' ', ',']:
				if not seq:
					pass
				elif len(seq) == 2 and hasattr(seq[1], 'name') and seq[1].name == self.ParserSymbol.brace:
					if seq[0] == 'var':
						result.append(self.StyleNode('var', seq[1].args))
					else:
						result.append(self.StyleNode('function', [seq[0], self.parse_arguments(seq[0], seq[1].args)]))
				else:
					result.append(self.StyleNode('value', seq))
				seq = []
			else:
				seq.append(token)
		else:
			if not seq:
				pass
			elif len(seq) == 2 and hasattr(seq[1], 'name') and seq[1].name == self.ParserSymbol.brace:
				if seq[0] == 'var':
					result.append(self.StyleNode('var', seq[1].args))
				else:
					result.append(self.StyleNode('function', [seq[0], self.parse_arguments(seq[0], seq[1].args)]))
			else:
				result.append(self.StyleNode('value', seq))
		
		return self.StyleNode('values', result)
	
	def parse_arguments(self, name, tokens): # TODO
		return self.StyleNode('arguments', tokens)
	
	def parse_prelude(self, tokens):
		at_rule = tokens[0]
		prelude = tokens[1:]
		
		self.strip_space(prelude)
		
		if at_rule == 'media':
			return self.parse_media_prelude(prelude)
		elif at_rule == 'import':
			return self.parse_values(prelude)
		elif at_rule == 'charset':
			return self.StyleNode('value', [prelude[0]])
		elif at_rule == 'namespace':
			return self.parse_values(prelude)
			#return self.StyleNode('value', [prelude[0], prelude[2]])
		else:
			return self.parse_other_prelude(prelude)
	
	def parse_media_prelude(self, tokens):
		self.strip_space(tokens)
		
		result = []
		args = []
		
		for token in tokens:
			if token == ',':
				self.strip_space(args)
				
				if args:
					result.append(self.parse_media_prelude_one(args))
					args = []
				else:
					pass # warning
			else:
				args.append(token)
		else:
			self.strip_space(args)
			
			if args:
				result.append(self.parse_media_prelude_one(args))
				args = []
		
		return self.StyleNode('prelude', result)
	
	def parse_media_prelude_one(self, tokens):
		self.strip_space(tokens)
		
		result = []
		args = []
		
		for token in tokens:
			if token == 'and':
				self.strip_space(args)
				
				if args:
					result.extend(self.parse_media_prelude_rules(args))
					args = []
			else:
				args.append(token)
		else:
			self.strip_space(args)
			
			if args:
				result.extend(self.parse_media_prelude_rules(args))
				args = []
		
		return self.StyleNode('media_test', result)
	
	def parse_media_prelude_rules(self, tokens):
		self.strip_space(tokens)
		
		result = []
		
		if hasattr(tokens[0], 'name') and tokens[0].name == self.ParserSymbol.brace:
			result.extend([self.StyleNode('media_property', _arg.args) for _arg in self.build_list(tokens[0]).args])
		else:
			result.append(self.StyleNode('media_type', [_token for _token in tokens if _token != ' ']))
		
		return result
	
	def parse_other_prelude(self, tokens): # TODO
		self.strip_space(tokens)
		
		return self.StyleNode('prelude', tokens)
	
	def parse_selector(self, tokens):
		self.strip_space(tokens)
		
		result = []
		args = []
		
		for token in tokens:
			if token == ',':
				self.strip_space(args)
				
				if args:
					result.append(self.parse_selector_seq(args))
					args = []
				else:
					pass # warning
			else:
				args.append(token)
		else:
			self.strip_space(args)
			
			if args:
				result.append(self.parse_selector_seq(args))
				args = []
		
		return self.StyleNode('selector', result)
	
	def parse_selector_seq(self, tokens):
		self.strip_space(tokens)
		
		result = []
		args = []
		
		for token in tokens:
			if token in ['>', '~', '+']:
				if args:
					result.append(self.parse_selector_single(args))
					args = []
				
				if result and hasattr(result[-1], 'name') and result[-1].name == 'path_operator' and result[-1].args[0] == ' ':
					result[-1] = self.StyleNode('path_operator', [token])
				else:
					result.append(self.StyleNode('path_operator', [token]))
			elif token == ' ':
				if args:
					result.append(self.parse_selector_single(args))
					args = []
				
				if result and not (hasattr(result[-1], 'name') and result[-1].name == 'path_operator'):
					result.append(self.StyleNode('path_operator', [' ']))
			else:
				args.append(token)
		else:
			if args:
				result.append(self.parse_selector_single(args))
				args = []
		
		return self.StyleNode('selector_seq', result)
	
	def parse_selector_single(self, tokens):
		result = []
		
		past = []
		for token in tokens:
			if token in ['#', '.', ':']:
				pass
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.brace:
				if result and result[-1].name == 'selector_pseudo_class':
					result[-1] = self.StyleNode('selector_pseudo_class_fn', [result[-1].args[0], self.parse_selector_function_args(':' + result[-1].args[0], token.args)])
				elif result and result[-1].name == 'selector_pseudo_element':
					result[-1] = self.StyleNode('selector_pseudo_element_fn', [result[-1].args[0], self.parse_selector_function_args('::' + result[-1].args[0], token.args)])
				else:
					pass # warning
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.square:
				result.append(self.StyleNode('selector_attr', token.args))
			elif not past:
				result.append(self.StyleNode('selector_tag', [token]))
			elif token == '*':
				pass # warning
			elif token == '%':
				if past and isinstance(past[-1], str) and past[-1] not in ['#', '.', ':'] and result and hasattr(result[-1], 'name') and result[-1].name == 'selector_tag':
					result[-1] = self.StyleNode('selector_percentage', result[-1].args)
				else:
					pass # warning
			elif past[-1] == '.':
				result.append(self.StyleNode('selector_class', [token]))
			elif past[-1] == '#':
				result.append(self.StyleNode('selector_id', [token]))
			elif past[-1] == ':' and (len(past) == 1 or past[-2] != ':'):
				result.append(self.StyleNode('selector_pseudo_class', [token]))
			elif len(past) >= 2 and past == [':', ':']:
				result.append(self.StyleNode('selector_pseudo_element', [token]))
			else:
				pass # warning
			
			past.append(token)
			if len(past) > 2:
				del past[0]
		
		return self.StyleNode('selector_single', result)
	
	def parse_selector_function_args(self, name, tokens):
		if name in [':is', ':has', ':with']:
			node = self.parse_selector_seq(tokens)
			return self.StyleNode('arguments', node.args)
		else: # TODO
			return self.StyleNode('arguments', tokens)


if __name__ == '__main__':
	print("css model")
	
	from pathlib import Path
	model = CSSModel()
	tree = model.create_document(Path('gfx/so-primary.css').read_bytes(), 'text/css')
	
	for node in model.scan_css_syntax_errors(tree):
		print(node)
	
	#assert model.is_css_document(tree)
	#model.print_css_tree(tree)

