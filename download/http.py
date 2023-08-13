#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTTPDownload',


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "http"


import httpx


class HTTPDownload:
	def download_document(self, url):
		if url.startswith('http:') or url.startswith('https:'):
			result = httpx.get(url)
			return result.content, result.headers['content-type'].split(';')[0].strip()
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	print("http download")
	
	model = HTTPDownload()
	assert model.download_document('https://gist.githubusercontent.com/prabansal/115387/raw/0e5911c791c03f2ffb9708d98cac70dd2c1bf0ba/HelloWorld.txt') == (b"Hi there", 'text/plain')
