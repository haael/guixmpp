#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ChromeDownload',


if __name__ == '__main__':
	from guixmpp.gtkaiopath import Path
else:
	from ..gtkaiopath import Path


class ChromeDownload:
	"""
	Downloader supporting `chrome` url scheme, i.e. various resources needed by application.
	The default implementations searches for files in `chrome_dir` argument provided to the
	model, or `./chrome` directory if argument is not present. MIME types are determined
	from file extension.
	"""
	
	def __init__(self, *args, **kwargs):
		self.chrome_dir = Path(kwargs.get('chrome_dir', 'chrome'))
	
	async def download_document(self, url) -> (bytes, str):
		if not url.startswith('chrome:'):
			return NotImplemented
		
		path = self.chrome_dir / url[9:]
		if path.suffix == '.css':
			mime = 'text/css'
		elif path.suffix in ('.jpeg', '.jpg'):
			mime = 'image/jpeg'
		elif path.suffix in ('.png'):
			mime = 'image/png'
		elif path.suffix in ('.svg'):
			mime = 'image/svg'
		else:
			mime = 'application/octet-stream'
		return await path.read_bytes(), mime


if __debug__ and __name__ == '__main__':
	from asyncio import run
	#from aiopath import Path
	
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


