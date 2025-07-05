#!/usr/bin/python3


import requests
from lxml import etree
from collections import defaultdict


def fetch_unicode_line_breaking_data(url):
	# Fetch the page
	response = requests.get(url)
	response.raise_for_status()  # Raise an error for bad status codes

	# Parse the HTML content and convert it to an XML tree
	tree = etree.fromstring(response.content, etree.HTMLParser())

	# Find the starting header
	start_header = tree.xpath('//h3[a/@name="DescriptionOfProperties"]')
	if not start_header:
		raise ValueError("Starting header not found.")

	# Initialize the dictionary to store the results
	category_dict = {}

	# Iterate over each h3 element after the starting header
	for h3 in start_header[0].itersiblings(tag='h3'):
		# Extract the category name
		category_name = h3.xpath('.//a/@name')[0]

		if h3.text and h3.text.strip() == '5.2':
			break

		# Initialize a set for the codepoints
		codepoint_set = set()
		codepoint_ranges = []

		# Find all tables following the current h3 until the next h3 or h2
		for table in h3.itersiblings():
			if table.tag in ('h3', 'h2'):
				break
			if table.tag != 'table':
				continue

			# Extract codepoints from the first column of the table
			for tr in table.xpath('.//tr'):
				first_td = tr.xpath('./td[1]')
				if first_td:
					text = first_td[0].text.strip()
					if '..' in text:
						# Handle range of codepoints
						start, end = text.split('..')
						start = start.strip()
						end = end.strip()
						codepoint_ranges.append(range(int(start, 16), int(end, 16) + 1))
					elif ',' in text:
						for number in text.split(','):
							if number.strip() == 'etc.': continue
							codepoint_set.add(int(number.strip(), 16))
					else:
						# Handle single codepoint as hex number
						codepoint_set.add(int(text.strip(), 16))

		# Add the codepoints set to the dictionary
		if codepoint_set:
			codepoint_ranges.append(codepoint_set)
		category_dict[category_name] = codepoint_ranges

		# Stop if the next element is an h2
		if h3.getnext().tag == 'h2':
			break

	return category_dict


def extract_centered_paragraphs(url, link_names):
	# Fetch the page
	response = requests.get(url)
	response.raise_for_status()  # Raise an error for bad status codes

	# Parse the HTML content and convert it to an XML tree
	tree = etree.fromstring(response.content, etree.HTMLParser())

	for link_name in link_names:
		# Find the starting header using the 'a/@name' attribute
		start_header = tree.xpath(f'//h3[a/@name="{link_name}"]')
		if not start_header:
			raise ValueError(f"Starting header with 'a/@name' attribute '{link_name}' not found.")

		# Iterate over the next siblings of the starting header
		for element in start_header[0].itersiblings():
			# Check if the element is a <p> tag with the specified style
			if element.tag == 'p' and element.get('style') == 'text-align:center':
				# Yield the text content of the <p> tag
				yield element.text.strip()

			# Stop if the next element is a heading tag
			if element.tag in ('h1', 'h2', 'h3'):
				break


def repr_hex(obj):
	if isinstance(obj, set):
		return '{' + ', '.join(hex(_n) for _n in obj) + '}'
	elif isinstance(obj, range):
		return 'range(' + hex(obj.start) + ', ' + hex(obj.stop) + ')'
	else:
		raise ValueError







class Tree:
	def __init__(self, production, arguments):
		self.production = production
		self.arguments = arguments

	def __repr__(self):
		return f"Tree({self.production}, {self.arguments})"
	
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


misses = 0
hits = 0

def cached(old_method):
	def new_method(self, *args):
		global misses, hits
		
		try:
			method_cache = self.__method_cache
		except AttributeError:
			method_cache = self.__method_cache = {}
		
		try:
			cache = method_cache[old_method.__name__]
		except KeyError:
			cache = method_cache[old_method.__name__] = {}
		
		try:
			result, value = cache[args]
			hits += 1
			if result:
				return value
			else:
				raise value
		except KeyError:
			misses += 1
			try:
				value = old_method(self, *args)
			except Exception as error:
				cache[args] = (False, error)
				raise
			else:
				cache[args] = (True, value)
				return value
	
	return new_method


