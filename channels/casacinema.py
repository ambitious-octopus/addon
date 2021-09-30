# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Canale per 'casacinema'
# ------------------------------------------------------------


from core import support
from platformcode import logger

host = support.config.get_channel_url()
headers = [['Referer', host]]


@support.menu
def mainlist(item):
    film = ['/category/film',
        ('Generi', ['', 'genres', 'genres']),
        ('Sub-ITA', ['/category/sub-ita/', 'movies', 'sub'])
        ]

    tvshow = ['/category/serie-tv',
        ('Novità', ['/aggiornamenti-serie-tv', 'movies', '']),
        ]

    search = ''

    return locals()


@support.scrape
def genres(item):
    action = 'movies'
    blacklist = ['PRIME VISIONI', 'ULTIME SERIE TV', 'ULTIMI FILM']
    patronGenreMenu = r'<li><a href="(?P<url>[^"]+)">(?P<title>[^<>]+)</a></li>'
    patronBlock = r'<div class="container home-cats">(?P<block>.*?)<div class="clear">'
    return locals()


def select(item):
    item.data = support.match(item).data
    if 'continua con il video' in item.data.lower():
        logger.debug('select = ### è un film ###')
        item.contentType = 'movie'
        return findvideos(item)
    else:
        logger.debug('select = ### è una serie ###')
        item.contentType = 'tvshow'
        return episodes(item)


def search(item, text):
    logger.debug(text)
    text = text.replace(' ', '+')
    item.url = host + '/?s=' + text
    item.args = 'search'
    try:
        return movies(item)

    except:
        import sys
        for line in sys.exc_info():
            logger.error(line)
        return []


def newest(category):
    itemlist = []
    item = support.Item()
    item.args = 'newest'

    try:
        if category == 'tvshow':
            item.contentType = 'tvshow'
            item.url = host+'/aggiornamenti-serie-tv'

        else:
            item.contentType = 'movie'
            item.url = host+'/category/film'

        item.action = 'movies'
        itemlist = movies(item)

        if itemlist[-1].action == 'movies':
            itemlist.pop()

    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error(line)
        return []

    return itemlist


@support.scrape
def movies(item):
    # debug = True
    if item.contentType == 'movie':
        action = 'findvideos'
    elif item.contentType == 'tvshow':
        action = 'episodes'
        pagination = True
    else:
        action = 'select'

    if item.args == 'newest':
        patron = r'<li><a href="(?P<url>[^"]+)"[^=]+="(?P<thumb>[^"]+)"><div>\s*?<div[^>]+>(?P<title>[^\(\[<]+)(?:\[(?P<quality1>HD)\])?[ ]?(?:\(|\[)?(?P<lang>[sS]ub-[iI][tT][aA])?(?:\)|\])?[ ]?(?:\[(?P<quality>.+?)\])?[ ]?(?:\((?P<year>\d+)\))?<(?:[^>]+>.+?(?:title="Nuovi episodi">(?P<episode>\d+x\d+)[ ]?(?P<lang2>Sub-Ita)?|title="IMDb">(?P<rating>[^<]+)))?'
    else:
        # patron = r'<li><a href="(?P<url>[^"]+)"[^=]+="(?P<thumb>[^"]+)"><div>\s*?<div[^>]+>(?P<title>[^\(\[<]+)(?:\[(?P<quality1>HD)\])?\s?(?:[\(\[])?(?P<lang>[sS]ub-[iI][tT][aA])?(?:[\)\]])?\s?(?:\[(?P<quality>.+?)\])?\s?(?:\((?P<year>\d+)\))?<'
        patron = r'<li><a href="(?P<url>[^"]+)"[^=]+="(?P<thumb>[^"]+)"><div>\s*?<div[^>]+>(?P<title>[^\(\[<]+)(?P<title2>\([\D*]+\))?(?:\[(?P<quality1>HD)\])?\s?(?:[\(\[])?(?P<lang>[sS]ub-[iI][tT][aA])?(?:[\)\]])?\s?(?:\[(?P<quality>.+?)\])?\s?(?:\((?P<year>\d+)\))?(?:\(\D{2}\s\d{4}\))?<'

    patronNext = r'<a href="([^"]+)"\s*>Pagina'
    patronTotalPages = r'>(\d+)(?:[^>]+>){4}Pagina'

    def itemHook(item):
        if item.quality1:
            item.quality = item.quality1
            # item.title += support.typo(item.quality, '_ [] color kod')
        if item.lang2:
            item.contentLanguage = item.lang2
            # item.title += support.typo(item.lang2, '_ [] color kod')
        # if item.args == 'novita':
        #     item.title = item.title
        # if 'wp-content' in item.thumbnail and not item.infoLabels['year']:
        #     item.infoLabels['year'] = item.thumbnail.split('/')[5]
        return item
    return locals()


@support.scrape
def episodes(item):
    if item.data:
        data = item.data
    action = 'findvideos'
    item.contentType = 'tvshow'
    blacklist = ['']
    patron = r'(?P<episode>\d+(?:&#215;|×)?\d+\-\d+|\d+(?:&#215;|×)\d+)[;]?(?:(?P<title>[^<]+)<(?P<data>.*?)|(\2[ ])(?:<(\3.*?)))(?:<br />|</p>)'
    patronBlock = r'<strong>(?P<block>(?:.+?Stagione*.+?(?P<lang>[Ii][Tt][Aa]|[Ss][Uu][Bb][\-]?[iI][tT][aA]))?(?:.+?|</strong>)(/?:</span>)?</p>.*?</p>)'
    return locals()


def findvideos(item):
    if item.contentType != 'movie':
        links = support.match(item.data, patron=r'href="([^"]+)"').matches
    else:
        matchData = item.data if item.data else item
        links = support.match(matchData, patron=r'(?:SRC|href)="([^"]+)"', patronBlock=r'<div class="col-md-10">(.+?)<div class="ads">').matches
    data = ''
    from lib.unshortenit import unshorten_only
    for link in links:
        logger.debug('URL=',link)
        url, c = unshorten_only(link.replace('#', 'speedvideo.net'))
        data += url + '\n'
    return support.server(item, data)
