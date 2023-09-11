#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'WOFFFont',


#from io import BytesIO
from hashlib import blake2b
from pathlib import Path
from fontTools import ttLib


class FontFile:
	def __init__(self, path, format_):
		self.path = path
		self.format_ = format_
	
	@property
	def name(self):
		with ttLib.TTFont(self.path) as f:
			return f['name'].getDebugName(4)
	
	@name.setter
	def name(self, name):
		raise NotImplementedError


class WOFFFont:	
	def create_document(self, data:bytes, mime_type):
		if mime_type == 'application/x-font-woff' or mime_type == 'application/font-woff':
			data = self.create_document(data, 'application/octet-stream')
			path = self.font_dir / (blake2b(data).hexdigest()[:32] + '.woff')
			if not path.exists():
				with path.open('wb') as fd:
					self.save_document(data, fd)
			return FontFile(path, 'woff')
		else:
			return NotImplemented
	
	def is_woff_document(self, document):
		return isinstance(document, FontFile)
	
	#def scan_document_links(self, document):
	#	if self.is_woff_document(document):
	#		return []
	#	else:
	#		return NotImplemented


if __debug__ and __name__ == '__main__':
	from base64 import b64decode
	from format.plain import PlainFormat
	
	print("WOFF font")
	
	data = '''d09GRgABAAAAAAToAA0AAAAAB2QAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAABGRlRNAAAEzAAAABoA
AAAcdNA2t0dERUYAAASwAAAAHAAAAB4AJwANT1MvMgAAAZwAAABLAAAAVk/2/bJjbWFwAAAB+AAA
AFkAAAFiIhFFt2dhc3AAAASoAAAACAAAAAj//wADZ2x5ZgAAAmQAAAE1AAACLD+btmBoZWFkAAAB
MAAAAC8AAAA2AAEx+2hoZWEAAAFgAAAAHAAAACQD5QIFaG10eAAAAegAAAAQAAAAFgZKAEpsb2Nh
AAACVAAAABAAAAAQATYBoG1heHAAAAF8AAAAHQAAACAASwBHbmFtZQAAA5wAAADcAAABbgUngcJw
b3N0AAAEeAAAAC4AAABFOXjBpHicY2BkYGAA4nOXRBnj+W2+MnAzMYDA+cKKejityqDKeJvxNpDL
wQCWBgAX4wnfAHicY2BkYGC8zcDAoMfEAAJANiMDKmABADBkAe94nGNgZGBgYGdwYWBiAAEQycgA
EnMA8xkACcgAkwAAAHicY2BkYmCcwMDKwMHow5jGwMDgDqW/MkgytDAwMDGwcjKAQQMDAyOQUmCA
goA01xQGB4ZExUmMD/4/YNBjvP3/NgNEDQMArQgM7AB4nGNigAAmCFaFQAACwgCbeJxjYGBgZoBg
GQZGBhCIAfIYwXwWBgcgzcPAwcAEZDMwJCooKU5QnPT/P1gdEu//ovuP7pXeK4GaAAeMbAxwIUYm
IMHEgKaAgXLATAUzWKhgBg4AAEdEDyUAAAAAAAAAAAAAAABmAIoA0AEWeJx1kF1Og0AQx3cKu0CX
lNAu1LQsKg3QDxIaQEj6YB88RPvkHXz3oeml9By+cgjjDdwtilbqTjKZ2f3PzG8HAQpRCDXU6AEh
cBhZQRBHW4hmgUaksbErLc+qsirz7Bpch8n7mZBJK+S9fBGqqhy7UPf1AyXYmC833POGzKTUZEPP
44F/MyKgKrHSu10tijRKJlNm22w6SaJ0GS94qJsUXg56n1IjjpuqTdPCGniKKFR6asxYU/LY1Fu2
F+oqQeL8/GUkshNl0CJKPqi5n62f15nPvwO4P0tlgHptnyuUIBRW5V2RQuPFXiwgTKwhz8pLI+ac
kN2OEI51DR8JOWJNf+2MffKxZqj7vWpo2MdCNxDCty7KX5YtlC2EIyi0k/+H5eNrPP6F9N5FaYbj
M6JLKJ/+rU60AAAAeJxtjj1qw0AQhT/ZkkN+SJEi9dqlQUISqlym0AFSuDdmESJCgpV9j1SpUuUY
OUAOkBPl7XohRbKwzPeGN/MGuOONBP8SMqkLL7hiE3nJmjFyKs975IxbPiOvpL7lTNJrdW7ClOcF
9zxEXvLENnIqz2vkjEc+Iq/U/2JmoOfIC8xDf1R5xtJxVv+Ak7TdeTgIWibddgrVyWEx1BSUqjv9
300XXdGQh1/L4xXtNJ7ayXXW1EVpdiYkqlZN3uR1Wcny9569kpz6fcj3e30me+vmfhpNVZT/TP0A
jaoyRXicY2BiQAaMDOiAHSzKxODC0M7IxMjMmVhUlF+ek5pWwgVmFWWmZ5QAAG4pCRIAAAAAAAH/
/wACeJxjYGRgYOABYjEgZmJgBEI2IGYB8xgAA+AANXicY2BgYGQAgqtvXXeA6POFFfUwGgBRNgcv
AAA='''
	
	class Model(WOFFFont, PlainFormat):
		font_dir = Path('~/.cache/guixmpp-fonts').expanduser()
		
		def create_document(self, data:bytes, mime_type):
			if mime_type == 'application/x-font-woff' or mime_type == 'application/font-woff':
				return WOFFFont.create_document(self, data, mime_type)
			else:
				return PlainFormat.create_document(self, data, mime_type)
	
	Model.font_dir.mkdir(parents=True, exist_ok=True)
	
	model = Model()
	
	font = model.create_document(b64decode(data), 'application/font-woff')
	assert font.name() == "slick"

