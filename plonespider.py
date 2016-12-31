import os.path
import posixpath
import re
import spider
import urlparse

amp_pattern = re.compile(r'(?:amp\;)+')
base_href_pattern = re.compile(r"""\<base.*?href=["'](.+?)['"] */?\>""", re.IGNORECASE)
css_link_pattern = re.compile(r"""url\((.+?)\)""", re.IGNORECASE)
link_pattern = re.compile(r"""(href|src|link)=(["'])(.+?)(["'])""", re.IGNORECASE)
link_pattern_nocap = re.compile(r"""(?:href|src|link)=["'](.+?)["']""", re.IGNORECASE)
is_css_or_js_pattern = re.compile(r"""\.(?:css|js)$""")


def getBaseHref(content, base):
    """ get base href from content; return base if none """

    mo = base_href_pattern.search(content)
    if mo:
        return mo.group(1)
    return base

def is_css_or_js(s):
    return is_css_or_js_pattern.search(s) is not None


class PloneSpider(spider.Spider):
    """ Overrides the Spider methods that need to be sensitive to Plone's
        Peculiarities.
    """

    def __init__(self, base=None, width=None, depth=None):
        super(PloneSpider, self).__init__(base=base, width=width, depth=depth)
        self._mimetypes = {}
        self._mime_extensions = {}
        white_split_pattern = re.compile(r'\s+')
        with open(os.path.join(os.path.dirname(__file__), 'mime.types')) as mt:
            for mlist in [white_split_pattern.split(l.strip()) for l in mt if not l.startswith('#')]:
                if len(mlist) > 1:
                    self._mime_extensions[mlist[0]] = mlist[1]

    def normalizeURL(self, url, base):
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
        # remove trailing / and return
        return rez.rstrip('/')

    def _webopen(self, base):
        '''Verifies URL and returns actual URL and extracted child URLs

        Arguments:
        base -- tuple containing a URL and its referring URL

        Modified to save MIME extension in self._mimetypes
        '''
        # Assignments
        cbase, referer = base
        try:
            # If webspiders can access URL, open it
            if (referer == '') or self._robot.can_fetch('*', cbase):
                url = self._ulib.urlopen(cbase)
            # Otherwise, mark as visited and abort
            else:
                self._visited[cbase] = 1
                return False
        # If HTTP error, log bad URL and abort
        except IOError:
            self._visited[cbase] = 1
            self.badurls.append((base[1], cbase))
            return False
        # Get real URL
        newbase = url.geturl()
        # Change URL if different from old URL
        if newbase != cbase:
            cbase, base = newbase, (newbase, base[1])
        self._mimetypes[cbase] = self._mime_extensions.get(url.headers.type, 'bin')
        # URLs with mimetype 'text/html" scanned for URLs
        if url.headers.type == 'text/html':
            # Feed parser
            contents = url.read()
            try:
                badurl, urls = self._webparser(contents, cbase)
            # Log URL if SGML parser can't parse it
            except self._sperror:
                self._visited[cbase], self.badhtm[cbase] = 1, 1
                return False
            url.close()
            # Return URL and extracted urls if it's good
            if not badurl:
                return cbase, urls
            # If the URL is bad (after BadUrl), stop processing and log URL
            else:
                self._visited[cbase] = 1
                self.badurls.append((base[1], cbase))
                return False
        # Return URL of non-HTML resources and empty list
        else:
            url.close()
            return cbase, []

    def _webparser(self, content, base):
        ''' Parses content and extracted URLs

            Modified to use re searches and consider base href
        '''
        # gather urls

        base = getBaseHref(content, base)
        links = []
        rez = link_pattern_nocap.findall(content)
        rez += css_link_pattern.findall(content)
        for url in rez:
            normurl = self.normalizeURL(url, base)
            if normurl.startswith(self.base) or is_css_or_js(normurl):
                links.append(normurl)
        return False, links

    def webpaths(self, b=None, w=200, d=5, t=None):
        '''Returns a list of web paths.

        Arguments:
        b -- base web URL (default: None)
        w -- amount of resources to crawl (default: 200)
        d -- depth in hierarchy to crawl (default: 5)
        t -- number of threads (default: None)

        Modified to consider mime types.
        '''

        def pathize():
            '''Strips base URL from full URLs to produce paths'''
            rbase = self.base.rstrip('/')
            for url in urls:
                extension = self._mimetypes.get(url.rstrip('/'), 'notfound')
                # Remove base URL from path list
                url = url.replace(rbase, '')
                url = url.strip('/')
                # remove 'view'
                if url.endswith('/view'):
                    url = url[:-5]
                if not is_css_or_js(url):
                    index_item = 'index.%s' % extension
                    if not url.endswith(index_item):
                        url = '/'.join([url, index_item]).lstrip('/')
                # Verify removal of base URL and remove it if found
                if url.find(':') != -1:
                    url = urlsplit(url)[2:][0]
                if url.startswith('//'):
                    url = url[1:]
                yield url.rstrip('/')

        # Assignments
        urlsplit = self._uparse.urlsplit
        # Run weburls if base passed as an argument
        if b:
            self.weburls(b, w, d, t)
        # Strip off trailing resource or query from base URL
        if self.base[-1] != '/':
            self.base = '/'.join(self._sb[:-1])
        urls = self.urls
        # Return path list after stripping base URL
        self.paths = list(pathize())
        return self.paths

    def _urlverify(self, url, base, newbase):
        '''Returns a full URL relative to a base URL

        Arguments:
        urls -- list of raw URLs
        base -- referring URL
        newbase -- temporary version of referring URL for joining

        Modified to only accept URLS at or under base.
        '''
        # Assignments
        visited, webopen = self._visited, self._webopen
        sb, depth, urljoin = self._sb[2], self.depth, self._uparse.urljoin
        urlsplit, urldefrag = self._uparse.urlsplit, self._uparse.urldefrag
        outside, redirs = self.outside, self.redirs
        rbase = self.base.rstrip('/')
        if url not in visited:
            # Remove whitespace from URL
            if url.find(' ') != -1:
                visited[url], url = 1, url.replace(' ', '')
                if url in visited:
                    return 0, 0
            # Remove fragments i.e. 'http:foo/bar#frag'
            if url.find('#') != -1:
                visited[url], url = 1, urldefrag(url)[0]
                if url in visited:
                    return 0, 0
            # Process full URLs i.e. 'http://foo/bar
            if url.find(':') != -1:
                if not (url.startswith(rbase) or is_css_or_js(url)):
                    # print self.base, url, url.startswith(self.base)
                    visited[url], outside[url] = 1, 1
                    return 0, 0
                # urlseg = urlsplit(url)
                # # Block non-FTP, HTTP URLs
                # if urlseg[0] not in supported:
                #     # Log as non-FTP/HTTP URL
                #     other[url], visited[url] = 1, 1
                #     return 0, 0
                # # If URL is not in root domain, block it
                # if urlseg[1] not in sb:
                #     visited[url], outside[url] = 1, 1
                #     return 0, 0
                # # Block duplicate root URLs
                # elif not urlseg[2] and urlseg[1] == sb:
                #     visited[url] = 1
                #     return 0, 0
            # Handle relative URLs i.e. ../foo/bar
            elif url.find(':') == -1:
                # Join root domain and relative URL
                visited[url], url = 1, urljoin(newbase, url)
                if url in visited:
                    return 0, 0
            # Test URL by attempting to open it
            rurl = webopen((url, base))
            if rurl and rurl[0] not in visited:
                # Get URL
                turl, rawurls = rurl
                visited[url], visited[turl] = 1, 1
                # If URL resolved to a different URL, process it
                if turl != url:
                    urlseg = urlsplit(turl)
                    # If URL is not in root domain, block it
                    if urlseg[1] not in sb:
                        # Log as a redirected internal URL
                        redirs[(url, turl)] = 1
                        return 0, 0
                    # Block duplicate root URLs
                    elif not urlseg[2] and urlseg[1] == sb:
                        return 0, 0
                # If URL exceeds depth, don't process
                if len(turl.split('/')) >= depth:
                    return 0, 0
                # Otherwise return URL
                else:
                    if rawurls:
                        return turl, rawurls
                    else:
                        return turl, []
            else:
                return 0, 0
        else:
            return 0, 0

    def _mirror(self, lists, root=None, threads=None):

        def relurl(otarget, obase):
            base = urlparse.urlparse(obase)
            target = urlparse.urlparse(otarget)
            if base.netloc != target.netloc:
                # raise ValueError('target and base netlocs do not match')
                return otarget
            base_dir = '.' + posixpath.dirname(base.path)
            target = '.' + target.path
            return posixpath.relpath(target, start=base_dir)

        def pathFix(url):
            furl = self.normalizeURL(url, base)
            nurl = mypaths.get(furl)
            if nurl is None:
                nurl = furl
            else:
                if not nurl.startswith('/'):
                    nurl = '/%s' % nurl
                nurl = relurl('%s' % nurl, '/%s' % path)
                # print path, furl, nurl
            return nurl

        def fixLink(mo):
            groups = mo.groups()
            nurl = pathFix(groups[2])
            return "%s=%s%s%s" % (
                groups[0],
                groups[1],
                nurl,
                groups[3],
            )

        def fixCSSLink(mo):
            nurl = pathFix(mo.groups()[0])
            return "url(%s)" % nurl

        super(PloneSpider, self)._mirror(lists, root, threads)
        # fix URLs in downloaded html
        # First, normalize saved URLs to have no trailing /
        mypaths = dict(
            zip(
                self.urls,
                self.paths
            )
        )
        for url in self.urls:
            path = mypaths[url]
            if path.endswith('.html'):
                fn = os.path.join(root, path)
                with open(fn, 'r') as f:
                    content = f.read()
                base = getBaseHref(content, self.base)
                content = base_href_pattern.sub('', content)
                content = link_pattern.sub(fixLink, content)
                content = css_link_pattern.sub(fixCSSLink, content)
                with open(fn, 'w') as f:
                    f.write(content)
