#!/usr/bin/env python3
"""Bounded offline DATE-table inspection for known modern OpenTTD smoke fixtures.
Not an alternative save loader: the original engine remains the load authority.
"""
from pathlib import Path
import lzma, zlib, json, sys

class Reader:
    def __init__(self,data): self.data=data; self.pos=0
    def take(self,n):
        if n < 0 or self.pos+n>len(self.data): raise ValueError('Truncated save')
        result=self.data[self.pos:self.pos+n]; self.pos+=n; return result
    def gamma(self):
        first=self.take(1)[0]
        if first<128:return first
        if first<192: count,mask=1,0x3f
        elif first<224: count,mask=2,0x1f
        elif first<240: count,mask=3,0xf
        elif first<248: count,mask=4,0
        else:raise ValueError('Unsupported gamma')
        return ((first&mask)<<(8*count)) | int.from_bytes(self.take(count),'big')

def inspect(path):
    raw=Path(path).read_bytes()
    if len(raw)<8 or len(raw)>32*1024*1024:raise ValueError('Unsupported fixture size')
    if raw[:4]==b'OTTX':
        dec=lzma.LZMADecompressor();data=dec.decompress(raw[8:],max_length=32*1024*1024)
        if not dec.eof:raise ValueError('Incomplete or over-budget compressed fixture')
    elif raw[:4]==b'OTTN':data=raw[8:]
    elif raw[:4]==b'OTTZ':
        dec=zlib.decompressobj();data=dec.decompress(raw[8:],32*1024*1024)
        if not dec.eof:raise ValueError('Incomplete or over-budget compressed fixture')
    else:raise ValueError('Unsupported fixture compression')
    reader=Reader(data)
    while True:
        tag=reader.take(4)
        if tag==b'\0'*4:raise ValueError('No DATE chunk')
        mode=reader.take(1)[0];kind=mode&15
        if kind==0:
            reader.take(((mode>>4)<<24)|int.from_bytes(reader.take(3),'big'));continue
        if kind not in [1,2,3,4]:raise ValueError('Unsupported chunk kind')
        entries=[]
        while True:
            n=reader.gamma()
            if not n:break
            entries.append(reader.take(n-1))
        if tag!=b'DATE':continue
        if kind!=3 or len(entries)!=2:raise ValueError('Unexpected DATE table layout')
        header=Reader(entries[0]);fields=[]
        while True:
            typ=header.take(1)[0]
            if typ==0:break
            name=header.take(header.gamma()).decode('utf-8');fields.append((name,typ))
        if header.pos!=len(header.data):raise ValueError('Nested DATE schema unsupported')
        values={};record=Reader(entries[1]);widths={1:1,2:1,3:2,4:2,5:4,6:4,7:8,8:8,9:2}
        for name,typ in fields:
            base=typ&15
            if base==10:values[name]=record.take(record.gamma()).decode('utf-8');continue
            if base not in widths:raise ValueError('Unsupported DATE field')
            count=record.gamma() if typ&16 else 1
            if count>10000:raise ValueError('Over-budget DATE list')
            vals=[int.from_bytes(record.take(widths[base]),'big',signed=base in (1,3,5,7)) for _ in range(count)]
            values[name]=vals if typ&16 else vals[0]
        if record.pos!=len(record.data):raise ValueError('Unconsumed DATE bytes')
        return {'save_version':int.from_bytes(raw[4:6],'big'),'date_fields':values}

if __name__=='__main__':print(json.dumps(inspect(sys.argv[1]),indent=2))
