#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'CIDDownload',


class BadCIDUrlError(Exception):
	pass


class CIDDownload:
	"Downloader that serves in-app generated content, available under `resource:` uri scheme."
	
	def __init__(self, *args, **kwargs):
		self.__client = None
	
	def set_xmpp_client(self, client):
		self.__client = client
	
	async def download_document(self, url) -> (bytes, str):
		if not url.startswith('cid:'):
			return NotImplemented
		
		if self.__client is not None:
			result, mime = await self.__client.get_resource(url)
		else:
			result, mime = b'', 'application/x-null'
		
		return result, mime


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("CID download")
	
	model = CIDDownload()
	client = XMPPClient('haael@dw.live/discovery')
	
	async def main():
			client.set_resource('cid:test@bob.xmpp.org', b"hello void", 'text/plain')
			model.set_xmpp_client(client)
			print(await model.get_resource('cid:test@bob.xmpp.org'))
	
	run(main())


