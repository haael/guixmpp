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
		if path.suffix == '.css':
			mime = 'text/css'
		else:
			mime = 'application/octet-stream'
		return await path.read_bytes(), mime


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("chrome download")
		
	async def main():
		model = ChromeDownload()
		
		(await model.download_document('chrome://html.css'))[1] == 'text/css'
		
		try:
			await model.download_document('chrome://nonexistent')
		except Exception as error:
			print("Error for nonexistent chrome resource:", error)
		else:
			assert False, "Should return error for nonexistent chrome resource."
	
	run(main())

