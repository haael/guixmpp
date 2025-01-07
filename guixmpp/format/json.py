#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'JSONFormat', 'JSONDocument'


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "json"


from io import BytesIO
from json import loads, dumps


class JSONDocument:
	def __init__(self, content):
		self.content = content


class JSONFormat:
	def __init__(self, *args, **kwargs):
		pass
	
	def create_document(self, data:bytes, mime:str):
		if mime == 'application/json':
			document = JSONDocument(loads(data.decode('utf-8')))
			return document
		else:
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_json_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(dumps(document.content).encode('utf-8'))
			return fileobj
		else:
			return NotImplemented
	
	def is_json_document(self, document):
		return isinstance(document, JSONDocument)
	
	def scan_document_links(self, document):
		if self.is_json_document(document):
			return []
		else:
			return NotImplemented


if __name__ == '__main__':
	from pathlib import Path
	
	print("json format")
	
	model = JSONFormat()
	a = model.create_document(b'''{
  "first_name": "John",
  "last_name": "Smith",
  "is_alive": true,
  "age": 27,
  "address": {
    "street_address": "21 2nd Street",
    "city": "New York",
    "state": "NY",
    "postal_code": "10021-3100"
  },
  "phone_numbers": [
    {
      "type": "home",
      "number": "212 555-1234"
    },
    {
      "type": "office",
      "number": "646 555-4567"
    }
  ],
  "children": [
    "Catherine",
    "Thomas",
    "Trevor"
  ],
  "spouse": null
}
''', 'application/json')
	assert model.is_json_document(a)
	
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for jsonfile in example.iterdir():
			if jsonfile.suffix != '.json': continue
			document = model.create_document(jsonfile.read_bytes(), 'application/json')
			assert model.is_json_document(document)

