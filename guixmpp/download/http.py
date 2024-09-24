#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTTPDownload',


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "http"


from os import environ, utime
_library = environ.get('GUIXMPP_HTTP', '2') # 1, 2, aiohttp, httpx

from hashlib import sha3_256
from mimetypes import inited as mimetypes_initialized, guess_type, guess_extension
from asyncio import gather, get_running_loop, to_thread
from time import strftime, gmtime


class HTTPDownloadCommon:
	def __init__(self, http_cache_dir=None, http_cache_fresh_time=None, http_cache_max_time=None, http_semaphore=None, **kwargs):
		self.http_cache_dir = http_cache_dir
		self.http_cache_fresh_time = http_cache_fresh_time
		self.http_cache_max_time = http_cache_max_time
		self.http_semaphore = http_semaphore
	
	async def download_document(self, url):
		if not (url.startswith('http:') or url.startswith('https:')):
			return NotImplemented
		
		if_modified_since = None
		
		if self.http_cache_dir is not None:
			cached_file = None
			
			code = sha3_256(url.encode('utf-8')).hexdigest()[2:16+2]
			cached_files = await self.http_cache_dir.glob(code + '.*')
			if len(cached_files) == 0:
				pass
			elif len(cached_files) == 1 and await cached_files[0].is_file():
				cached_file = cached_files[0]
				s = await cached_file.stat()
				t = get_running_loop().time()
				
				do_request = True
				if s.st_mtime > t - self.http_cache_fresh_time:
					do_request = False
				elif s.st_mtime > t - self.http_cache_max_time:
					if_modified_since = t - s.st_atime
				else:
					await cached_file.unlink()
				
				if not do_request:
					#print("cache hit")
					content_type = (await to_thread(guess_type, cached_file))[0]
					return await cached_file.read_bytes(), content_type
			else:
				await gather(*[_cached_file.unlink() for _cached_file in cached_files])
		
		request_headers = {}
		
		if if_modified_since is not None:
			request_headers['if-modified-since'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime(if_modified_since))
		
		if self.http_semaphore:
			async with self.http_semaphore:
				data, response_headers = await self.http_download_url(url, request_headers)
		else:
			data, response_headers = await self.http_download_url(url, request_headers)
		#print(len(data), response_headers)
		
		try:
			content_type = response_headers['content-type'].split(';')[0].strip()
		except KeyError:
			content_type = 'application/octet-stream'
		
		if self.http_cache_dir is not None:
			if cached_file and ((await to_thread(guess_type, cached_file))[0] != content_type):
				await cached_file.unlink()
			
			try:
				cache_control = frozenset(_s.strip().lower() for _s in response_headers['cache-control'].split(','))
			except KeyError:
				cache_control = frozenset()
			
			if 'no-store' in cache_control:
				return data, content_type
			
			cached_file = self.http_cache_dir / (code + guess_extension(content_type))
			await cached_file.write_bytes(data)
			
			try:
				max_age = int([_s for _s in cache_control if _s.startswith('max-age=')][0].split('=')[1])
			except IndexError:
				max_age = None
			
			t = get_running_loop().time()
			if 'must-revalidate' in cache_control or 'no-cache' in cache_control:
				if max_age is None:
					mtime = t - self.http_cache_fresh_time
				else:
					mtime = min(t - self.http_cache_max_time + max_age, t - self.http_cache_fresh_time)
			else:
				if max_age is None:
					mtime = None
				else:
					mtime = min(t - self.http_cache_fresh_time + max_age, t)
			
			if mtime is not None:
				await to_thread(utime, cached_file, (mtime, t))
		
		return data, content_type


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
	
	class HTTPDownload(HTTPDownloadCommon):
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
		
		async def http_download_url(self, url, headers):
			"Download document using HTTP client implementation provided in this library."
			
			if not (url.startswith('http:') or url.startswith('https:')):
				return NotImplemented
			
			_, _, host, *path = url.split('/')
			path = '/'.join(path)
			
			if (host in self.__client) and (not self.__client[host].is_eof()):
				connection = self.__client[host]
			else:
				if host in self.__client:
					await self.__client[host].close()
				connection = self.__client[host] = Connection(f'https://{host}')
				await connection.open()
			
			async with connection.Url(path).get(headers=headers) as request:
				status, headers = await request.response()
				request.raise_for_status(status)
				return (await request.read()), headers


elif _library == 'aiohttp':
	import aiohttp
	
	class HTTPDownload(HTTPDownloadCommon):
		async def begin_downloads(self):
			"Create client session."
			assert not hasattr(self, '_HTTPDownload__client')
			self.__client = aiohttp.ClientSession()
		
		async def end_downloads(self):
			"Cleanup client session."
			await self.__client.close()
			del self.__client
		
		async def http_download_url(self, url, headers): # TODO
			"Use `aiohttp` to download document."
			
			if not (url.startswith('http:') or url.startswith('https:')):
				return NotImplemented
			async with self.__client.get(url) as response:
				response.raise_for_status()
				#try:
				#	ct = response.headers['content-type'].split(';')[0].strip()
				#except KeyError:
				#	ct = 'application/octet-stream'
				return (await response.read()), response.headers


elif _library == 'httpx':
	import httpx
	
	class HTTPDownload(HTTPDownloadCommon):
		async def begin_downloads(self):
			"Create client session."
			assert not hasattr(self, '_HTTPDownload__client')
			self.__client = httpx.AsyncClient()
		
		async def end_downloads(self):
			"Cleanup client session."
			await self.__client.aclose()
			del self.__client
		
		async def http_download_url(self, url, headers): # TODO
			"Use `httpx` to download document."
			
			if not (url.startswith('http:') or url.startswith('https:')):
				return NotImplemented
			result = await self.__client.get(url)
			#try:
			#	ct = result.headers['content-type'].split(';')[0].strip()
			#except KeyError:
			#	ct = 'application/octet-stream'
			return result.content, result.headers


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

