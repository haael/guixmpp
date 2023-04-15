#!/usr/bin/python3


from collections.abc import Iterable
from typing import Protocol, NewType, runtime_checkable


Document = NewType('Document')


@runtime_checkable
class Model(Protocol):
	def create_document(self, data:bytes|str, mime:str) -> Document:
		pass


@runtime_checkable
class Format(Protocol):
	def scan_document_links(self, doc:Document) -> Iterable[str]:
		pass
	
	def transform_document(self, doc:Document) -> Self:
		pass


@runtime_checkable
class Download(Protocol):
	def download_document(self, url:str):
		pass
	
	def get_document(self, url:str) -> Document:
		pass


@runtime_checkable
class Render(Protocol):
	def render_document(self, doc:Document, ctx:cairo.Context) -> None:
		pass

