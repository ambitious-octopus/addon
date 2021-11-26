# -*- coding: utf-8 -*-
# --------------------------------------------------------
# Conector Samaup By Alfa development Group
# --------------------------------------------------------
from core import httptools
from core import scrapertools
from lib import jsunpack
from platformcode import config
from platformcode import logger


def test_video_exists(page_url):
    logger.debug("(page_url='%s')" % page_url)
    global data
    data = httptools.downloadpage(page_url).data
    if "Not Found" in data or "File was deleted" in data:
        return False,  config.getLocalizedString(70449) % "Samaup"
    return True, ""


def get_videoUrl(page_url, premium=False, user="", password="", video_password=""):
    logger.debug("url=" + page_url)
    videoUrls = []
    ext = 'mp4'

    packed = scrapertools.find_single_match(data, "text/javascript'>(eval.*?)\s*</script>")
    unpacked = jsunpack.unpack(packed)
    logger.error(unpacked)
    media_url = scrapertools.find_single_match(unpacked, 'file:"([^"]+)"')
    #media_url += "|Referer=%s" %page_url
    if "m3u8" in media_url:
        ext = "m3u8"
    videoUrls.append({'type':ext, 'url':media_url})

    return videoUrls
