#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'FileDownload',


from pathlib import Path
import mimetypes
from urllib.parse import unquote


class FileDownload:
	def download_document(self, url):
		if url.startswith('file:'):
			path = Path(unquote(url[5:]))
			if not mimetypes.inited:
				raise RuntimeError("Call mimetypes.init() first.")
			mime_type, encoding = mimetypes.guess_type(str(path))
			return path.read_bytes(), mime_type
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	print("file download")
	
	mimetypes.init()
	
	download = FileDownload()
	for filepath in Path('gfx').iterdir():
		data, mime_type = download.download_document('file:' + str(filepath))
		if filepath.suffix == '.xml':
			assert mime_type == 'application/xml', mime_type
		elif filepath.suffix == '.svg':
			assert mime_type == 'image/svg+xml', mime_type
		elif filepath.suffix == '.css':
			assert mime_type == 'text/css', mime_type
		elif filepath.suffix == '.png':
			assert mime_type == 'image/png', mime_type
		elif filepath.suffix == '.jpeg':
			assert mime_type == 'image/jpeg', mime_type
		elif filepath.suffix == '.txt':
			assert mime_type == 'text/plain', mime_type
			if filepath.name == 'test.txt':
				assert data == b"hello, void\n"
		else:
			raise NotImplementedError(filepath)




