#!/usr/bin/python3

__author__ = 'https://github.com/haael'
__credits__ = 'https://github.com/vlasebian',
__license__ = '?'

if __name__ != '__main__':
	from .query import create_dns_query
	from .reply import parse_dns_reply, get_serial
	from .client import SyncResolver, AsyncResolver

