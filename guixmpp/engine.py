#!/usr/bin/python3


from pythonmonkey import globalThis, eval as eval_javascript
from os import fdopen, close, set_blocking
from sys import stdin, argv
from pickle import loads, dumps
#from asyncio import run
from asyncio.exceptions import IncompleteReadError
from seccomp import *


end_of_transmission = bytes([0x04])
file_separator = bytes([0x1c])
group_separator = bytes([0x1d])
record_separator = bytes([0x1e])
unit_separator = bytes([0x1f])


class ReadUntil:
	def __init__(self, reader):
		self.reader = reader
		self.chunks = b""
	
	def readuntil(self, char):
		while char not in self.chunks:
			chunk = self.reader.read(1)
			if not chunk:
				break
			self.chunks += chunk
		
		if char not in self.chunks:
			if self.chunks:
				raise IncompleteReadError
			else:
				return
		
		n = self.chunks.index(char)
		result = self.chunks[:n + 1]
		self.chunks = self.chunks[n + 1:]
		return result
	
	def close(self):
		self.reader.close()


class Proxy:
	def __init__(self, name):
		self.__dict__['_Proxy__name'] = name
	
	def __getattr__(self, attr):
		write_pipe.write('get'.encode('utf-8'))
		write_pipe.write(record_separator)
		write_pipe.write((self.__name + '.' + attr).encode('utf-8'))
		write_pipe.write(group_separator)
		write_pipe.flush()
		data = read_pipe.readuntil(group_separator)[:-1]
		assert data
		return loads(data)
	
	def __setattr__(self, attr, value):
		write_pipe.write('set'.encode('utf-8'))
		write_pipe.write(record_separator)
		write_pipe.write((self.__name + '.' + attr).encode('utf-8'))
		write_pipe.write(record_separator)
		write_pipe.write(dumps(value))
		write_pipe.write(group_separator)
		write_pipe.flush()


def main(stdin):
	globalThis['window'] = Proxy('window')
	
	while True:
		try:
			data = stdin.readuntil(file_separator)
		except IncompleteReadError:
			break
		else:
			if data is None:
				break
			data = data[:-1]
			if (not data) or (len(data) == 1 and data[0] == end_of_transmission) or (group_separator not in data):
				break
		
		mime_type, script = data.split(group_separator)
		mime_type = mime_type.decode('utf-8')
		script = script.decode('utf-8')
		
		#print("received script:", mime_type, len(script))
		if mime_type == 'application/javascript':
			eval_javascript(script + "\n\n")
		else:
			print("Unsupported script type:", mime_type)


if __debug__ and __name__ == '__main__':
	... # TODO: tests


if __name__ == '__main__':
	try:
		r_fd = int(argv[1])
		w_fd = int(argv[2])
	
	except (IndexError, ValueError):
		print("Script engine with browser document model.")
		print("usage:", argv[0], "<read pipe fd> <write pipe fd>")
	
	else:
		set_blocking(r_fd, True)
		set_blocking(w_fd, True)
		
		read_pipe = ReadUntil(fdopen(r_fd, 'rb', buffering=0))
		write_pipe = fdopen(w_fd, 'wb', buffering=0)
		
		'''
		write_pipe.write(b"slave\n")
		write_pipe.flush()
		
		master = read_pipe.readuntil(b"\n")
		assert master == b"master\n"
		print("ok")
		'''
		
		# Only allow the following syscalls.
		filter_ = SyscallFilter(KILL) # TODO: Report violations back instead of killing the process.
		filter_.add_rule(ALLOW, 'mmap') # FIXME: disallow mmapping files except non-shared memory
		filter_.add_rule(ALLOW, 'munmap')
		filter_.add_rule(ALLOW, 'select')
		filter_.add_rule(ALLOW, 'read')
		filter_.add_rule(ALLOW, 'write')
		filter_.add_rule(ALLOW, 'close')
		filter_.add_rule(ALLOW, 'futex')
		filter_.add_rule(ALLOW, 'getrusage')
		filter_.add_rule(ALLOW, 'mprotect')
		filter_.add_rule(ALLOW, 'rt_sigaction')
		filter_.add_rule(ALLOW, 'rt_sigreturn')
		filter_.add_rule(ALLOW, 'clock_gettime')
		filter_.add_rule(ALLOW, 'madvise')
		filter_.add_rule(ALLOW, 'prctl') # FIXME
		filter_.add_rule(ALLOW, 'exit')
		filter_.add_rule(ALLOW, 'exit_group')
		filter_.load()
		
		main(ReadUntil(stdin.buffer))
		
		read_pipe.close()
		write_pipe.close()


