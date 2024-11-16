#!/usr/bin/python3

"""
This is a simple dnsclient that supports A, AAAA, MX, SOA, NS and CNAME
queries written in python.
"""

# TODO: support SRV records


import asyncio
import asyncio.protocols
import socket
from random import randrange
from collections import defaultdict

try:
	from .query import create_dns_query
	from .reply import parse_dns_reply, get_serial
except ImportError: # allow testing
	from query import create_dns_query
	from reply import parse_dns_reply, get_serial


class SyncResolver:
	def __init__(self):
		self.server = [('127.0.0.53', 53)]
		#self.cache = defaultdict(set)
	
	def resolve(self, name, type_):
		serial = randrange(2**16)
		query = create_dns_query(name, type_, serial)
		self.sock.sendto(query, self.server[0])
		reply, l = self.sock.recvfrom(1024)
		result, ll = parse_dns_reply(reply)
		if result.header.x_id != serial:
			raise ValueError
		
		addrs = []
		for answer in result.answer:
			if answer.name == name and answer.x_type == type_:
				addrs.append(answer.rdata)
			#self.cache[answer.name, answer.x_type].add((answer.rdata, t + answer.ttl))
		return addrs
	
	def __enter__(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return self
	
	def __exit__(self, *args):
		self.sock.close()
		del self.sock


class AsyncResolver(asyncio.protocols.DatagramProtocol):
	def __init__(self):
		self.retry = 3
		self.timeout = 3
		self.server = [('127.0.0.53', 53)]
		self.waiting = {}
		self.cache = defaultdict(set)
	
	def connection_made(self, transport):
		self.transport = transport
	
	def datagram_received(self, reply, addr):
		while reply:
			serial = get_serial(reply)
			
			if (serial not in self.waiting) or self.waiting[serial].done():
				return # warning
			
			try:
				result, l = parse_dns_reply(reply)
			except Exception as error:
				self.waiting[serial].set_exception(error)
				break
			else:
				self.waiting[serial].set_result(result)
				reply = reply[l:]
	
	def error_received(self, exc):
		if exc:
			raise exc # TODO: raise proper exception
	
	def connection_lost(self, exc):
		del self.transport
		if exc:
			raise exc # TODO: raise proper exception
	
	def prune_cache(self):
		t = self.loop.time()
		for addr, ttl in frozenset(self.cache[name, type_]):
			if ttl <= t:
				self.cache[name, type_].remove((addr, ttl))
				if not self.cache[name, type_]:
					del self.cache[name, type_]
	
	async def resolve(self, name, type_):
		t = self.loop.time()
		result = []
		for addr, ttl in frozenset(self.cache[name, type_]):
			if ttl > t:
				result.append(addr)
			else:
				self.cache[name, type_].remove((addr, ttl))
		
		if result:
			return result
		
		for n in range(self.retry):
			try:
				return await self.raw_resolve(name, type_)
			except TimeoutError:
				pass
		else:
			return []
	
	async def raw_resolve(self, name, type_):
		serial = randrange(2**16)
		while serial in self.waiting:
			serial = randrange(2**16)
		
		query = create_dns_query(name, type_, serial)
		self.waiting[serial] = self.loop.create_future()
		self.transport.sendto(query)
		
		try:
			result = await asyncio.wait_for(self.waiting[serial], timeout=self.timeout)
		finally:
			del self.waiting[serial]
		
		t = self.loop.time()
		addrs = []
		cnames = []
		for answer in result.answer:
			if answer.name == name and answer.x_type == 'CNAME':
				cnames.append(answer.rdata)
			if answer.name == name and answer.x_type == type_:
				addrs.append(answer.rdata)
			self.cache[answer.name, answer.x_type].add((answer.rdata, t + answer.ttl))
		
		for cname in cnames:
			for answer in result.answer:
				if answer.name == cname and answer.x_type == type_:
					addrs.append(answer.rdata)
					self.cache[cname, answer.x_type].add((answer.rdata, t + answer.ttl))
		return addrs
	
	async def __aenter__(self):
		loop = asyncio.get_running_loop()
		await self.open(loop)
		return self
	
	async def open(self, loop):
		self.loop = loop
		await self.loop.create_datagram_endpoint((lambda: self), remote_addr=self.server[0], flags=socket.AI_NUMERICHOST)
	
	async def __aexit__(self, *args):
		await self.close()
	
	async def close(self):
		self.transport.abort()
		del self.loop
		for future in self.waiting.values():
			future.set_exception(RuntimeError("Closing."))
		self.waiting.clear()


if __debug__ and __name__ == "__main__":
	with SyncResolver() as resolver:
		print(resolver.resolve('gist.githubusercontent.com', 'AAAA'))
		print(resolver.resolve('gist.githubusercontent.com', 'A'))
		print(resolver.resolve('www.google.pl', 'AAAA'))
		print(resolver.resolve('hotmail.com', 'MX'))
		print(resolver.resolve('interia.pl', 'MX'))
		print(resolver.resolve('wp.pl', 'MX'))
	
	async def main():
		async with AsyncResolver() as resolver:
			gh1 = resolver.resolve('gist.githubusercontent.com', 'AAAA')
			gh2 = resolver.resolve('gist.githubusercontent.com', 'A')
			google = resolver.resolve('www.google.pl', 'AAAA')
			hotmail = resolver.resolve('hotmail.com', 'MX')
			interia = resolver.resolve('interia.pl', 'MX')
			wp = resolver.resolve('wp.pl', 'MX')
			print(await asyncio.gather(gh1, gh2, google, hotmail, interia, wp)) # resolve in parallel
			
			gh1 = resolver.resolve('gist.githubusercontent.com', 'AAAA')
			gh2 = resolver.resolve('gist.githubusercontent.com', 'A')
			google = resolver.resolve('www.google.pl', 'AAAA')
			hotmail = resolver.resolve('hotmail.com', 'MX')
			interia = resolver.resolve('interia.pl', 'MX')
			wp = resolver.resolve('wp.pl', 'MX')
			print(await asyncio.gather(gh1, gh2, google, hotmail, interia, wp)) # resolve again to test caching
	
	asyncio.run(main())



