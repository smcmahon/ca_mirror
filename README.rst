A script that mirrors a site with sensitivity to the oddness of Plone sites, such as:

 * Lack of filename extensions;
 * The fact that an index object is not necessarily HTML.

Based on spider.py, included here with some fixes.
spider.py is BSD licensed: https://pypi.python.org/pypi/spider.py


spider._webopen
'''Verifies URL and returns actual URL and extracted child URLs

        Arguments:
        base -- tuple containing a URL and its referring URL'''

spider._webparser(self, html):
    '''Parses HTML and returns bad URL indicator and extracted URLs

    Arguments:
    html -- HTML data'''

spider.webpaths(self, b=None, w=200, d=5, t=None):
    '''Returns a list of web paths.

    Arguments:
    b -- base web URL (default: None)
    w -- amount of resources to crawl (default: 200)
    d -- depth in hierarchy to crawl (default: 5)
    t -- number of threads (default: None)'''
NOTE: self.paths contains paths
if b is None, runs weburls

spider.weburls(self, base=None, width=200, depth=5, thread=None):
    '''Returns a list of web paths.

    Arguments:
    base -- base web URL (default: None)
    width -- amount of resources to crawl (default: 200)
    depth -- depth in hierarchy to crawl (default: 5)
    thread -- number of threads to run (default: None)'''
NOTE: self.urls contains URLs