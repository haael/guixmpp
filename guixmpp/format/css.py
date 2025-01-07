#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'CSSFormat', 'CSSParser', 'CSSDocument'


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "xml"

from collections import namedtuple, defaultdict
from enum import Enum
from itertools import chain, product
from lxml.etree import tostring

if __name__ == '__main__':
	from guixmpp.format.xml import XMLDocument
else:
	from .xml import XMLDocument


def parse_float(f): # TODO: move to utils
	if f is None:
		return None
	elif f == 'null':
		return 0
	else:
		return float(f)


class CSSFormat:
	web_colors = {
		'aliceblue': '#F0F8FF',
		'antiquewhite': '#FAEBD7',
		'aqua': '#00FFFF',
		'aquamarine': '#7FFFD4',
		'azure': '#F0FFFF',
		'beige': '#F5F5DC',
		'bisque': '#FFE4C4',
		'black': '#000000',
		'blanchedalmond': '#FFEBCD',
		'blue': '#0000FF',
		'blueviolet': '#8A2BE2',
		'brown': '#A52A2A',
		'burlywood': '#DEB887',
		'cadetblue': '#5F9EA0',
		'chartreuse': '#7FFF00',
		'chocolate': '#D2691E',
		'coral': '#FF7F50',
		'cornflowerblue': '#6495ED',
		'cornsilk': '#FFF8DC',
		'crimson': '#DC143C',
		'cyan': '#00FFFF',
		'darkblue': '#00008B',
		'darkcyan': '#008B8B',
		'darkgoldenrod': '#B8860B',
		'darkgray': '#A9A9A9',
		'darkgreen': '#006400',
		'darkgrey': '#A9A9A9',
		'darkkhaki': '#BDB76B',
		'darkmagenta': '#8B008B',
		'darkolivegreen': '#556B2F',
		'darkorange': '#FF8C00',
		'darkorchid': '#9932CC',
		'darkred': '#8B0000',
		'darksalmon': '#E9967A',
		'darkseagreen': '#8FBC8F',
		'darkslateblue': '#483D8B',
		'darkslategray': '#2F4F4F',
		'darkslategrey': '#2F4F4F',
		'darkturquoise': '#00CED1',
		'darkviolet': '#9400D3',
		'deeppink': '#FF1493',
		'deepskyblue': '#00BFFF',
		'dimgray': '#696969',
		'dimgrey': '#696969',
		'dodgerblue': '#1E90FF',
		'firebrick': '#B22222',
		'floralwhite': '#FFFAF0',
		'forestgreen': '#228B22',
		'fuchsia': '#FF00FF',
		'gainsboro': '#DCDCDC',
		'ghostwhite': '#F8F8FF',
		'gold': '#FFD700',
		'goldenrod': '#DAA520',
		'gray': '#808080',
		'green': '#008000',
		'greenyellow': '#ADFF2F',
		'grey': '#808080',
		'honeydew': '#F0FFF0',
		'hotpink': '#FF69B4',
		'indianred': '#CD5C5C',
		'indigo': '#4B0082',
		'ivory': '#FFFFF0',
		'khaki': '#F0E68C',
		'lavender': '#E6E6FA',
		'lavenderblush': '#FFF0F5',
		'lawngreen': '#7CFC00',
		'lemonchiffon': '#FFFACD',
		'lightblue': '#ADD8E6',
		'lightcoral': '#F08080',
		'lightcyan': '#E0FFFF',
		'lightgoldenrodyellow': '#FAFAD2',
		'lightgray': '#D3D3D3',
		'lightgreen': '#90EE90',
		'lightgrey': '#D3D3D3',
		'lightpink': '#FFB6C1',
		'lightsalmon': '#FFA07A',
		'lightseagreen': '#20B2AA',
		'lightskyblue': '#87CEFA',
		'lightslategray': '#778899',
		'lightslategrey': '#778899',
		'lightsteelblue': '#B0C4DE',
		'lightyellow': '#FFFFE0',
		'lime': '#00FF00',
		'limegreen': '#32CD32',
		'linen': '#FAF0E6',
		'magenta': '#FF00FF',
		'maroon': '#800000',
		'mediumaquamarine': '#66CDAA',
		'mediumblue': '#0000CD',
		'mediumorchid': '#BA55D3',
		'mediumpurple': '#9370DB',
		'mediumseagreen': '#3CB371',
		'mediumslateblue': '#7B68EE',
		'mediumspringgreen': '#00FA9A',
		'mediumturquoise': '#48D1CC',
		'mediumvioletred': '#C71585',
		'midnightblue': '#191970',
		'mintcream': '#F5FFFA',
		'mistyrose': '#FFE4E1',
		'moccasin': '#FFE4B5',
		'navajowhite': '#FFDEAD',
		'navy': '#000080',
		'oldlace': '#FDF5E6',
		'olive': '#808000',
		'olivedrab': '#6B8E23',
		'orange': '#FFA500',
		'orangered': '#FF4500',
		'orchid': '#DA70D6',
		'palegoldenrod': '#EEE8AA',
		'palegreen': '#98FB98',
		'paleturquoise': '#AFEEEE',
		'palevioletred': '#DB7093',
		'papayawhip': '#FFEFD5',
		'peachpuff': '#FFDAB9',
		'peru': '#CD853F',
		'pink': '#FFC0CB',
		'plum': '#DDA0DD',
		'powderblue': '#B0E0E6',
		'purple': '#800080',
		'red': '#FF0000',
		'rosybrown': '#BC8F8F',
		'royalblue': '#4169E1',
		'saddlebrown': '#8B4513',
		'salmon': '#FA8072',
		'sandybrown': '#F4A460',
		'seagreen': '#2E8B57',
		'seashell': '#FFF5EE',
		'sienna': '#A0522D',
		'silver': '#C0C0C0',
		'skyblue': '#87CEEB',
		'slateblue': '#6A5ACD',
		'slategray': '#708090',
		'slategrey': '#708090',
		'snow': '#FFFAFA',
		'springgreen': '#00FF7F',
		'steelblue': '#4682B4',
		'tan': '#D2B48C',
		'teal': '#008080',
		'thistle': '#D8BFD8',
		'tomato': '#FF6347',
		'turquoise': '#40E0D0',
		'violet': '#EE82EE',
		'wheat': '#F5DEB3',
		'white': '#FFFFFF',
		'whitesmoke': '#F5F5F5',
		'yellow': '#FFFF00',
		'yellowgreen': '#9ACD32'
	}
	
	def create_document(self, data, mime):
		if mime == 'text/css':
			return CSSDocument(CSSParser().parse_css(data.decode('utf-8'))) # TODO: parse encoding indicator from the file
		else:
			return NotImplemented
	
	def is_css_document(self, document):
		return hasattr(document, 'css_tree')
	
	def scan_document_links(self, document):
		if self.is_css_document(document):
			return chain(
				document.scan_imports(),
				document.scan_urls(),
				document.scan_fonts()
			)
		else:
			return NotImplemented
	
	def units(self, view, spec, percentage=None, percentage_origin=0, em_size=None):
		"Convert a string with unit spec into a float metric in pixels. If the spec involves percentage or `em`, additional arguments must be supplied."
		
		if not isinstance(spec, str):
			return spec
		
		spec = spec.strip()
		if not spec:
			return 0
		
		dpi = self.get_dpi(view)
		shift = 0
		
		if spec[-2:] == 'px':
			scale = 1
			value = spec[:-2]
		elif spec[-2:] == 'ex':
			if em_size == None:
				raise ValueError("`em_size` not specified.")
			scale = em_size * 0.5 # TODO
			value = spec[:-2]
		elif spec[-2:] == 'mm':
			scale = dpi / 25.4
			value = spec[:-2]
		elif spec[-2:] == 'cm':
			scale = dpi / 2.54
			value = spec[:-2]
		elif spec[-2:] == 'in':
			scale = dpi
			value = spec[:-2]
		elif spec[-2:] == 'pc':
			scale = dpi / 6
			value = spec[:-2]
		elif spec[-2:] == 'pt':
			scale = dpi / 72
			value = spec[:-2]
		elif spec[-2:] == 'em':
			if em_size == None:
				raise ValueError("`em_size` not specified.")
			scale = em_size * 1
			value = spec[:-2]
		elif spec[-1:] == 'Q':
			scale = dpi / (2.54 * 40)
			value = spec[:-1]
		elif spec[-1:] == '%':
			if percentage == None:
				raise ValueError("Percentage not specified.")
			scale = percentage / 100
			shift = percentage_origin
			value = spec[:-1]
		else:
			scale = 1
			value = spec
		
		return parse_float(value) * scale + shift
	
	def resolve_css_var(self, name, default=None):
		raise NotImplementedError(f"Resolve var: {name} / {default}")
	
	def resolve_css_func(self, name, *args):
		raise NotImplementedError(f"Resolve func: {name} ( {args} )")
	
	def create_css_matcher(self, view, document, media_test, get_id, get_classes, get_pseudoclasses, pseudoelement_test, default_namespace):
		namespace = ('{' + default_namespace + '}') if default_namespace else ''
		
		def walk_node(css_node, args):
			"""
			This method accepts a SyntaxTree and a list of processed arguments from recursive application of this method and returns the processed result.
			If css_node corresponds to a CSS selector (i.e. "div.c > *"), it should return a function that accepts XML node (from lxml.etree) and returns a boolean whether the node matches the selector.
			If css_node corresponds to a CSS value (like in "attr:value"), it should return a function that accepts a dict and returns the evaluated value as a string. The dict contains CSS vars (like "--custom-var")
			evaluated for the particular XML node, which may contain values collected from many different scopes.
			If css_node corresponds to the root of a stylesheet, it shoud return a function that takes an XML node and returns a dict. This dict should contain items: (attr, (priority, value_fn)) where `attr` is
			the name of the style attribute, `priority` is a priority determined from the specificity of the selector that contained this value and `value_fn` is a function that when given a var dict will return the evaluated value.
			Returning None means to ignore the node, as it does not produce any value, i.e. remove it from args list.
			This function is the hot spot of CSS processing so it must be optimized well.
			"""
			
			args = [_arg for _arg in args if _arg is not None]
			
			if isinstance(css_node, str):
				return css_node
			elif css_node.name == 'path-operator':
				return args[0]
			elif css_node.name == 'separator':
				return None
			elif css_node.name == 'importance':
				return None
			elif css_node.name == 'selector-tag':
				if args[0] == '*':
					return lambda _xml_node: True
				else:
					return (lambda _xml_node: _xml_node.tag == f'{namespace}{args[0]}'), ('tag', f'{namespace}{args[0]}')
			elif css_node.name == 'selector-class':
				return (lambda _xml_node: args[0] in get_classes(_xml_node) if (get_classes is not None) else False), ('class', args[0])
			elif css_node.name == 'selector-pseudo-class':
				if args[0] == 'empty':
					return lambda _xml_node: bool([_child for _child in _xml_node if isinstance(_child, str)]) and not bool(_xml_node.text)
				elif args[0] == 'first-child':
					return lambda _xml_node: _xml_node.getparent()[0] == _xml_node
				elif args[0] == 'first-of-type':
					self.emit_warning(view, "Implement pseudoclass: " + str(args[0]), css_node)
					return lambda _xml_node: False
				elif args[0] == 'last-child':
					return lambda _xml_node: _xml_node.getparent()[-1] == _xml_node
				elif args[0] == 'last-of-type':
					self.emit_warning(view, "Implement pseudoclass: " + str(args[0]), css_node)
					return lambda _xml_node: False
				elif args[0] == 'only-child':
					return lambda _xml_node: len(_xml_node.getparent()) == 1
				elif args[0] == 'only-of-type':
					self.emit_warning(view, "Implement pseudoclass: " + str(args[0]), css_node)
					return lambda _xml_node: False
				elif args[0] == 'root':
					return lambda _xml_node: _xml_node.getroottree().getroot() == _xml_node
				else:
					return (lambda _xml_node: (args[0] in get_pseudoclasses(_xml_node)) if (get_pseudoclasses is not None) else False), ('pseudoclass', args[0])
			elif css_node.name == 'selector-pseudo-class-fn':
				if args[0] == 'not':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				elif args[0] == 'is':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				elif args[0] == 'has':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				elif args[0] == 'with':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				elif args[0] == 'nth-child':
					
					cmp = lambda _n: False
					
					try:
						match args[1]:
							case ['odd']:
								cmp = lambda _n: (_n % 2 == 1)
							case ['even']:
								cmp = lambda _n: (_n % 2 == 0)
							case ['n']:
								cmp = lambda _n: True
							case [_c]:
								c = int(_c)
								cmp = lambda _n: (_n == c)
							case [_d, 'n']:
								d = int(_d)
								cmp = lambda _n: (_n % d == 0)
							case ['-', 'n', '+', _c]:
								c = int(_c)
								cmp = lambda _n: (_n <= c)
							case [_d, 'n', '+', _c]:
								c = int(_c)
								d = int(_d)
								if d > 1:
									cmp = lambda _n: (_n % d == c)
								elif d == 1:
									cmp = lambda _n: (_n > c)
								else:
									cmp = lambda _n: (_n == c)
							case _:
								self.emit_warning(view, "Unknown format of nth child spec: " + str(args[0]) + ", " + str(args[1]) + ".", css_node)
					except ValueError:
						self.emit_warning(view, "Unknown format of nth child spec: " + str(args[0]) + ", " + str(args[1]) + ".", css_node)
					
					return lambda _xml_node: cmp(_xml_node.getparent().index(_xml_node) + 1)
				
				elif args[0] == 'nth-last-child':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				elif args[0] == 'nth-last-of-type':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				elif args[0] == 'nth-of-type':
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
					return lambda _xml_node: False
				else:
					self.emit_warning(view, "Implement pseudoclass function: " + str(args[0]) + ".", css_node)
			elif css_node.name == 'selector-pseudo-element':
				return lambda _xml_node: pseudoelement_test(_xml_node, args[0]) if (pseudoelement_test is not None) else False
			elif css_node.name == 'selector-attr':
				if args[1] == '=':
					return lambda _xml_node: (args[0] in _xml_node.attrib) and (_xml_node.attrib[args[0]] == args[2])
				elif args[1] == '~=':
					return lambda _xml_node: (args[0] in _xml_node.attrib) and (args[2] in _xml_node.attrib[args[0]].split(' '))
				elif args[1] == '*=':
					return lambda _xml_node: (args[0] in _xml_node.attrib) and (args[2] in _xml_node.attrib[args[0]])
				elif args[1] == '^=':
					return lambda _xml_node: (args[0] in _xml_node.attrib) and (_xml_node.attrib[args[0]].startswith(args[2]))
				elif args[1] == '$=':
					return lambda _xml_node: (args[0] in _xml_node.attrib) and (_xml_node.attrib[args[0]].endswith(args[2]))
				elif args[1] == '|=':
					return lambda _xml_node: (args[0] in _xml_node.attrib) and (args[2] == _xml_node.attrib[args[0]] or _xml_node.attrib[args[0]].startswith(args[2] + '-'))
				else:
					self.emit_warning(view, "Implement attribute selector operator " + repr(args[1]), css_node)
					return lambda _xml_node: False
			elif css_node.name == 'selector-id':
				return (lambda _xml_node: args[0] == get_id(_xml_node) if (get_id is not None) else False), ('id', args[0])
			elif css_node.name == 'selector-percentage': # TODO: keyframes
				#self.emit_warning(view, "Implement keyframes.", css_node)
				return lambda _xml_node: False
			elif css_node.name == 'selector-single':
				assert all(callable(_check) if not isinstance(_check, tuple) else callable(_check[0]) for _check in args), str(args)
				
				tag = None
				id_ = None
				classes = set()
				pseudoclasses = set()
				for arg in args:
					if not isinstance(arg, tuple): continue
					typ, prop = arg[1]
					match typ:
						case 'tag':
							tag = prop
						case 'id':
							id_ = prop
						case 'class':
							classes.add(prop)
						case 'pseudoclass':
							pseudoclasses.add(prop)
						case _:
							raise ValueError
				
				fargs = [_matcher[0] if isinstance(_matcher, tuple) else _matcher for _matcher in args]
				
				return (lambda _xml_node: all(_check(_xml_node) for _check in fargs)), (tag, id_, frozenset(classes), frozenset(pseudoclasses))
			elif css_node.name == 'selector-seq':
				def check_selector_seq(args, xml_node):
					if xml_node is None or not args[-1](xml_node):
						return False
					
					if len(args) == 1:
						return True
					elif args[-2] == '>':
						return check_selector_seq(args[:-2], xml_node.getparent())
					elif args[-2] == ' ':
						ancestor = xml_node.getparent()
						while ancestor is not None:
							if check_selector_seq(args[:-2], ancestor):
								return True
							ancestor = ancestor.getparent()
						else:
							return False
					elif args[-2] == '+':
						return check_selector_seq(args[:-2], xml_node.getprevious())
					elif args[-2] == '~':
						senpai = xml_node.getprevious()
						while senpai is not None:
							if check_selector_seq(args[:-2], senpai):
								return True
							senpai = senpai.getprevious()
						else:
							return False
					else:
						self.emit_warning(view, "Implement path operator: " + str(args[-2]), css_node)
						return False
				
				fargs = [_matcher[0] if isinstance(_matcher, tuple) else _matcher for _matcher in args]
				props = [_matcher[1] for _matcher in args if isinstance(_matcher, tuple)][-1]
				
				return (lambda _xml_node: check_selector_seq(fargs, _xml_node)), props
			elif css_node.name == 'function':
				assert len(args) == 2
				return lambda _vars: FuncExpr(args[0], args[1](_vars))
			elif css_node.name == 'url':
				assert len(args) == 1
				return lambda _vars: f'url({args[0]})'
			elif css_node.name == 'arguments':
				return lambda _vars: [_arg(_vars) for _arg in args]
			elif css_node.name == 'selector-function-arguments':
				return args
			elif css_node.name == 'value':
				assert len(args) == 1
				#assert isinstance(args[0], str), repr(args[0])
				if isinstance(args[0], str):
					return lambda _vars: args[0]
				else:
					return lambda _vars: args[0](_vars)
			elif css_node.name == 'multivalue':
				return lambda _vars: [_arg if isinstance(_arg, str) else _arg(_vars) for _arg in args]
			elif css_node.name == 'values':
				return lambda _vars: [_arg(_vars) for _arg in args]
			elif css_node.name == 'rule':
				return args
			elif css_node.name == 'rules':
				return dict((_kv[0], _kv[1:]) for _kv in args if _kv is not None)
			elif css_node.name == 'selector':
				testers = []
				properties = []
				selectors = []
				for sel, (tst, prop) in zip(css_node.args, args):
					testers.append(tst)
					properties.append(prop)
					selectors.append(sel)
				return list(zip(properties, testers, selectors))
			elif css_node.name == 'style':
				assert isinstance(args[0], list) and all(len(_el) == 3 for _el in args[0])
				assert isinstance(args[1], dict)
				return [_el + (args[1],) for _el in args[0]]
			elif css_node.name == 'stylesheet' or css_node.name == 'scope':
				per_tag = defaultdict(set)
				per_id = defaultdict(set)
				per_class = defaultdict(set)
				per_pseudoclass = defaultdict(set)
				per_selector = defaultdict(list)
				all_selectors = set()
				
				for zarg in args:
					if zarg is None: continue
					for (tag, id_, classes, pseudoclasses), tester, selector, rules in zarg:
						per_tag[tag].add(selector)
						if tag is not None:
							per_tag[True].add(selector)
						
						per_id[id_].add(selector)
						if id_ is not None:
							per_id[True].add(selector)
						
						if not classes:
							per_class[None].add(selector)
						else:
							for class_ in classes:
								per_class[class_].add(selector)
							per_class[True].add(selector)
						
						if not pseudoclasses:
							per_pseudoclass[None].add(selector)
						else:
							for pclass_ in pseudoclasses:
								per_pseudoclass[pclass_].add(selector)
							per_pseudoclass[True].add(selector)
						
						per_selector[selector].append((tester, self.css_selector_priority(view, document, selector), rules))
						all_selectors.add(selector)
				
				def match_selector(xml_node):
					# limit number of selectors to process
					
					tag = xml_node.tag
					selectors = per_tag[None] | (per_tag[tag] if (tag in per_tag) else frozenset()) # only selectors with the right tag, or wildcard tag
					
					if selectors & per_id[True]: # any overlap with id selectors?
						id_ = get_id(xml_node) if (get_id is not None) else None
						selectors &= per_id[None] | (per_id[id_] if (id_ in per_id) else frozenset()) # only selectors with the right id, or no id
					
					if selectors & per_class[True]: # any overlap with class selectors?
						classes = get_classes(xml_node) if (get_classes is not None) else frozenset()
						selectors &= per_class[None] | frozenset().union(*[per_class[_clas] for _clas in classes if _clas in per_class]) # only selectors with the right class, or no class
					
					if selectors & per_pseudoclass[True]: # any overlap with pseudoclass selectors?
						pseudoclasses = get_pseudoclasses(xml_node) if (get_pseudoclasses is not None) else frozenset()
						selectors &= per_pseudoclass[None] | frozenset().union(*[per_pseudoclass[_clas] for _clas in pseudoclasses if _clas in per_pseudoclass]) # only selectors with the right pseudoclass, or no pseudoclass
					
					result = {}
					for selector in selectors:
						for matcher, priority, rules in per_selector[selector]:
							if not matcher(xml_node): continue
							
							for key, value in rules.items():
								if key in result:
									cur_priority = result[key][1]
								else:
									cur_priority = 0
								
								if priority >= cur_priority:
									if len(value) == 2 and value[1] == '!important':
										priority += 10000
									result[key] = value[0], priority
					
					return result
				
				return match_selector
			elif css_node.name == 'prelude':
				return args
			elif css_node.name == 'atrule-simple':
				return None
			elif css_node.name == 'atrule-style':
				if args[0] == 'font-face':
					return None
				return None
			elif css_node.name == 'atrule-block':
				if args[0] == 'keyframes':
					#self.emit_warning(view, "Implement keyframes.", css_node)
					return None
				return None
			elif css_node.name == 'var-decl':
				assert len(args) == 2
				return args[0], lambda _vars: args[1](_vars)
			elif css_node.name == 'var':
				assert len(args) == 1 or len(args) == 2, str(args)
				def get_arg(_vars):
					try:
						return _vars[args[0]]
					except KeyError:
						if len(args) == 2:
							return args[1]
						else:
							return ''
				return get_arg
			elif css_node.name == 'selector-attr-present':
				return None
			elif css_node.name == 'infix-operator':
				return css_node
			elif css_node.name == 'expression':
				if len(args) == 3:
					if args[1].name == 'infix-operator':
						return lambda _var: [args[1].args[0], [args[0](_var), args[2](_var)]]
				
				self.emit_warning(view, f"Unimplemented CSS expression: {args}.", css_node)
			else:
				self.emit_warning(view, f"Unimplemented CSS syntax: {css_node.name}.", css_node)
				#return css_node
		
		return document.traverse(document.css_tree, None, None, walk_node, None)
	
	def css_selector_priority(self, view, document, selector):
		try:
			return selector.__cache_selector_priority
		except AttributeError:
			pass
		
		def walk_node(node, args):
			if isinstance(node, str):
				return node
			elif node.name == 'selector-tag':
				if args[0] == '*':
					return 1
				else:
					return 2
			elif node.name == 'selector-class':
				return 10
			elif node.name == 'selector-attr':
				return 20
			elif node.name == 'selector-id':
				return 30
			elif node.name == 'selector-pseudo-class':
				if node.args[0] == 'active':
					return 41
				return 40
			elif node.name == 'selector-pseudo-element':
				return 100
			elif node.name == 'selector-percentage':
				return 1
			elif node.name == 'selector-single':
				return sum(args)
			elif node.name == 'selector-seq':
				return max(args)
			elif node.name == 'path-operator':
				pri = [0]
				for arg in args:
					match arg:
						case ' ':
							pri.append(1)
						case '>':
							pri.append(2)
						case '~':
							pri.append(5)
						case '+':
							pri.append(5)
						case _:
							self.emit_warning(view, "Implement path operator priority: " + str(arg), node)
				return sum(pri)
			else:
				self.emit_warning(view, "Implement selector priority: " + str(node.name), node)
				return 0
		
		def descend(node):
			if isinstance(node, str):
				return False
			elif node.name in ['selector-class', 'selector-attr', 'selector-id', 'selector-pseudo-class']:
				return False
			else:
				return True
		
		priority = document.traverse(selector, [], None, walk_node, descend)
		selector.__cache_selector_priority = priority
		return priority
	
	def eval_css_value(self, value):
		if not isinstance(value, list):
			raise TypeError
		
		r = []
		for val in value:
			if isinstance(val, str):
				r.append(val)
			elif isinstance(val, FuncExpr):
				r.append(val.name + "(" + self.eval_css_value(val.args) + ")")
			else:
				raise ValueError(f"{type(val)} {repr(val)}")
		
		return ",".join(r)


