'''An object relational mapper library for Redis remote data structures.'''
VERSION = (0, 6, 1)
 
def get_version():
    return '.'.join(map(str,VERSION))
 
__version__ = get_version()
__license__ = "BSD"
__author__ = "Luca Sbardella"
__contact__ = "luca.sbardella@gmail.com"
__homepage__ = "https://github.com/lsbardel/python-stdnet"
CLASSIFIERS = [
               'Development Status :: 4 - Beta',
               'Environment :: Plugins',
               'Environment :: Web Environment',
               'Intended Audience :: Developers',
               'License :: OSI Approved :: BSD License',
               'Operating System :: OS Independent',
               'Programming Language :: Python',
               'Programming Language :: Python :: 2.6',
               'Programming Language :: Python :: 2.7',
               'Programming Language :: Python :: 3.1',
               'Programming Language :: Python :: 3.2',
               'Topic :: Utilities',
               'Topic :: Database'
               ]


sphinxtogithub = False

from .exceptions import *
from .backends import *
