#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'FontDocument', 'FontFormat', 'TTLibError'


from io import BytesIO
from itertools import product
from fontTools import ttLib
from fontconfig import Config, query
from aiopath import Path
from hashlib import sha3_256
from asyncio import get_running_loop, Lock


TTLibError = ttLib.TTLibError

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
	def magic_version(self):
		return self.data[:5]
	
	@property
	def font_family(self):
		with ttLib.TTFont(BytesIO(self.data)) as font:
			table = font['name']
			
			for name_id, (plat_id, enc_id, lang_id) in product((PREFERRED_FAMILY, LEGACY_FAMILY), (WINDOWS_ENGLISH_IDS, MAC_ROMAN_IDS)):
				family_name_rec = table.getName(nameID=name_id, platformID=plat_id, platEncID=enc_id, langID=lang_id)
				if family_name_rec is not None:
					break
			else:
				raise ValueError("Family name not found.")
			return family_name_rec.toUnicode()
	
	@font_family.setter
	def font_family(self, value):
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
					"The Truetype Unique ID rec may contain either the PostScript Name or the Full Name string, so we try both."
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


class FontFormat:
	def __init__(self, *args, font_dir=None, **kwargs):
		if not font_dir:
			font_dir = '~/.cache/guixmpp-fonts'
		self.font_dir = font_dir
		self.__config = Config.get_current()
		self.__lock = Lock()
	
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
	
	async def install_font(self, font_doc, font_family):
		"Install the provided font doc to use under the specified font family."
		
		font_family = font_family.replace(':', '_')
		print("install_font", font_family)
		
		font_dir = await Path(self.font_dir).expanduser()
		await font_dir.mkdir(parents=True, exist_ok=True)
		font_url = self.get_document_url(font_doc)
		file_name = sha3_256((font_family + '@' + font_url).encode('utf-8')).hexdigest()[:16]
		file_path = font_dir / (file_name + '.' + font_doc.format_)
		
		if not await file_path.is_file():
			print(" installing font:", font_family, file_name, font_url[:96])
			font_doc.font_family = font_family # font family inside the font file might be different, so change it
			await file_path.write_bytes(font_doc.data)
		
		async with self.__lock:
			await get_running_loop().run_in_executor(None, self.__config.app_font_add_file, str(file_path))
		
		assert await self.is_font_installed(font_family), f"Failed to install font: {font_family}"
		print(" font installed:", font_family)
	
	async def is_font_installed(self, font_family):
		async with self.__lock:
			return bool(await get_running_loop().run_in_executor(None, query, ':family=' + font_family))
	
	async def uninstall_fonts(self):
		async with self.__lock:
			await get_running_loop().run_in_executor(None, self.__config.app_font_clear)


if __name__ == '__main__':
	from base64 import b64decode
	from asyncio import run
	
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
	
	async def main():
		model = Model()
		font = model.create_document(b64decode(data), 'font/woff')
		assert font.font_family == "slick", "default font family should be 'slick'"
		font.font_family = "burp"
		assert font.font_family == "burp", "font family after name change should be 'burp'"
		assert not query(':family=slick'), "font 'slick' should not be installed by default"
		await model.install_font(font, "slick")
		assert await model.is_font_installed('slick'), "font should be installed under font family name 'slick'"
		await model.uninstall_fonts()
		assert not query(':family=slick'), "font 'slick' should be uninstalled"
	
	run(main())
