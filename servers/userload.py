# -*- coding: utf-8 -*-
from lib import aadecode
from lib import jsunpack
from core import support, httptools
from platformcode import logger, config


def test_video_exists(page_url):
    global data
    logger.debug('page url=', page_url)
    response = httptools.downloadpage(page_url)

    if response.code == 404 or 'We’re Sorry' in response.data:
        return False, config.getLocalizedString(70449) % 'Userload'
    else:
        data = response.data
    return True, ""


def get_videoUrl(page_url, premium=False, user="", password="", video_password=""):
    global data
    logger.debug("URL", page_url)
    videoUrls = []
    packed = support.match(data, patron=r"(eval\(function\(p,a,c,k,e,d\).*?)\s*<").match
    unpack = jsunpack.unpack(packed)
    for m in support.match(unpack, patron='var (\w+)="([^"]+)').matches:
        globals()[m[0]] = m[1]

    videojs = httptools.downloadpage('https://userload.co/api/assets/userload/js/videojs.js').data
    videojs_decoded = aadecode.decode(videojs)
    post = eval(support.match(videojs_decoded, patron="t.send\(([^\)]+)").match)
    logger.debug(post)
    url = support.match('https://userload.co/api/request/', post=post, patron=r'([^\s\r\n]+)').match
    if url:
        videoUrls.append({'type':url.split('.')[-1], 'url':url})

    return videoUrls