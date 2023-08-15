#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ChromeDownload',


class ChromeDownload:
	async def download_document(self, url) -> (bytes, str):
		if url.startswith('chrome:'): # TODO: implement chrome docs	
			return b"", 'application/x-null'
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("chrome download")
	
	model = ChromeDownload()
	assert run(model.download_document('chrome://nonexistent')) == (b"", 'application/x-null')