class StyleNode:
	"CSS document is made of style nodes that have a name and children that could be other style nodes or strings."
	
	def __init__(self, name, args):
		self.name = name
		self.args = args
	
	def __repr__(self):
		return f"<{self.__class__.__qualname__} {repr(self.name)} @{hex(id(self))}>"
	
	def __str__(self):
		return str(self.name) + "(" + ", ".join(str(_arg) for _arg in self.args) + ")"
	
	def __eq__(self, other):
		try:
			return self.name == other.name and self.args == other.args
		except AttributeError:
			return NotImplemented
	
	def __hash__(self):
		return hash((self.name,) + tuple(hash(_arg) for _arg in self.args))


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
	
	def traverse(self, node, param, pre_function, post_function, descend_function):
		if pre_function != None:
			node, param = pre_function(node, param)
		
		if hasattr(node, 'args') and (descend_function == None or descend_function(node)):
			children = []
			for child in node.args:
				child = self.traverse(child, param, pre_function, post_function, descend_function)
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
		
		if tree is None:
			self.traverse(self.css_tree, level, print_node, None, None)
		else:
			self.traverse(tree, level, print_node, None, None)
	
	def tree_contains(self, tree, target):
		def catch(node, results):
			if node is target:
				return True
			else:
				return any(results)
		
		return self.traverse(tree, None, None, catch, None)
	
	def print_context(self, target, tree=None, level=0):
		def print_node(node, level):
			if node is target:
				self.print_tree(target, level)
			elif hasattr(node, 'name') and self.tree_contains(node, target):
				print(" " * level, node.name)
			return node, level + 1
		
		if tree is None:
			self.traverse(self.css_tree, level, print_node, None, None)
		else:
			self.traverse(tree, level, print_node, None, None)
	
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
		"Yield all @import urls."
		
		for node in self.css_tree.args:
			try:
				if all([
					node.name == 'atrule-simple',
					node.args[0] == 'import',
					node.args[1].name == 'prelude',
					node.args[1].args[0].name == 'value',
					node.args[1].args[0].args[0].name == 'url'
				]):
					yield node.args[1].args[0].args[0].args[0]
			except (AttributeError, IndexError):
				pass
	
	def scan_fonts(self):
		"Yield all urls pointing to web fonts."
		
		for node in self.css_tree.args:
			try:
				if node.name == 'atrule-style' and node.args[0] == 'font-face' and node.args[2].name == 'rules':
					for subnode in node.args[2].args:
						if subnode.name == 'rule' and subnode.args[0] == 'src':
							for urlnode in subnode.args[1].args:
								if urlnode.name == 'value' and urlnode.args[0].name == 'url':
									yield urlnode.args[0].args[0]
			except (AttributeError, IndexError):
				pass
	
	def scan_font_faces(self): # TODO
		for node in self.css_tree.args:
			try:
				if node.name == 'atrule-style' and node.args[0] == 'font-face' and node.args[2].name == 'rules':
					font_family = []
					font_weight = []
					srcs = []
					for subnode1 in node.args[2].args:
						if subnode1.name != 'rule':
							continue # warning
						
						if subnode1.args[0] == 'src':
							prop = {}
							for subnode2 in subnode1.args[1].args:
								if subnode2.name == 'separator':
									if prop:
										srcs.append(prop)
										prop = {}
									continue
								elif subnode2.name != 'value':
									print('subnode2', subnode2.name, subnode2.args) # warning
									continue
								
								#print("iter", subnode2)
								subnode3 = subnode2.args[0]
								if subnode3.name == 'url':
									prop['url'] = subnode3.args[0]
								elif subnode3.name == 'function':
									for value in subnode3.args[1].args:
										if value.name != 'value': continue
										
										for vv in value.args:
											vv = vv.strip()
											if vv[0] in '\'\"':
												vv = vv[1:]
											if vv[-1] in '\'\"':
												vv = vv[:-1]
											
											prop[subnode3.args[0]] = vv
								#elif subnode3.name == 'separator':
								#	if prop:
								#		srcs.append(prop)
								#		prop = {}
								else:
									print('subnode3', subnode3.name, subnode3.args) # warning
							
							if prop:
								srcs.append(prop)
						elif subnode1.args[0] == 'font-family' and subnode1.args[1].name == 'values':
							for value in subnode1.args[1].args:
								if value.name != 'value': continue # warning
								ff = value.args[0].strip()
								if ff[0] in '\'\"':
									ff = ff[1:]
								if ff[-1] in '\'\"':
									ff = ff[:-1]
								font_family.append(ff.strip())
					
					if not font_weight:
						font_weight.append('normal')
					
					#if not font_style:
					#	font_style.append('normal')
					
					for fontspec in product(font_family, font_weight):
						yield fontspec, srcs
			except (AttributeError, IndexError):
				pass
	
	def scan_urls(self):
		"Yield all urls in style values."
		
		result = []
		
		def walk_node(node, ancestors):
			if ancestors == ['stylesheet', 'style', 'rules', 'rule', 'values', 'url'] and isinstance(node, str):
				result.append(node)
			
			return node, ancestors + [node.name if hasattr(node, 'name') else None]
		
		self.traverse(self.css_tree, [], walk_node, None, None)
		
		return result
	
	def scan_vars(self):
		raise NotImplementedError


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
	
	__hex_digits = frozenset('0123456789abcdefABCDEF')
	
	@classmethod
	def __hex_escape(cls, s):
		r = []
		e = False
		h = []
		for c in s:
			if e:
				if c in cls.__hex_digits:
					h.append(c)
				elif c == ' ':
					e = False
					r.append(chr(int(''.join(h), 16)))
				else:
					e = False
					r.append(chr(int(''.join(h), 16)))
					r.append(c)
			else:
				if c == '\\':
					h.clear()
					e = True
				else:
					r.append(c)
		
		if e:
			r.append(chr(int(''.join(h), 16)))
		return r
	
	LexerContext = Enum('LexerContext', 'comment xmlcomment quote dblquote variable identifier number whitespace hexnumber')
	
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
			
			elif context == self.LexerContext.xmlcomment:
				if stream.prefix(3) == '-->':
					stream.shift(3)
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
					token.append('\\')
					token.append(stream.prefix(1))
					stream.shift(1)
				elif stream.prefix(1) == '"':
					yield ''.join(['"'] + self.__hex_escape(token) + ['"'])
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
			
			elif stream.prefix(4) == '<!--':
				context = self.LexerContext.xmlcomment
				stream.shift(4)
			
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
		for token in tokens + [None]:
			if token in [' ', ',', '!', None]:
				if seq:
					result.append(self.parse_expression(seq))
					seq = []
				
				if token is None:
					pass
				elif token == '!':
					seq.append(token)
				elif token in [',', ';']:
					result.append(StyleNode('separator', token))
			elif token is not None:
				seq.append(token)
		
		assert not seq
		return StyleNode('values', result)
	
	def parse_expression(self, tokens):
		assert tokens
		self.strip_space(tokens)
		op = False
		
		result = []
		ts = []
		for token in tokens:
			if token in [' ', '\t', '\r', '\n']:
				pass
			elif token in ['+', '-', '*', '/']:
				if ts:
					result.append(self.parse_expression(ts))
				result.append(StyleNode('infix-operator', [token]))
				ts = []
				op = True
			elif isinstance(token, str) and ts and isinstance(ts[-1], str) and (ts[-1][-1] in '0123456789.#'): # FIXME: correct number parsing
				ts[-1] = ts[-1] + token
			elif hasattr(token, 'name') and token.name == self.ParserSymbol.brace and ts:
				if ts[-1] == 'var':
					if ',' in token.args:
						c = token.args.index(',')
						assert c == 1 # warning
						args = self.parse_arguments(token.args[c + 1:])
						result.append(StyleNode('var', [token.args[0], args]))
					else:
						result.append(StyleNode('var', token.args))
					del ts[-1]
				elif ts[-1] == 'url':
					result.append(StyleNode('url', [self.__remove_optional_quotes(''.join(token.args))]))
					del ts[-1]
				else:
					result.append(StyleNode('function', [ts[-1], self.parse_arguments(token.args)]))
					del ts[-1]
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
	
	def parse_arguments(self, tokens):
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
				elif len(args) >= 3:
					result.append(StyleNode('selector-attr', [args[0], ''.join(args[1:-1]).strip(), self.__remove_optional_quotes(args[-1])]))
				else:
					print("Wrong attr selector:", args)
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
			return StyleNode('selector-function-arguments', node.args)
		else: # TODO
			return StyleNode('selector-function-arguments', tokens)
	
	def build_features(self, node):
		if not hasattr(node, 'name'):
			return node
		elif node.name == 'function':
			return node
		else:
			return StyleNode(node.name, [self.build_features(_child) for _child in node.args])


