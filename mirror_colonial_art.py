from spider import Spider

import os
import os.path
import re
import sys
import urlparse

# special_ext_pattern = re.compile(r"\.(?:gif|png|jpg|pdf|mp3)+(?:\-\d+)?$", re.I)

base_href_pattern = re.compile(r"""\<base.*?href=["'](.+?)['"]""", re.IGNORECASE)
amp_pattern = re.compile(r'(?:amp\;)+')
link_pattern = re.compile(r"""(href|src|link)=(["'])(.+?)(["'])""", re.IGNORECASE)
css_link_pattern = re.compile(r"""url\((.+?)\)""", re.IGNORECASE)
link_pattern_nocap = re.compile(r"""(?:href|src|link)=["'](.+?)["']""", re.IGNORECASE)
image_view_pattern = re.compile(r'/image_[^/]+$')
white_split_pattern = re.compile(r'\s+')


def getBaseHref(content, base):
    """ get base href from content; return base if none """

    mo = base_href_pattern.search(content)
    if mo:
        return mo.group(1)
    return base


class PloneSpider(Spider):

    def __init__(self, base=None, root=None, width=None, depth=None, aliases=[]):
        super(PloneSpider, self).__init__(base=base, width=width, depth=depth)
        if root is not None:
            self.root = root
        else:
            self.root = None
        self.aliases = aliases
        self.filepaths = {}
        self.html_files = []

    def normalizeURL(self, url, base):
        # print url, base
        for alias in self.aliases:
            url = url.replace(alias, self.base)
        newurl = urlparse.urljoin(base, url)
        split = urlparse.urlsplit(newurl)
        path = split.path
        while path.startswith('/..'):
            path = path[3:]
        query = amp_pattern.sub('amp;', split.query)
        rez = urlparse.urlunsplit((
            split.scheme,
            split.netloc,
            path,
            query,
            ''
        ))
        # remove trailing /s
        if rez.endswith('/'):
            rez = rez[:-1]
        return rez

    def _fixlinks(self, content, base):
        ''' fixes links in contents; filepaths must be loaded.
        '''

        def fixLink(mo):
            groups = mo.groups()
            url = self.normalizeURL(groups[2], base)
            if url in self.filepaths:
                url = "/%s" % self.filepath(url, url, 'text/html')
            rez = "%s=%s%s%s" % (
                groups[0],
                groups[1],
                url,
                groups[3],
            )
            return rez

        base = getBaseHref(content, base)
        # gather and fix urls
        return link_pattern.sub(fixLink, content)

    def _fixCSSlinks(self, content, base):
        ''' fixes links in contents; filepaths must be loaded.
        '''

        def fixLink(mo):
            groups = mo.groups()
            url = self.normalizeURL(groups[0].replace("'", "").replace('"', ''), base)
            if url in self.filepaths:
                url = "/%s" % self.filepath(url, url, 'text/html')
            rez = "url(%s)" % url
            return rez

        base = getBaseHref(content, base)
        # gather and fix urls
        return css_link_pattern.sub(fixLink, content)

    def _webparser(self, content, base):
        ''' Parses content and extracted URLs
        '''
        # gather urls

        base = getBaseHref(content, base)
        links = []
        rez = link_pattern_nocap.findall(content)
        rez += css_link_pattern.findall(content)
        for url in rez:
            normurl = self.normalizeURL(url, base)
            if normurl.startswith(self.base):
                links.append(normurl)
        return links

    def filepath(self, url, old_url, mimetype):
        # decode url, normalize url and query
        rurl = self.filepaths.get(old_url)
        if rurl is not None:
            return rurl
        o = urlparse.urlparse(url)
        path, ext = os.path.splitext(o.path)
        if not ext:
            ext = ".%s" % mime_extensions.get(mimetype, 'html')
        rurl = "%s://%s%s" % (o.scheme, o.netloc, path)
        if o.query:
            rurl += '/%s' % o.query
        if mimetype == 'text/html':
            if ext in ('.css', '.js', '.kss'):
                rurl += ext
            else:
                rurl = os.path.join(rurl, 'index.html')
        elif mimetype.startswith('image/'):
            # scaling needs special handling
            if image_view_pattern.search(path):
                rurl += ext
            else:
                rurl = os.path.join('%s%s' % (rurl, ext), "view%s" % ext)
        else:
            if path.endswith('view') or path.endswith('download'):
                rurl += ext
            else:
                rurl = os.path.join('%s%s' % (rurl, ext), "view%s" % ext)
        rurl = rurl.replace('%', '_').replace('&amp;', '_').replace('&', '_').replace('=', '_').replace('+', '_')
        rurl = rurl.replace(self.base, '')
        if rurl.startswith('/'):
            rurl = rurl[1:]
        self.filepaths[old_url] = rurl
        self.filepaths[url] = rurl
        return rurl

    def _webopen(self, base):
        '''Verifies URL and returns actual URL and extracted child URLs

        Arguments:
        base -- tuple containing a URL and its referring URL'''
        # Assignments
        good, cbase = self._good, base[0]
        # Get real URL
        url = self._ulib.urlopen(cbase)
        newbase = url.geturl()
        if '@@search' in newbase:
            return False
        if '/recent' in newbase:
            return False
        mimetype = url.headers.type
        filepath = os.path.join(self.root, self.filepath(newbase, cbase, mimetype))
        # print cbase, mimetype, filepath
        # print newbase
        # Change URL if different from old URL
        if newbase != cbase:
            cbase, base = newbase, (newbase, base[1])
        contents = url.read()
        url.close()
        # URLs with mimetype 'text/html" scanned for URLs
        if mimetype in ('text/html', 'text/css'):
            # Feed parser
            urls = self._webparser(contents, cbase)
            # add to list of html files that will need rewriting.
            self.html_files.append((filepath, cbase,))
        else:
            # Return URL of non-HTML resources and empty list
            urls = []
        # print urls
        dirname = os.path.split(filepath)[0]
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filepath, 'wb') as f:
            f.write(contents)
        return cbase, urls

spider = PloneSpider(
    base="http://localhost:8080/colonialart",
    root="/home/steve/cart_mirror",
    width=5,
    )

mime_extensions = {}
with open(os.path.join(os.path.dirname(__file__), 'mime.types')) as mt:
    for mlist in [white_split_pattern.split(l.strip()) for l in mt if not l.startswith('#')]:
        if len(mlist) > 1:
            mime_extensions[mlist[0]] = mlist[1]
# print mime_extensions

print "mirroring, pass one"
spider.weburls(spider.base, width=5000000, depth=5000)
# spider.weburls(spider.base, width=5, depth=2)
print "%s items copied" % len(spider.filepaths)

print "mirroring, pass two: normalize urls"
for fn, cbase in spider.html_files:
    # print fn
    with open(fn, 'rb') as f:
        content = f.read()
    newcontent = spider._fixlinks(content, cbase)
    # affix a mirror stylesheet import to the end of head
    newcontent = newcontent.replace(
        "</head>",
        """<style media="screen" type="text/css">@import url(/mirror.css);</style></head>"""
        )
    newcontent = spider._fixCSSlinks(newcontent, cbase)
    with open(fn, 'wb') as f:
        f.write(newcontent)
print "%s HTML files rewritten" % len(spider.html_files)

