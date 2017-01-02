from plonespider import PloneSpider

my_spider = PloneSpider(
    base="http://groups.dcn.org/ondh",
    depth=1000,
    width=20000,
)

# import pdb; pdb.set_trace()
# urls = my_spider.weburls()

# import pdb; pdb.set_trace()
# paths = my_spider.webpaths()

# import pdb; pdb.set_trace()
# pass

my_spider.webmirror(
    root="/home/steve/nobackup/lofland/ondh",
    base="http://groups.dcn.org/ondh",
    depth=1000,
    width=20000,
)
