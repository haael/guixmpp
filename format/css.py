#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'CSSFormat', 'CSSParser', 'CSSDocument'


from collections import namedtuple, defaultdict
from enum import Enum
from itertools import chain


class CSSFormat:
	def create_document(self, data, mime):
		if mime == 'text/css':
			return CSSDocument(CSSParser().parse_css(data.decode('utf-8')))
		else:
			return NotImplemented
	
	def is_css_document(self, document):
		return hasattr(document, 'css_tree')
	
	def scan_document_links(self, document):
		if self.is_css_document(document):
			return chain(
				document.scan_imports(),
				document.scan_urls()
			)
		else:
			return NotImplemented


class StyleNode(namedtuple('_StyleNode', ['name', 'args'])):
	def __repr__(self):
		return f"<{self.__class__.__qualname__} {repr(self.name)} @{hex(id(self))}>"


class CSSDocument:
	def __init__(self, arg):
		try:
			self.css_tree = arg.css_tree
			return
		except AttributeError:
			pass
		
		if hasattr(arg, 'name') and hasattr(arg, 'args'):
			self.css_tree = arg
			return
		
		self.css_tree = CSSParser().parse_css(arg.decode('utf-8'))
	
	def traverse(self, node, param, pre_function, post_function):
		if pre_function != None:
			node, param = pre_function(node, param)
		
		if hasattr(node, 'args'):
			children = []
			for child in node.args:
				child = self.traverse(child, param, pre_function, post_function)
				children.append(child)
		else:
			children = []
		
		if post_function != None:
			node = post_function(node, children)
		return node
	
	def is_valid(self, document=None):
		if document is None:
			return self.is_valid(self.css_tree)
		
		if hasattr(document, 'name') and hasattr(document, 'args'):
			return isinstance(document.name, str) and all(isinstance(_arg, str) or self.is_valid(_arg) for _arg in document.args)
		else:
			return False
	
	def print_tree(self, tree=None, level=0):
		def print_node(node, level):
			try:
				if not isinstance(node.name, str):
					print(" " * level, node.name, "!!!")
				else:
					print(" " * level, node.name)
				return node, level + 1
			except AttributeError:
				if not isinstance(node, str):
					print(" " * level, repr(node), "!!!")
				else:
					print(" " * level, repr(node))
				return node, level
		
		if node is None:
			self.traverse(self.css_tree, level, print_node, None)
		else:
			self.traverse(tree, level, print_node, None)
	
	def tree_contains(self, tree, target):
		def catch(node, results):
			if node is target:
				return True
			else:
				return any(results)
		
		return self.traverse(tree, None, None, catch)
	
	def print_context(self, target, tree=None, level=0):
		def print_node(node, level):
			if node is target:
				self.print_tree(target, level)
			elif hasattr(node, 'name') and self.tree_contains(node, target):
				print(" " * level, node.name)
			return node, level + 1
		
		if tree is None:
			self.traverse(self.css_tree, level, print_node, None)
		else:
			self.traverse(tree, level, print_node, None)			
	
	def scan_syntax_errors(self, node=None):
		if node is None:
			yield from self.scan_syntax_errors(self.css_tree)
			return
		
		if hasattr(node, 'name') and hasattr(node, 'args'):
			if not isinstance(node.name, str):
				yield node
			
			for arg in node.args:
				yield from self.scan_syntax_errors(arg)
		
		elif not isinstance(node, str):
			yield node
	
	def scan_imports(self):
		for node in self.css_tree.args:
			try:
				if all([
					node.name == 'atrule-simple',
					node.args[0] == 'import',
					node.args[1].name == 'prelude',
					node.args[1].args[0].name == 'url'
				]):
					yield node.args[1].args[0].args[0]
			except (AttributeError, IndexError):
				pass
	
	def match_element(self, xml_element, media_test, pseudoclass_test, default_namespace): # TODO
		if default_namespace is None:
			namespace = ''
		else:
			namespace = '{' + default_namespace + '}'
		
		def print_node(node, ancestors):
			print(ancestors + [node.name if hasattr(node, 'name') else node])
			return node, ancestors + [node.name if hasattr(node, 'name') else None]
		
		def walk_node(node, args):
			if isinstance(node, str):
				return node
			elif node.name == 'path-operator':
				return args[0]
			elif node.name == 'selector-tag':
				if args[0] == '*':
					return lambda _node: True
				else:
					return lambda _node: _node.tag == f"{namespace}{args[0]}"
			elif node.name == 'selector-class':
				return lambda _node: ('class' in _node.attrib) and (_node.attrib['class'] == args[0])
			elif node.name == 'selector-pseudo-class':
				return lambda _node: pseudoclass_test(args[0], _node)
			elif node.name == 'selector-attr':
				if args[1] == '=':
					return lambda _node: (args[0] in _node.attrib) and (_node.attrib[args[0]] == args[2])
				else:
					raise NotImplementedError("Attribute selector operator: " + repr(args[1]))
			elif node.name == 'selector-id':
				return lambda _node: ('id' in _node.attrib) and (_node.attrib['id'] == args[0])
			elif node.name == 'selector-single':
				assert all(callable(_check) for _check in args), str(args)
				return lambda _node: all(_check(_node) for _check in args)
			elif node.name == 'selector-seq':
				if len(args) == 1:
					return args[0](xml_element)
				elif len(args) == 3 and args[1] == ' ':
					if not args[2](xml_element):
						return False
					target = xml_element.getparent()
					while target is not None:
						if args[0](target):
							return True
						target = target.getparent()
					return False
				#raise NotImplementedError("Implement path operators. {args}")
				print("Implement path operators", args)
				return False
			elif node.name == 'function':
				return args[0] + '(' + ', '.join(args[1]) + ')'
			elif node.name == 'url':
				assert len(args) == 1
				return f'url({args[0]})'
			elif node.name == 'arguments':
				return args
			elif node.name == 'value':
				return ''.join(args)
			elif node.name == 'values':
				return ', '.join(args)
			elif node.name == 'rule':
				return args
			elif node.name == 'rules':
				return dict(args)
			elif node.name == 'selector':
				return any(args)
			elif node.name == 'style':
				assert isinstance(args[1], dict)
				if args[0]:
					return args[1]
				else:
					return {}
			elif node.name == 'stylesheet':
				result = {}
				for style in args:
					if not isinstance(style, dict):
						#print("unsupported style spec:", style)
						continue
					result.update(style)
				return result
			else:
				return node
		
		return self.traverse(self.css_tree, [], None, walk_node)
	
	def scan_urls(self):
		result = []
		
		def walk_node(node, ancestors):
			if ancestors == ['stylesheet', 'style', 'rules', 'rule', 'values', 'url'] and isinstance(node, str):
				result.append(node)
			
			return node, ancestors + [node.name if hasattr(node, 'name') else None]
		
		self.traverse(self.css_tree, [], walk_node, None)
		
		return result


