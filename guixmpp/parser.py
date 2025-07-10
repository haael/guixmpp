#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'Parser', 'ParsingError', 'ParseTree'


from collections import defaultdict


if __name__ == '__main__':
	from guixmpp.caching import cached
else:
	from .caching import cached


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
	
	@cached
	def process_nonterminal(self, source, position, nonterminal):
		sp = 0
		while position + sp < len(source) and source[position + sp] == ' ':
			sp += 1
		errors = []
		results = {}
		for production in self.grammar[nonterminal]:
			if not any(source[position + sp : position + sp + len(_pfx)] == _pfx for _pfx in self.prefixes(production)): continue
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

