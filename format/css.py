#!/usr/bin/python3


class CSSFormat:
	def scan_css_imports(self, document):
		for node in document.args:
			try:
				if all([
					node.name == 'atrule-simple',
					node.args[0] == 'import',
					node.args[1].name == 'values',
					node.args[1].args[0].name == 'function',
					node.args[1].args[0].args[0] == 'url',
					node.args[1].args[0].args[1].name == 'arguments'
				]):
					url = ''.join(node.args[1].args[0].args[1].args)
					if url[0] == '"' or url[0] == '\'':
						url = url[1:-1]
					yield url
			except (AttributeError, IndexError):
				pass
	
	def scan_document_links(self, document):
		if self.is_css_document(document):
			return []
		else:
			return NotImplemented


if __name__ == '__main__':
	from model.css import CSSModel
	from pathlib import Path
	
	class Model(CSSFormat, CSSModel):
		pass
	
	model = Model()
	tree = model.create_document(Path('gfx/so-primary.css').read_bytes(), 'text/css')
	assert model.is_css_document(tree)
	
	print(list(model.scan_css_imports(tree)))