class CSSParser:
	def parse_css(self, text):
		return self.build_features(self.build_block(self.build_lists(self.build_structure(self.lexer(self.StringStream(text))))))
	
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
						node = StyleNode(symbol, args)
						args = stack.pop()
						args.append(node)
					fence.pop()
					node = StyleNode(self.ParserSymbol.curly, args)
					args = stack.pop()
					args.append(node)
			elif token == ')':
				if fence:
					while fence[-1] != self.ParserSymbol.brace: # warning
						symbol = fence.pop()
						node = StyleNode(symbol, args)
						args = stack.pop()
						args.append(node)
					fence.pop()
					node = StyleNode(self.ParserSymbol.brace, args)
					args = stack.pop()
					args.append(node)
			elif token == ']':
				if fence:
					while fence[-1] != self.ParserSymbol.square: # warning
						symbol = fence.pop()
						node = StyleNode(symbol, args)
						args = stack.pop()
						args.append(node)
					fence.pop()
					node = StyleNode(self.ParserSymbol.square, args)
					args = stack.pop()
					args.append(node)
			else:
				args.append(token)
		
		while fence: # warning
			symbol = fence.pop()
			node = StyleNode(symbol, args)
			args = stack.pop()
			args.append(node)
		
		return StyleNode('stylesheet', args)
	
	def build_list(self, node):
		series = []
		args = []
		
		for arg in node.args:
			args.append(arg)
			
			if arg == ';' or (hasattr(arg, 'name') and arg.name == self.ParserSymbol.curly):
				self.strip_space(args)
				
				if args:
					series.append(StyleNode(self.ParserSymbol.item, args))
					args = []
		else:
			self.strip_space(args)
			
			if args:
				series.append(StyleNode(self.ParserSymbol.item, args))
		
		return StyleNode(node.name, series)
	
	def build_lists(self, node):
		if hasattr(node, 'name') and (node.name == 'stylesheet' or node.name == self.ParserSymbol.curly):
			return self.build_list(StyleNode(node.name, [self.build_lists(_arg) for _arg in node.args]))
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
						children.append(StyleNode('atrule-style', [rule_name, self.parse_prelude(prelude), self.build_rules(child.args[-1])]))
					else:
						pass # warning
				elif rule_name in ['font-feature-values', 'font-palette-values', 'keyframes', 'layer', 'media', 'supports']:
					if child.args[-1].name == self.ParserSymbol.curly:
						children.append(StyleNode('atrule-block', [rule_name, self.parse_prelude(prelude), StyleNode('scope', self.build_block(child.args[-1]).args)]))
					else:
						pass # warning
				elif rule_name in ['charset', 'import',  'namespace']:
					if child.args[-1] == ';':
						children.append(StyleNode('atrule-simple', [rule_name, self.parse_prelude(prelude)]))
					else:
						pass # warning
				else:
					pass # warning
			
			else:
				#print(child.args)
				if child.args[-1].name == self.ParserSymbol.curly:
					children.append(StyleNode('style', [self.parse_selector(child.args[:-1]), self.build_rules(child.args[-1])]))
				else:
					pass # warning
		
		return StyleNode(node.name, children)
	
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
			
			value = self.parse_values(child.args[colon + 1 : (-1 if child.args[-1] == ';' else None)])
			
			if name.startswith('--'):
				children.append(StyleNode('var-decl', [name, value]))
			elif value.args[-1].name == 'importance':
				children.append(StyleNode('rule', [name, StyleNode(value.name, value.args[:-1]), value.args[-1]]))
			else:
				children.append(StyleNode('rule', [name, value]))
		
		return StyleNode('rules', children)
	
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
	
	@staticmethod
	def __remove_optional_quotes(s):
		if s[0] == '"' and s[-1] == '"':
			return s[1:-1]
		elif s[0] == '\'' and s[-1] == '\'':
			return s[1:-1]
		else:
			return s
	
	def parse_values(self, tokens):
		self.strip_space(tokens)
		
		result = []
		seq = []
		for token in tokens + [',']:
			if token in [' ', ',', '!']:
				if not seq:
					pass
				elif len(seq) == 2 and hasattr(seq[1], 'name') and seq[1].name == self.ParserSymbol.brace:
					if seq[0] == 'var':
						result.append(StyleNode('var', seq[1].args))
					elif seq[0] == 'url':
						result.append(StyleNode('url', [self.__remove_optional_quotes(''.join(seq[1].args))]))
					else:
						result.append(StyleNode('function', [seq[0], self.parse_arguments(seq[0], seq[1].args)]))
				else:
					result.append(self.parse_expression(seq))
				seq = []
				
				if token == '!':
					seq.append(token)
			else:
				seq.append(token)
		
		assert not seq
		return StyleNode('values', result)
	
	def parse_expression(self, tokens):
		self.strip_space(tokens)
		
		op = False
		
		result = []
		ts = []
		for token in tokens:
			if token in [' ', '\t', '\r', '\n']:
				pass
			elif token in ['+', '-', '*', '/']:
				result.append(self.parse_expression(ts))
				result.append(StyleNode('infix-operator', [token]))
				ts = []
				op = True
			elif isinstance(token, str) and ts and isinstance(ts[-1], str) and (ts[-1][-1] in '0123456789.#'): # FIXME: correct number parsing
				ts[-1] = ts[-1] + token
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.brace and ts:
				if ts[-1] == 'var':
					return StyleNode('var', token.args)
				elif ts[-1] == 'url':
					result.append(StyleNode('url', [self.__remove_optional_quotes(''.join(token.args))]))
				else:
					return StyleNode('function', [ts[-1], self.parse_arguments(ts[-1], token.args)])
			else:
				ts.append(token)
		
		if result:
			if ts:
				result.append(self.parse_expression(ts))
		else:
			result = ts
		
		if op:
			return StyleNode('expression', result)
		elif len(result) == 1 and hasattr(result[0], 'name') and result[0].name == self.ParserSymbol.brace:
			return self.parse_expression(result[0].args)
		elif len(result) == 2 and result[0] == '!':
			return StyleNode('importance', [result[1]])
		elif len(result) == 1:
			return StyleNode('value', result)
		else:
			return StyleNode('multivalue', result)
	
	def parse_arguments(self, name, tokens):
		result = []
		ts = []
		for token in tokens:
			if token == ',':
				result.append(self.parse_expression(ts))
				ts = []
			else:
				ts.append(token)
		if ts:
			result.append(self.parse_expression(ts))
		
		for n, r in enumerate(result):
			if hasattr(r, 'name') and r.name == 'multivalue' and r.args[1] == '=':
				if len(r.args) == 3:
					result[n] = StyleNode('named-argument', [r.args[0], StyleNode('value', r.args[2])])
				else:
					result[n] = StyleNode('named-argument', [r.args[0], StyleNode('multivalue', r.args[2:])])
		
		return StyleNode('arguments', result)
	
	def parse_prelude(self, tokens):
		at_rule = tokens[0]
		prelude = tokens[1:]
		
		self.strip_space(prelude)
		
		if at_rule == 'media':
			result = [self.parse_media_prelude(prelude)]
		elif at_rule == 'import':
			result = self.parse_values(prelude).args
		elif at_rule == 'charset':
			result = [self.parse_expression([prelude[0]])]
		elif at_rule == 'namespace':
			result = self.parse_values(prelude).args
		elif at_rule == 'supports':
			result = [self.parse_supports_prelude(prelude)]
		else:
			result = prelude
		
		return StyleNode('prelude', result)
	
	def parse_supports_prelude(self, tokens):
		self.strip_space(tokens)
		
		if len(tokens) == 3 and tokens[1] == ':':
			return StyleNode('supports-test', [tokens[0], tokens[2]])
		
		result = []
		for token in tokens:
			if token in [" ", "\n", "\r", "\t"]:
				pass
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.brace:
				result.append(self.parse_supports_prelude(token.args))
			else:
				result.append(StyleNode('operator', [token]))
		
		return StyleNode('boolexpr', result)
	
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
		
		if len(result) == 1:
			return result[0]
		else:
			return StyleNode('media-tests', result)
	
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
		
		return StyleNode('media-test', result)
	
	def parse_media_prelude_rules(self, tokens):
		self.strip_space(tokens)
		
		result = []
		
		if hasattr(tokens[0], 'name') and tokens[0].name == self.ParserSymbol.brace:
			result.extend([StyleNode('media-property', [_arg.args[0], _arg.args[2]]) for _arg in self.build_list(tokens[0]).args])
		else:
			result.append(StyleNode('media-type', [_token for _token in tokens if _token != ' ']))
		
		return result
	
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
		
		return StyleNode('selector', result)
	
	def parse_selector_seq(self, tokens):
		self.strip_space(tokens)
		
		result = []
		args = []
		
		for token in tokens:
			if token in ['>', '~', '+']:
				if args:
					result.append(self.parse_selector_single(args))
					args = []
				
				if result and hasattr(result[-1], 'name') and result[-1].name == 'path-operator' and result[-1].args[0] == ' ':
					result[-1] = StyleNode('path-operator', [token])
				else:
					result.append(StyleNode('path-operator', [token]))
			elif token == ' ':
				if args:
					result.append(self.parse_selector_single(args))
					args = []
				
				if result and not (hasattr(result[-1], 'name') and result[-1].name == 'path-operator'):
					result.append(StyleNode('path-operator', [' ']))
			else:
				args.append(token)
		else:
			if args:
				result.append(self.parse_selector_single(args))
				args = []
		
		return StyleNode('selector-seq', result)
	
	def parse_selector_single(self, tokens):
		result = []
		
		past = []
		for token in tokens:
			if token in ['#', '.', ':']:
				pass
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.brace:
				if result and result[-1].name == 'selector-pseudo-class':
					result[-1] = StyleNode('selector-pseudo-class-fn', [result[-1].args[0], self.parse_selector_function_args(':' + result[-1].args[0], token.args)])
				elif result and result[-1].name == 'selector-pseudo-element':
					result[-1] = StyleNode('selector-pseudo-element-fn', [result[-1].args[0], self.parse_selector_function_args('::' + result[-1].args[0], token.args)])
				else:
					pass # warning
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.square:
				args = list(token.args)
				#assert len(args) == 3 or len(args) == 1
				if len(args) == 1:
					result.append(StyleNode('selector-attr-present', args))
				elif len(args) == 3:
					args[2] = self.__remove_optional_quotes(args[2])
					result.append(StyleNode('selector-attr', args))
				else:
					pass # warning
			elif not past:
				result.append(StyleNode('selector-tag', [token]))
			elif token == '*':
				pass # warning
			elif token == '%':
				if past and isinstance(past[-1], str) and past[-1] not in ['#', '.', ':'] and result and hasattr(result[-1], 'name') and result[-1].name == 'selector-tag':
					result[-1] = StyleNode('selector-percentage', result[-1].args)
				else:
					pass # warning
			elif past[-1] == '.':
				result.append(StyleNode('selector-class', [token]))
			elif past[-1] == '#':
				result.append(StyleNode('selector-id', [token]))
			elif past[-1] == ':' and (len(past) == 1 or past[-2] != ':'):
				result.append(StyleNode('selector-pseudo-class', [token]))
			elif len(past) >= 2 and past == [':', ':']:
				result.append(StyleNode('selector-pseudo-element', [token]))
			else:
				pass # warning
			
			past.append(token)
			if len(past) > 2:
				del past[0]
		
		return StyleNode('selector-single', result)
	
	def parse_selector_function_args(self, name, tokens):
		if name in [':is', ':has', ':with', ':not']:
			node = self.parse_selector_seq(tokens)
			return StyleNode('arguments', node.args)
		else: # TODO
			return StyleNode('arguments', tokens)
	
	def build_features(self, node):
		if not hasattr(node, 'name'):
			return node
		elif node.name == 'function':
			#print("feature:", node)
			return node
		else:
			return StyleNode(node.name, [self.build_features(_child) for _child in node.args])


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("css format")
	
	model = CSSFormat()
	
	tree = model.create_document(b'''
		:root {
			--one: '1';
			--two: '2';
			--three: '3';
		}
		
		element_1 {
			prop: var(--one);
		}
		
		element_2 {
			prop: var(--two);
		}
		
		element_3 {
			prop: var(--three);
		}
		
		element_4 {
			prop: var(--four);
		}
	''', 'text/css')
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	assert model.is_css_document(tree)
	assert tree.is_valid()
	
	tree = model.create_document(b'''
		html.html__responsive  *[data-is-here-when]:not([data-is-here-when~="sm"]){display:none}
	''', 'text/css')
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	assert model.is_css_document(tree)
	assert tree.is_valid()
	
	tree = model.create_document(b'''
		.s-editor-resizable{max-height:calc(var(--s-step) * 6);resize:vertical}
	''', 'text/css')
	#model.print_css_tree(tree)
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	assert model.is_css_document(tree)
	assert tree.is_valid()
	
	for cssfile in Path('gfx').iterdir():
		if cssfile.suffix != '.css': continue
		print()
		print(cssfile.name)
		tree = model.create_document(cssfile.read_bytes(), 'text/css')
		for node in tree.scan_syntax_errors():
			tree.print_context(node)
		#model.print_css_tree(tree)
		assert model.is_css_document(tree)
		assert tree.is_valid()
		#print(list(model.scan_document_links(tree)))

