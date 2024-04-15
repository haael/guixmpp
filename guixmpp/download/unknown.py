#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'UnknownDownload',


class UnsupportedSchemeError(Exception):
	pass


class UnknownDownload:
	"Download handler for unsupported url schemes. Include it to make unsupported schemes non-fatal."
	
	async def download_document(self, url) -> (bytes, str):
		raise UnsupportedSchemeError(url)


if __debug__ and __name__ == '__main__':
	from asyncio import run
	
	print("unknown download")
		
	async def main():
		model = UnknownDownload()
		
		try:
			await model.download_document('scheme://unknown')
		except UnsupportedSchemeError as error:
			print("Error for unknown url scheme:", error)
		else:
			assert False, "Should return error for unknown url scheme."
	
	run(main())


