# -*- coding: utf-8 -*-
from core import httptools
from core import scrapertools
from platformcode import config
from platformcode import logger


def test_video_exists(page_url):
    logger.debug("(page_url='%s')" % page_url)
    data = httptools.downloadpage(page_url).data
    if "no longer exists" in data or "to copyright issues" in data:
        return False, "[Downace] El video ha sido borrado"
    if "please+try+again+later." in data:
        return False, "[Downace] Error de downace, no se puede generar el enlace al video"
    if "File has been removed due to inactivity" in data:
        return False,  config.getLocalizedString(70449) % "Downace"
    return True, ""


def get_videoUrl(page_url, user="", password="", video_password=""):
    logger.debug("(page_url='%s')" % page_url)
    data = httptools.downloadpage(page_url).data
    videoUrls = []
    videourl = scrapertools.find_single_match(data, 'controls preload.*?src="([^"]+)')
    videoUrls.append({'type':'mp4', 'url':videourl})

    return videoUrls
