#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ResourceDownload',


class BadResourceUrlError(Exception):
	pass


class ResourceDownload:
	"Downloader that serves in-app generated content, available under `resource:` uri scheme."
	
	def __init__(self, *args, **kwargs):
		self.create_resource = kwargs.get('create_resource', None)
	
	async def download_document(self, url) -> (bytes, str):
		if not url.startswith('resource:'):
			return NotImplemented
		
		if self.create_resource:
			result, mime = await self.create_resource(self, url)
		else:
			raise BadResourceUrlError(url)
		return result, mime


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("resource download")
	
	def f(a, b):
		return ('f', int(a) + int(b), int(a) - int(b))
	
	def g(a, b):
		return ('g', b, a)
	
	funs = {'f':f, 'g':g}
	
	async def create_resource(model, url):
		scheme, realm, server, *path = url.split('/')
		assert scheme == 'resource:'
		assert realm == ''
		assert server == 'app'
		path = '/'.join(path)
		path, *query = path.split('?')
		query = '?'.join(query)
		query = dict(_q.split('=') for _q in query.split('&'))
		return funs[path](**query), 'application/x-whatever'
	
	model = ResourceDownload(create_resource=create_resource)
	
	async def main():
		print(await model.download_document('resource://app/f?a=1&b=2'))
		print(await model.download_document('resource://app/f?a=50&b=0'))
		print(await model.download_document('resource://app/g?a=aaa&b=bbb'))
	
	run(main())


