#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'FileDownload',


from aiopath import AsyncPath as Path
import mimetypes
from urllib.parse import unquote


class FileDownload:
	async def begin_downloads(self):
		if not mimetypes.inited:
			mimetypes.init()
	
	async def end_downloads(self):
		pass
	
	async def download_document(self, url):
		if not mimetypes.inited:
			raise RuntimeError("Run `mimetypes.init()` first.")
		
		if url.startswith('file:'):
			print("open file", url)
			path = Path(unquote(url[5:]))
			mime_type, encoding = mimetypes.guess_type(str(path))
			try:
				return await path.read_bytes(), mime_type
			except IOError as error:
				#print(error)
				return None, 'application/x-null'
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("file download")
	
	async def test_main():
		download = FileDownload()
		await download.begin_downloads()
		
		async for filepath in (Path.cwd() /'gfx').iterdir():
			data, mime_type = await download.download_document(filepath.as_uri())
			if filepath.suffix == '.xml':
				assert mime_type == 'application/xml', mime_type
			elif filepath.suffix == '.svg':
				assert mime_type == 'image/svg+xml', mime_type
			elif filepath.suffix == '.css':
				assert mime_type == 'text/css', mime_type
			elif filepath.suffix == '.png':
				assert mime_type == 'image/png', mime_type
			elif filepath.suffix == '.jpeg':
				assert mime_type == 'image/jpeg', mime_type
			elif filepath.suffix == '.txt':
				assert mime_type == 'text/plain', mime_type
				if filepath.name == 'test.txt':
					assert data == b"hello, void\n"
			else:
				raise NotImplementedError(filepath)
		
		await download.end_downloads()
	
	run(test_main())


