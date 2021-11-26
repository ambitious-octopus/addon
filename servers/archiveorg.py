# -*- coding: utf-8 -*-
# --------------------------------------------------------
# Conector ArchiveOrg By Alfa development Group
# --------------------------------------------------------
from core import httptools
from core import scrapertools
from platformcode import config
from platformcode import logger


def test_video_exists(page_url):
    logger.debug("(page_url='%s')" % page_url)
    data = httptools.downloadpage(page_url)
    if data.code == 404:
        return False,  config.getLocalizedString(70449) % "ArchiveOrg"
    return True, ""


def get_videoUrl(page_url, premium=False, user="", password="", video_password=""):
    logger.debug("url=" + page_url)
    videoUrls = []
    data = httptools.downloadpage(page_url).data
    patron = '<meta property="og:video" content="([^"]+)">'
    matches = scrapertools.findMultipleMatches(data, patron)
    for url in matches:
        videoUrls.append({'type':'mp4', 'url':url})
    return videoUrls