class Parser:
	def __init__(self, start, grammar_source):
		self.start = start
		
		grammar = defaultdict(list)
		for nonterminal, production in self.analyze_grammar(grammar_source):
			grammar[nonterminal].append(tuple(production))
		
		self.grammar = dict(grammar)
	
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
				raise ParsingError(f"Garbage at the end of input {source[length]}.", "", [])
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
			return Tree(nonterminal + ' ::= ' + ' '.join(production), tuple(arguments)), offset + zpos
	
	@cached
	def process_terminal(self, source, position, terminal):
		zpos = 0
		while position < len(source) and source[position] == ' ':
			position += 1
			zpos += 1
		
		length = len(terminal) - 2
		value = source[position:position + length]
		if value == terminal[1:-1]:
			return Tree(terminal, value), length + zpos
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




if __name__ == '__main__':
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	# Example usage
	url = "https://www.unicode.org/reports/tr14/"
	
	categories = set()
	for category, codepoint_ranges in fetch_unicode_line_breaking_data(url).items():
		categories.add(category)
		print(repr(category) + ": [" + ", ".join(repr_hex(_cr) for _cr in codepoint_ranges) + "],")
	print()
	
	for rule in extract_centered_paragraphs(url, ["BreakingRules", "TailorableBreakingRules"]):
		print(repr(rule) + ",")
	print()


if __name__ == '__main__' and False:
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	# Example usage
	url = "https://www.unicode.org/reports/tr14/"
	
	categories = set()
	for category, codepoint_ranges in fetch_unicode_line_breaking_data(url).items():
		categories.add(category)
		print(repr(category) + ": [" + ", ".join(repr_hex(_cr) for _cr in codepoint_ranges) + "],")
	print()

	grammar = '''
		RULE ::= EXPR OP | OP EXPR | EXPR OP EXPR
		OP ::= "!" | "×" | "÷"
		
		EXPR ::= SEQ ( "|" SEQ )*
		SEQ ::= SIMPLE ( SIMPLE )*
		SIMPLE ::= ATOM "*" | ATOM "+" | ATOM
		ATOM ::= "(" EXPR ")" | SET | MOD
		
		SET ::= "[" EXPR "&" EXPR "]" | "[" EXPR "-" EXPR "]" | "[" "^" EXPR "]"
		MOD ::= BRK_CLASS | "\\p" "{" CHR_CLASS "}" | "$EastAsian" | "[◌]" | "sot" | "eot" | "ALL"
		
		BRK_CLASS ::= ''' + " | ".join("\"" + _cat + "\"" for _cat in categories) + '''
		CHR_CLASS ::= "Pi" | "Pf" | "Cn" | "Extended_Pictographic"
	'''
	
	parser = Parser('RULE', grammar)
	
	for nonterminal, productions in parser.grammar.items():
		print(nonterminal, '::=', ' | '.join((' '.join(_production)) for _production in productions))
	
	#print()
	#parser("CR × CR")
	#quit()
	
	print()
	with PyCallGraph(output=GraphvizOutput(output_type='svg', output_file=f'"parser.svg"')):
		for n, rule in enumerate(extract_centered_paragraphs(url, ["BreakingRules", "TailorableBreakingRules"])):
			if rule.startswith("Treat"): continue
			if rule == "(": continue
			rule = rule.replace("\t", " ")
			try:
				tree = parser(rule)
			except ParsingError:
				print(repr(rule), "<<error>>")
			else:
				print(repr(rule))
				for level, message in tree.print_tree():
					print(" " * level, message)
				print()
	
	print(hits, int(100 * hits / (hits + misses)), "%", misses, int(100 * misses / (hits + misses)), "%")

