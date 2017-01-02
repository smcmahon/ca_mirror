#!/usr/bin/env python

import argparse
from plonespider import PloneSpider

parser = argparse.ArgumentParser()
parser.add_argument("url", help="Site to mirror")
parser.add_argument("path", help="Destination path")
parser.add_argument("-d", '--depth', type=int, default=100, help="Maximum depth to mirror")
parser.add_argument("-w", '--width', type=int, default=20000, help="Maximum items to mirror")
args = parser.parse_args()

my_spider = PloneSpider(
    base=args.url,
    depth=args.depth,
    width=args.width,
)

my_spider.webmirror(
    root=args.path,
    base=args.url,
    depth=args.depth,
    width=args.width,
)
