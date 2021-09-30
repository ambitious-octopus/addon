# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Canale per animealtadefinizione
# ----------------------------------------------------------

from platformcode import platformtools
from core import support
from platformcode import logger

host = support.config.get_channel_url()
headers = [['Referer', host]]

perpage_list = ['20','30','40','50','60','70','80','90','100']
perpage = perpage_list[support.config.get_setting('perpage' , 'animealtadefinizione')]
epPatron = r'<td>\s*(?P<title>[^<]+)[^>]+>[^>]+>\s*<a href="(?P<url>[^"]+)"'


@support.menu
def mainlist(item):
    anime=['/anime/',
           ('Tipo',['', 'menu', 'Anime']),
           ('Anno',['', 'menu', 'Anno']),
           ('Genere', ['', 'menu','Genere']),
           ('Ultimi Episodi',['', 'movies', 'last'])]
    return locals()


@support.scrape
def menu(item):
    action = 'movies'
    patronBlock= r'<a href="' + host + r'/category/' + item.args.lower() + r'/">' + item.args + r'</a>\s*<ul class="sub-menu">(?P<block>.*?)</ul>'
    patronMenu = r'<a href="(?P<url>[^"]+)">(?P<title>[^<]+)<'
    if 'genere' in item.args.lower():
        patronGenreMenu = patronMenu
    return locals()


def search(item, text):
    logger.debug(text)
    item.search = text
    try:
        return movies(item)
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def newest(category):
    logger.debug(category)
    item = support.Item()
    try:
        if category == "anime":
            item.url = host
            item.args = "last"
            return movies(item)
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        return []


@support.scrape
def movies(item):
    if '/movie/' in item.url:
        item.contentType = 'movie'
        action='findvideos'
    elif item.args == 'last':
        item.contentType = 'episode'
        action='findvideos'
    else:
        item.contentType = 'tvshow'
        action='episodes'
    if item.search:
        query = 's'
        searchtext = item.search
    else:
        query='category_name'
        searchtext = item.url.split('/')[-2]

    page = 1 if not item.page else item.page

    numerationEnabled = True
    post = 'action=itajax-sort&loop=main+loop&location=&thumbnail=1&rating=1sorter=recent&columns=4&numarticles={}&paginated={}&currentquery%5B{}%5D={}'.format(perpage, page, query, searchtext)
    res = support.match(host + '/wp-admin/admin-ajax.php', post=post, patron=r'"pages":(\d+)')
    data= res.data.replace('\\','')
    # item.total_pages = int(res.match)

    patron = r'<a href="(?P<url>[^"]+)"><img width="[^"]+" height="[^"]+" src="(?P<thumb>[^"]+)" class="[^"]+" alt="" title="(?P<title>[^"]+?)\s+(?P<type>Movie)?\s*(?P<lang>Sub Ita|Ita)?\s*[sS]treaming'
    typeContentDict = {'movie':['movie']}
    typeActionDict = {'findvideos':['movie']}

    def itemlistHook(itemlist):
        if item.search:
            itemlist = [ it for it in itemlist if ' Episodio ' not in it.title ]
        if len(itemlist) == int(perpage):
            support.nextPage(itemlist, item, 'movies', page=page + 1, total_pages=int(res.match))
        return itemlist
    return locals()


@support.scrape
def episodes(item):
    numerationEnabled = True
    pagination = True
    patron = epPatron
    return locals()


def findvideos(item):
    itemlist = []
    if item.contentType == 'movie':
        matches = support.match(item, patron=epPatron).matches
        for title, url in matches:
            get_video_list(item, url, title, itemlist)
    else:
        get_video_list(item, item.url, support.config.get_localized_string(30137), itemlist)
    return support.server(item, itemlist=itemlist)


def get_video_list(item, url, title, itemlist):
    if 'vvvvid' in url:
        itemlist.append(item.clone(title='VVVVID', url=url, server='vvvvid', action='play'))
    else:
        from requests import get
        if not url.startswith('http'): url = host + url

        url = support.match(get(url).url, string=True, patron=r'file=([^$]+)').match
        if 'http' not in url: url = 'http://' + url
        itemlist.append(item.clone(title=title, url=url, server='directo', action='play'))

    return itemlist