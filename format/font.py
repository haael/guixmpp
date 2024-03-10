#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'FondDocument', 'FontFormat'


from io import BytesIO
from itertools import product
from fontTools import ttLib


WINDOWS_ENGLISH_IDS = 3, 1, 0x409
MAC_ROMAN_IDS = 1, 0, 0
LEGACY_FAMILY = 1
TRUETYPE_UNIQUE_ID = 3
FULL_NAME = 4
POSTSCRIPT_NAME = 6
PREFERRED_FAMILY = 16
WWS_FAMILY = 21


class FontDocument:
	def __init__(self, data, format_):
		self.data = data
		self.format_ = format_
	
	@property
	def name(self):
		with ttLib.TTFont(BytesIO(self.data)) as font:
			table = font['name']
			
			for name_id, (plat_id, enc_id, lang_id) in product((PREFERRED_FAMILY, LEGACY_FAMILY), (WINDOWS_ENGLISH_IDS, MAC_ROMAN_IDS)):
				family_name_rec = table.getName(nameID=name_id, platformID=plat_id, platEncID=enc_id, langID=lang_id)
				if family_name_rec is not None:
					break
			else:
				raise ValueError("Family name not found.")
			return family_name_rec.toUnicode()
	
	@name.setter
	def name(self, value):
		with ttLib.TTFont(BytesIO(self.data)) as font:
			table = font['name']
			
			for name_id, (plat_id, enc_id, lang_id) in product((PREFERRED_FAMILY, LEGACY_FAMILY), (WINDOWS_ENGLISH_IDS, MAC_ROMAN_IDS)):
				family_name_rec = table.getName(nameID=name_id, platformID=plat_id, platEncID=enc_id, langID=lang_id)
				if family_name_rec is not None:
					break
			else:
				raise ValueError("Family name not found.")
			
			ps_name = family_name_rec.toUnicode().replace(' ', '')
			
			for rec in table.names:
				name_id = rec.nameID
				if name_id == POSTSCRIPT_NAME:
					rec.string = value.replace(' ', '')
				elif name_id == TRUETYPE_UNIQUE_ID:
					# The Truetype Unique ID rec may contain either the PostScript
					# Name or the Full Name string, so we try both
					if ps_name in rec.toUnicode():
						rec.string = value.replace(' ', '')
					else:
						rec.string = value
				elif name_id in (LEGACY_FAMILY, FULL_NAME, PREFERRED_FAMILY, WWS_FAMILY):
					rec.string = value
			
			stream = BytesIO()
			font.save(stream)
			self.data = stream.getvalue()
			stream.close()
	
	#async def install(self, dir_path):
	#	await (dir_path / (self.name + '.' + self._format)).write_bytes(self.data)


class FontFormat:
	def create_document(self, data:bytes, mime_type):
		if mime_type in ['font/woff', 'application/font-woff', 'application/x-font-woff']:
			data = self.create_document(data, 'application/octet-stream')
			return FontDocument(data, 'woff')
		elif mime_type == 'font/woff2':
			data = self.create_document(data, 'application/octet-stream')
			return FontDocument(data, 'woff2')
		elif mime_type in ['font/ttf', 'font/sfnt', 'application/font-sfnt', 'application/x-font-sfnt', 'application/font-ttf', 'application/x-font-ttf']:
			data = self.create_document(data, 'application/octet-stream')
			return FontDocument(data, 'ttf')
		elif mime_type == 'font/otf':
			data = self.create_document(data, 'application/octet-stream')
			return FontDocument(data, 'otf')
		else:
			return NotImplemented
	
	def is_font_document(self, document):
		return isinstance(document, FontDocument)
	
	def scan_document_links(self, document):
		if self.is_font_document(document):
			return []
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from base64 import b64decode
	
	print("font format")
	
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
	
	class Model(FontFormat):
		def create_document(self, data:bytes, mime_type):
			if mime_type == 'font/woff':
				return FontFormat.create_document(self, data, mime_type)
			elif mime_type == 'application/octet-stream':
				return data
			else:
				raise NotImplementedError
	
	model = Model()
	font = model.create_document(b64decode(data), 'font/woff')
	assert font.name == "slick"
	font.name = "burp"
	assert font.name == "burp"

