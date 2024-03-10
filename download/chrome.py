#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ChromeDownload',


from aiopath import Path


class ChromeDownload:
	def __init__(self, *args, **kwargs):
		self.chrome_dir = Path(kwargs.get('chrome_dir', 'chrome'))
	
	async def download_document(self, url) -> (bytes, str):
		if not url.startswith('chrome:'):
			return NotImplemented
		
		path = self.chrome_dir / url[9:]
		if await path.is_file():
			if path.suffix == '.css':
				return await path.read_bytes(), 'text/css'
			else:
				return await path.read_bytes(), 'application/octet-stream'
		else:
			raise ValueError("Chrome resource not found.")


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("chrome download")
	
	model = ChromeDownload()
	assert run(model.download_document('chrome://nonexistent')) == (b"", 'application/x-null')


