#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTTPDownload',


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "http"


from os import environ
_library = environ.get('GUIXMPP_HTTP', '2') # 1, 2, aiohttp, httpx

if _library in ['1', '2']:
	if __name__ == '__main__':
		from guixmpp.protocol.http.client import HTTPError, ResolveError
		if _library == '1':
			from guixmpp.protocol.http.client import Connection1 as Connection
		elif _library == '2':
			from guixmpp.protocol.http.client import Connection2 as Connection
	else:
		from ..protocol.http.client import HTTPError, ResolveError
		if _library == '1':
			from ..protocol.http.client import Connection1 as Connection
		elif _library == '2':
			from ..protocol.http.client import Connection2 as Connection
	
	from asyncio import gather
	
	class HTTPDownload:
		"""
		Downloader supporting `http` url scheme. Supports http and https connections
		and http version 1.1 or 2, depending on configuration.
		"""
		
		async def begin_downloads(self):
			"Create client dict. Downloaded will use one connection per host, created on demand."
			assert not hasattr(self, '_HTTPDownload__client')
			self.__client = {}
		
		async def end_downloads(self):
			"Close all connections to all hosts."
			await gather(*[_connection.close() for _connection in self.__client.values()])
			del self.__client
		
		async def download_document(self, url):
			"Download document using HTTP client implementation provided in this library."
			
			if not (url.startswith('http:') or url.startswith('https:')):
				return NotImplemented
			
			_, _, host, *path = url.split('/')
			path = '/'.join(path)
			
			if (host in self.__client) and (not self.__client[host].is_eof()):
				connection = self.__client[host]
			else:
				connection = self.__client[host] = Connection(f'https://{host}')
				await connection.open()
			
			async with connection.Url(path).get() as request:
				status, headers = await request.response()
				request.raise_for_status(status)
				try:
					ct = headers['content-type'].split(';')[0].strip()
				except KeyError:
					ct = 'application/octet-stream'
				return (await request.read()), ct


elif _library == 'aiohttp':
	import aiohttp
	
	class HTTPDownload:
		async def begin_downloads(self):
			"Create client session."
			assert not hasattr(self, '_HTTPDownload__client')
			self.__client = aiohttp.ClientSession()
		
		async def end_downloads(self):
			"Cleanup client session."
			await self.__client.close()
			del self.__client
		
		async def download_document(self, url):
			"Use `aiohttp` to download document."
			
			if not (url.startswith('http:') or url.startswith('https:')):
				return NotImplemented
			async with self.__client.get(url) as response:
				response.raise_for_status()
				try:
					ct = response.headers['content-type'].split(';')[0].strip()
				except KeyError:
					ct = 'application/octet-stream'
				return (await response.read()), ct


elif _library == 'httpx':
	import httpx
	
	class HTTPDownload:
		async def begin_downloads(self):
			"Create client session."
			assert not hasattr(self, '_HTTPDownload__client')
			self.__client = httpx.AsyncClient()
		
		async def end_downloads(self):
			"Cleanup client session."
			await self.__client.aclose()
			del self.__client
		
		async def download_document(self, url):
			"Use `httpx` to download document."
			
			if not (url.startswith('http:') or url.startswith('https:')):
				return NotImplemented
			result = await self.__client.get(url)
			try:
				ct = result.headers['content-type'].split(';')[0].strip()
			except KeyError:
				ct = 'application/octet-stream'
			return result.content, ct


if __debug__ and __name__ == '__main__':
	from asyncio import run, set_event_loop_policy
	from guixmpp.mainloop import loop_init
	
	loop_init()
	
	print("http download")
	
	async def test_main():
		model = HTTPDownload()
		await model.begin_downloads()

		data, mime = await model.download_document('http://www.google.com/robots.txt')
		assert mime == 'text/plain', mime
		for line in data.split(b'\n'):
			print(line.decode('utf-8'))
		
		data, mime = await model.download_document('https://www.google.com/sitemap.xml')
		assert mime == 'text/xml', mime
		for line in data.split(b'\n'):
			print(line.decode('utf-8'))
		
		assert await model.download_document('https://gist.githubusercontent.com/prabansal/115387/raw/0e5911c791c03f2ffb9708d98cac70dd2c1bf0ba/HelloWorld.txt') == (b"Hi there", 'text/plain')
		
		try:
			data, mime = await model.download_document('https://www.google.com/nonexistent-url.whatever')
		except Exception as error:
			print("Nonexistent url error:", error)
		else:
			assert False, "Should return 404 error."
		
		await model.end_downloads()
	
	run(test_main())

