#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTTPDownload',


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "http"


import aiohttp


class HTTPDownload:
	async def begin_downloads(self):
		assert not hasattr(self, '_HTTPDownload__client')
		self.__client = aiohttp.ClientSession()
	
	async def end_downloads(self):
		await self.__client.close()
		del self.__client
	
	async def download_document(self, url):
		if url.startswith('http:') or url.startswith('https:'):
			async with self.__client.get(url) as response:
				response.raise_for_status()
				return (await response.read()), response.headers['content-type'].split(';')[0].strip()
		else:
			return NotImplemented

'''
import httpx


class HTTPDownload:
	async def begin_downloads(self):
		assert not hasattr(self, '_HTTPDownload__client')
		self.__client = httpx.AsyncClient()
	
	async def end_downloads(self):
		await self.__client.aclose()
		del self.__client
	
	async def download_document(self, url):
		if url.startswith('http:') or url.startswith('https:'):
			result = await self.__client.get(url)
			return result.content, result.headers['content-type'].split(';')[0].strip()
		else:
			return NotImplemented
'''

if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("http download")
	
	async def test_main():
		model = HTTPDownload()
		await model.begin_downloads()
		assert await model.download_document('https://gist.githubusercontent.com/prabansal/115387/raw/0e5911c791c03f2ffb9708d98cac70dd2c1bf0ba/HelloWorld.txt') == (b"Hi there", 'text/plain')
		await model.end_downloads()
	
	run(test_main())

