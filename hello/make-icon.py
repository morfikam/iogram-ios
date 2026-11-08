# Значок 120×120: зелёный квадрат, без лишних библиотек
import struct
import sys
import zlib

SIZE = 120
PIXEL = bytes((38, 140, 77))


def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))


raw = (b'\0' + PIXEL * SIZE) * SIZE
png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(raw))
       + chunk(b'IEND', b''))

with open(sys.argv[1], 'wb') as out:
    out.write(png)
