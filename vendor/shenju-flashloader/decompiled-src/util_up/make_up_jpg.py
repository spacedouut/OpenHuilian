# Source Generated with Decompyle++
# File: make_up_jpg.pyc (Python 3.10)

__author__ = 'yangyang'
import io
from PIL import Image

def read_word(file):
    ''' Read a 16 bit word from file '''
    out = ord(file.read(1)) << 8
    out |= ord(file.read(1))
    return out


def read_byte(file):
    ''' Read a byte from file '''
    out = ord(file.read(1))
    return out


def read_dht(file):
