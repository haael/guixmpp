#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'DataDownload',


from base64 import b64decode
from urllib.parse import unquote


class DataDownload:
	async def download_document(self, url) -> (bytes, str):
		if url.startswith('data:'):
			headers = url[url.index(':') + 1 : url.index(',')].split(';')
			
			try:
				mime_type = headers[0]
				if mime_type == '':
					mime_type = 'application/octet-stream'
			except IndexError:
				mime_type = 'application/octet-stream'
			
			try:
				encoding = headers[1]
			except IndexError:
				encoding = ''
			
			raw_data = url[url.index(',') + 1 :]
			if encoding == 'base64':
				data = b64decode(raw_data)
			elif encoding == '':
				data = unquote(raw_data).encode('utf-8')
			elif encoding.startswith('charset='):
				data = unquote(raw_data).encode(encoding.split('=')[1])
			else:
				print("unknown encoding", encoding)
				data = None
			
			return data, mime_type
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("data download")
	
	model = DataDownload()
	assert run(model.download_document('data:,hello,void')) == (b"hello,void", 'application/octet-stream')


