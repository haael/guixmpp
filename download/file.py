#!/usr/bin/python3.11
#-*- coding:utf-8 -*-


__all__ = 'FileDownload',


from pathlib import Path
import mimetypes


class FileDownload:
	def download_document(self, url):
		if url.startswith('file:'):
			path = Path(url[5:])
			if not mimetypes.inited:
				raise RuntimeError("Call mimetypes.init() first.")
			mime_type, encoding = mimetypes.guess_type(str(path))
			return path.read_bytes(), mime_type
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	#from abc_types import Download
	#assert issubclass(FileDownload, Download)
	
	mimetypes.init()
	
	download = FileDownload()
	for filepath in Path('gfx').iterdir():
		data, mime_type = download.download_document('file:' + str(filepath))
		print(filepath, len(data), mime_type)




