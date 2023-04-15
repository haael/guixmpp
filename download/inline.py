#!/usr/bin/python3.11
#-*- coding:utf-8 -*-


__all__ = 'InlineDownload',


class InlineDownload:
	def download_document(self, url) -> bytes:
		if url.startswith('data:'):
			headers = url[url.index(':') + 1 : url.index(',')].split(';')
			
			try:
				mime_type = headers[0]
				if mime_type == '':
					mime_type = 'text/plain'
			except IndexError:
				mime_type = 'text/plain'
			
			try:
				encoding = headers[1]
			except IndexError:
				encoding = ''
			
			raw_data = url[url.index(',') + 1 :]
			if encoding == 'base64':
				from base64 import b64decode
				data = b64decode(raw_data)
			elif encoding == '':
				from urllib.parse import unquote
				data = unquote(raw_data).encode('utf-8')
			
			return data, mime_type
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	model = InlineDownload()
	assert model.download_document('data:,hello,void') == "hello,void"


