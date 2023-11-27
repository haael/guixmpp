#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTTPDownload',


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "http"


_library = ''


if _library == '':
	from protocol.http.client import Connection1, Connection2, HTTPError, ResolveError
	from asyncio import gather
	
	class HTTPDownload:
		async def begin_downloads(self):
			#print('begin_downloads')
			assert not hasattr(self, '_HTTPDownload__client')
			self.__client = {}
		
		async def end_downloads(self):
			#print('end_downloads')
			await gather(*[_connection.close() for _connection in self.__client.values()])
			del self.__client
		
		async def download_document(self, url):
			if url.startswith('http:') or url.startswith('https:'):
				_, _, host, *path = url.split('/')
				path = '/'.join(path)
				
				if host in self.__client:
					connection = self.__client[host]
				else:
					connection = self.__client[host] = Connection1(f'https://{host}')
					await connection.open()
				
				async with connection.Url(path).get() as request:
					status, headers = await request.response()
					request.raise_for_status(status)
					return (await request.read()), headers['content-type'].split(';')[0].strip()
			
			else:
				return NotImplemented


elif _library == 'aiohttp':
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


elif _library == 'httpx':
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


if __debug__ and __name__ == '__main__':
	from asyncio import run, set_event_loop_policy
	from gtkaio import GtkAioEventLoopPolicy
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
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
		await model.end_downloads()
	
	run(test_main())

