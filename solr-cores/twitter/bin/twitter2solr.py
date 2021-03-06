#!/usr/bin/env python

import sys
import pysolr
import json
import logging
import re

import httplib
import urlparse

def import_tweets(options):

    solr = pysolr.Solr(options.solr)

    if options.purge:
        logging.info("purging all existing tweets...")
        solr.delete(q='*:*')

    fh = open(options.tweets, 'r')

    data = json.load(fh)
    docs = []

    for doc in data['tweets']:

        doc['username'] = data['twitter_account']

        for key in ('created_at', 'added_at') :
            doc[ key ] = 'T'.join(doc[ key ].split(' ')) + 'Z'

        if options.extract and doc['link_count']:

            possible = re.findall(r'(https?://\S+)', doc['text'])
            links = []

            if len(possible):
                for p in possible:
                    url = unshorten_url(p, [])
      
                    if url:
                        links.append(url)

            if len(links):
                doc['links'] = links

        del(doc['source'])
        docs.append(doc)

        if len(docs) == 100:
            solr.add(docs)
            docs = []

    if len(docs):
        solr.add(docs)
    
    solr.optimize()

def unshorten_url(url, seen=[]):

    logging.debug("unshorten: %s (%s)" % (url, ";".join(seen)))

    to_check = (
        'bit.ly',
        'flic.kr',
        'ow.ly',
        # 'sta.mn',
        'shlong.us',
        't.co',
        )

    def _resolve(url):

        parts = urlparse.urlparse(url)

        try:
            conn = httplib.HTTPConnection(parts.hostname)
            conn.request("HEAD", parts.path)
            res = conn.getresponse()

            for k,v in res.getheaders():
                if k == 'location' or k == 'Location':
                    return v

        except Exception, e:
            logging.warning("failed to resolve '%s' : %s" % (url, e))
            return None

        return None

    parts = urlparse.urlparse(url)
    unshorten_me = False

    if parts.hostname in to_check:
        unshorten_me = True
    elif parts.hostname == 'www.flickr.com' and parts.path == '/short_urls.gne':
        unshorten_me = True
    elif parts.hostname == 'www.flickr.com' and parts.path == '/photo.gne':
        unshorten_me = True
    else:
        pass

    logging.debug("unshorten %s: %s" % (url, unshorten_me))

    if not unshorten_me:
        return url

    unshortened = _resolve(url)

    if not unshortened:
        return url

    if unshortened in seen:
        return url

    seen.append(url)

    return unshorten_url(unshortened, seen)

if __name__ == '__main__':

    import optparse

    parser = optparse.OptionParser()
    parser.add_option("-t", "--tweets", dest="tweets", action="store", help="your tweets (as a pinboard.in JSON export files)")
    parser.add_option("-s", "--solr", dest="solr", action="store", help="your solr endpoint; default is http://localhost:8983/solr/twitter", default="http://localhost:8983/solr/twitter")
    parser.add_option("-e", "--extract", dest="extract", action="store_true", help="extract links from tweets; default is false", default=False)
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="enable chatty logging; default is false", default=False)
    parser.add_option("--purge", dest="purge", action="store_true", help="purge all your existing bookmarks before starting the import; default is false", default=False)

    (opts, args) = parser.parse_args()

    if opts.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    import_tweets(opts)

    logging.info("all done!")
    sys.exit()
