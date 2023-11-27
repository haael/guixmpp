#!/usr/bin/python3

from .query import create_dns_query
from .reply import parse_dns_reply, get_serial
from .client import SyncResolver, AsyncResolver

