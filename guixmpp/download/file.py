#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'FileDownload',


if __name__ == '__main__':
	from guixmpp.gtkaiopath import Path
else:
	from ..gtkaiopath import Path

from urllib.parse import unquote
import magic
import mimetypes
from asyncio import get_running_loop


class FileDownload:
	"""
	Downloader that supports `file` uri scheme. Files are searched in the local filesystem.
	MIME types are guessed by `mimetypes` library.
	"""
	
	async def begin_downloads(self):
		if not mimetypes.inited:
			mimetypes.init()
		pass
	
	async def end_downloads(self):
		pass
	
	async def download_document(self, url):
		if not url.startswith('file:'):
			return NotImplemented
		
		if not mimetypes.inited:
			raise RuntimeError("Run `mimetypes.init()` first.")
		
		components = url.split('/')
		assert components[0] == 'file:'
		if components[1]: # KDE format file:/path/to/file.ext
			if components[2] == '.': # relative path
				path_name = '/'.join(components[1:])
			else: # absolute path
				path_name = '/' + '/'.join(components[1:])
		else: # file://<host>/path/to/file.ext
			host = components[2]
			if not host or host == 'localhost': # absolute path
				path_name = '/' + '/'.join(components[3:])
			elif host == '.': # relative path
				path_name = '/'.join(components[3:])
			else:
				raise ValueError("Only localhost files are supported.")
		
		path = Path(unquote(path_name))
		mime_type, encoding = mimetypes.guess_type(str(path)) # TODO: Run in executor? Possible blocking io.
		#mime_type = await get_running_loop().run_in_executor(None, (lambda _filename: magic.from_file(_filename, mime=True)), str(path))
		if not mime_type:
			mime_type = 'application/octet-stream'
		
		return await path.read_bytes(), mime_type


if __debug__ and __name__ == '__main__':
	from asyncio import run, set_event_loop_policy
	from guixmpp.mainloop import loop_init
	
	loop_init()
	
	print("file download")
	
	async def test_main():
		download = FileDownload()
		await download.begin_downloads()
		
		async for filepath in (Path.cwd() / 'examples/gfx').iterdir():
			data, mime_type = await download.download_document(filepath.as_uri())
			if filepath.suffix[-1] == '_':
				assert mime_type == 'application/octet-stream', mime_type
			elif filepath.suffix == '.xml':
				assert mime_type == 'application/xml', mime_type
			elif filepath.suffix == '.svg':
				assert mime_type == 'image/svg+xml', mime_type
			elif filepath.suffix == '.css':
				assert mime_type == 'text/css', f"{filepath.as_uri()} : {mime_type}"
			elif filepath.suffix == '.png':
				assert mime_type == 'image/png', mime_type
			elif filepath.suffix == '.jpeg':
				assert mime_type == 'image/jpeg', mime_type
			elif filepath.suffix == '.bmp':
				assert mime_type == 'image/bmp', mime_type
			elif filepath.suffix == '.txt':
				assert mime_type == 'text/plain', mime_type
				if filepath.name == 'test.txt':
					assert data == b"hello, void\n"
			else:
				raise NotImplementedError(filepath)
		
		try:
			data, mime_type = await download.download_document((Path.cwd() / 'nonexistent-file.whatever').as_uri())
		except Exception as error:
			print("Error for nonexistent file:", error)
		else:
			assert False, "Should raise error for nonexistent file."
		
		await download.end_downloads()
	
	run(test_main())


