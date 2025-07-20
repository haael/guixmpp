#!/usr/bin/python3


__all__ = 'cached',


from inspect import isgeneratorfunction


def cached(old_method):
	if isgeneratorfunction(old_method):
		def new_method(self, *args, **kwargs):
			try:
				method_cache = self.method_cache
			except AttributeError:
				method_cache = self.method_cache = {}
			
			try:
				cache = method_cache[old_method.__name__]
			except KeyError:
				cache = method_cache[old_method.__name__] = {}
			
			try:
				series, error = cache[args, frozenset(kwargs.items())]
			except KeyError:
				try:
					series = []
					for value in old_method(self, *args, **kwargs):
						series.append(value)
						yield value
				except Exception as error:
					cache[args, frozenset(kwargs.items())] = (series, error)
					raise
				else:
					cache[args, frozenset(kwargs.items())] = (series, None)
			else:
				yield from series
				if error is not None:
					raise error
	else:
		def new_method(self, *args, **kwargs):
			try:
				method_cache = self.method_cache
			except AttributeError:
				method_cache = self.method_cache = {}
			
			try:
				cache = method_cache[old_method.__name__]
			except KeyError:
				cache = method_cache[old_method.__name__] = {}
			
			try:
				result, value = cache[args, frozenset(kwargs.items())]
			except KeyError:
				try:
					value = old_method(self, *args, **kwargs)
				except Exception as error:
					cache[args, frozenset(kwargs.items())] = (False, error)
					raise
				else:
					cache[args, frozenset(kwargs.items())] = (True, value)
					return value
			else:
				if result:
					return value
				else:
					raise value
	
	return new_method

