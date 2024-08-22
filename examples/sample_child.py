#!/usr/bin/python3


import sys
from pathlib import Path
from time import time

l = Path('sample_child.log')
lf = l.open('w')


for l in sys.stdin:
	t = time()
	print(t, repr(l))
	print(t, repr(l), file=lf)


lf.close()




