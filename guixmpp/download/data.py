#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DataDownload',


from base64 import b64decode
from urllib.parse import unquote


class DataDownload:
	"Downloader that supports `data` uri scheme, where the content is provided in the uri itself."
	
	async def download_document(self, url) -> (bytes, str):
		if not url.startswith('data:'):
			return NotImplemented
		
		headers = url[url.index(':') + 1 : url.index(',')].split(';')
		
		try:
			mime_type = headers[0]
			if mime_type == '':
				mime_type = 'application/octet-stream'
		except IndexError:
			mime_type = 'application/octet-stream'
		
		charset = 'utf-8'
		for h in headers[1:]:
			if h.startswith('charset='):
				charset = h.split('=')[1]
		
		data = url[url.index(',') + 1 :]
		
		if ('base64' in headers[1:]):
			data = b64decode(data)
		else:
			data = unquote(data).encode(charset)
		
		return data, mime_type


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("data download")
	
	model = DataDownload()
	assert run(model.download_document('data:,hello,void')) == (b"hello,void", 'application/octet-stream')