class FuncExpr:
	def __init__(self, name, args):
		self.name = name
		self.args = args


if __name__ == '__main__':
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	from pathlib import Path
	from lxml.etree import fromstring
	
	print("css format")
	
	class CSSFormatPlus(CSSFormat):
		def emit_warning(self, view, message, node):
			print(message, node)
	
	model = CSSFormatPlus()
	
	view = None
	
	sample_css = model.create_document(b'''
	 *.x { tag: '*'; selector: '*'; selector_all: 1 }
	 a { tag: 'a'; selector: 1, 2, 3; selector_a: 2 }
	 /*a * { tag: '*'; selector: 'a *'; selector_a_all: 3 }
	 a > * { tag: '*'; selector: 'a > *'; selector_a_direct_all: 4 }*/
	 b { tag: 'b'; selector: 'b'; selector_b: 5 }
	 /*b * { tag: '*'; selector: 'b *'; selector_b_all: 6 }
	 b > * { tag: 'b'; selector: 'b > *'; selector_b_direct_all: 7 }*/
	 c { tag: 'c'; selector: 'c'; selector_c: 8 }
	 d { tag: 'd'; selector: 'd'; selector_d: 9 }
	 b c { tag: 'c'; selector: 'b c'; selector_b_c: 10 }
	 b, c { tag: 'b,c'; selector: 'b, c'; selector_b_or_c: 11 }
	''', 'text/css')
	
	assert sample_css.is_valid()
	assert model.is_css_document(sample_css)
	#sample_css.print_tree()
	
	sample_xml = XMLDocument(fromstring(b'''
	<a>
	 <b/>
	 <b/>
	 <c/>
	 <b>
	  <c/>
	  <d/>
	 </b>
	</a>
	'''))
	
	print()
	print("matcher")
	matcher = model.create_css_matcher(view, sample_css, None, None, None, None, None, None)
	for element in sample_xml.iter():
		values = matcher(element)
		print(element)
		for name, (value, priority) in values.items():
			print("", name, priority, value({}))
	
	print()
	print("vars")
	tree = model.create_document(b'''
		:root {
			--one: '1';
			--two: '2';
			--three: '3';
		}
		
		element_1 {
			--five: '5';
			prop1: var(--one);
			prop2: var(--five);
		}
		
		element_2 {
			prop1: var(--two);
			prop2: var(--five);
		}
		
		element_3 {
			prop: var(--three);
		}
		
		element_4 {
			prop: var(--four);
		}
	''', 'text/css')
	
	assert tree.is_valid()
	assert model.is_css_document(tree)
	#tree.print_tree()
	
	sample_xml = XMLDocument(fromstring(b'''
	<root>
	 <element_1/>
	 <element_2/>
	 <element_3/>
	 <element_4/>
	</root>
	'''))
	
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	matcher = model.create_css_matcher(view, tree, None, None, None, None, None, None)
	for element in sample_xml.iter():
		values = matcher(element)
		print(element)
		for name, (value, priority) in values.items():
			print("", name, priority, value({'--one':"1", '--two':"2", '--three':"3", '--four':"4", '--five':"5"}))
	
	print()
	print("not")
	tree = model.create_document(b'''
		html.html__responsive  *[data-is-here-when]:not([data-is-here-when~="sm"]){display:none}
	''', 'text/css')
	assert tree.is_valid()
	assert model.is_css_document(tree)
	#tree.print_tree()
	
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	
	print()
	print("calc")
	tree = model.create_document(b'.a { a:a; b:calc(a); c:calc(a*b); d:var(--a); e:calc(var(--a)); f:calc(var(--a)*b);  }', 'text/css')
	
	assert tree.is_valid()
	assert model.is_css_document(tree)
	#tree.print_tree()
	
	sample_xml = XMLDocument(fromstring(b'<root class="a"/>'))
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	matcher = model.create_css_matcher(view, tree, None, None, lambda _node: frozenset(_node.attrib['class'].split(",")), None, None, None)
	for element in sample_xml.iter():
		values = matcher(element)
		print(element)
		for name, (value, priority) in values.items():
			print("", name, priority, value({'--a':'va'}))
	
	print()
	print("font-face")
	tree = model.create_document(b'''
	@font-face
	{
		font-family:OpenSans;
		src:url(/f/open-sans-3/OpenSans-Regular.eot);
		src:
			url(/f/open-sans-3/OpenSans-Regular.eot?#iefix) format('embedded-opentype'),
			url(/f/open-sans-3/OpenSans-Regular.woff2) format('woff2'),
			url(/f/open-sans-3/OpenSans-Regular.woff) format('woff'),
			url(/f/open-sans-3/OpenSans-Regular.ttf) format('truetype'),
			url(/f/open-sans-3/OpenSans-Regular.svg#OpenSansRegular) format('svg');
		font-weight:400;
		font-style:normal;
		font-display:swap
	}
	@font-face
	{
		font-family:OpenSansSB;
		src:url(/f/open-sans-3/OpenSans-Semibold.eot);
		src:
			url(/f/open-sans-3/OpenSans-Semibold.eot?#iefix) format('embedded-opentype'),
			url(/f/open-sans-3/OpenSans-Semibold.woff2) format('woff2'),
			url(/f/open-sans-3/OpenSans-Semibold.woff) format('woff'),
			url(/f/open-sans-3/OpenSans-Semibold.ttf) format('truetype'),
			url(/f/open-sans-3/OpenSans-Semibold.svg#OpenSansSemibold) format('svg');
		font-weight:400;
		font-style:normal;
		font-display:swap
	}
	@font-face
	{
		font-family:OpenSansB;
		src:url(/f/open-sans-3/OpenSans-Bold.eot);
		src:
			url(/f/open-sans-3/OpenSans-Bold.eot?#iefix) format('embedded-opentype'),
			url(/f/open-sans-3/OpenSans-Bold.woff2) format('woff2'),
			url(/f/open-sans-3/OpenSans-Bold.woff) format('woff'),
			url(/f/open-sans-3/OpenSans-Bold.ttf) format('truetype'),
			url(/f/open-sans-3/OpenSans-Bold.svg#OpenSansBold) format('svg');
		font-weight:400;
		font-style:normal;
		font-display:swap
	}
	@font-face
	{
		font-family:OpenSansEB;
		src:url(/f/open-sans-3/OpenSans-ExtraBold.eot);
		src:
			url(/f/open-sans-3/OpenSans-ExtraBold.eot?#iefix) format('embedded-opentype'),
			url(/f/open-sans-3/OpenSans-ExtraBold.woff2) format('woff2'),
			url(/f/open-sans-3/OpenSans-ExtraBold.woff) format('woff'),
			url(/f/open-sans-3/OpenSans-ExtraBold.ttf) format('truetype'),
			url(/f/open-sans-3/OpenSans-ExtraBold.svg#OpenSansExtraBold) format('svg');
		font-weight:400;
		font-style:normal;
		font-display:swap
	}
	@font-face
	{
		font-family:OpenSansLI;
		src:url(/f/open-sans-3/OpenSans-LightItalic.eot);
		src:
			url(/f/open-sans-3/OpenSans-LightItalic.eot?#iefix) format('embedded-opentype'),
			url(/f/open-sans-3/OpenSans-LightItalic.woff2) format('woff2'),
			url(/f/open-sans-3/OpenSans-LightItalic.woff) format('woff'),
			url(/f/open-sans-3/OpenSans-LightItalic.ttf) format('truetype'),
			url(/f/open-sans-3/OpenSans-LightItalic.svg#OpenSanslightitalic) format('svg');
		font-weight:400;
		font-style:normal;
		font-display:swap
	}
	@font-face
	{
		font-family:OpenSansL;
		src:url(/f/open-sans-3/OpenSans-Light.eot);
		src:
			url(/f/open-sans-3/OpenSans-Light.eot?#iefix) format('embedded-opentype'),
			url(/f/open-sans-3/OpenSans-Light.woff2) format('woff2'),
			url(/f/open-sans-3/OpenSans-Light.woff) format('woff'),
			url(/f/open-sans-3/OpenSans-Light.ttf) format('truetype'),
			url(/f/open-sans-3/OpenSans-Light.svg#OpenSanslight) format('svg');
		font-weight:400;
		font-style:normal;
		font-display:swap
	}
	body,html { background-color:#fff; color:#1e1f23; font-family:OpenSans,Arial,sans-serif; font-size:16px }
	''', 'text/css')
	
	assert tree.is_valid()
	assert model.is_css_document(tree)
	#tree.print_tree()
	
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	for (name, type_), srcs in tree.scan_font_faces():
		print(name, type_)
		for src in srcs:
			print("src:", src)
	print("font urls:", list(tree.scan_fonts()))
	#m = model.create_css_matcher(tree, None, None, None, None, None, None)
	
	#print(m())
	
	print()
	print("url")
	tree = model.create_document(b'''
@import
  url(http://fonts.googleapis.com/css?family=Miltonian+Tattoo); 

        svg {
            font-family: "Miltonian Tattoo", serif;
            font-size: 18pt;
        }
        .verse {
            fill: darkGreen;
            stroke: #031;
            word-spacing: 2px;                             
        }
        .verse > tspan:nth-child(2n) {                     
            fill: navy;
            stroke: #013;
        }
	''', 'text/css')
	
	assert tree.is_valid()
	assert model.is_css_document(tree)
	tree.print_tree()
	
	for node in tree.scan_syntax_errors():
		tree.print_css_context(node)
	for (name, type_), srcs in tree.scan_font_faces():
		print(name, type_)
		for src in srcs:
			print("src:", src)
	print("import urls:", list(tree.scan_imports()))
	#m = model.create_css_matcher(tree, None, None, None, None, None, None)

	
	print()
	print("examples")
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for cssfile in example.iterdir():
			if cssfile.suffix != '.css': continue
			
			#profiler = PyCallGraph(output=GraphvizOutput(output_file=f'profile/css_{example.name}_{cssfile.name}.png'))
			#profiler.start()
			
			tree = model.create_document(cssfile.read_bytes(), 'text/css')
			for node in tree.scan_syntax_errors():
				tree.print_context(node)
			#model.print_css_tree(tree)
			assert model.is_css_document(tree)
			assert tree.is_valid()
			#print(list(model.scan_document_links(tree)))
			for (name, type_), srcs in tree.scan_font_faces():
				print(name, type_)
				for src in srcs:
					print("src:", src)
			print("font urls:", list(tree.scan_fonts()))
			
			#profiler.done()
