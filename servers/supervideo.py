# -*- coding: utf-8 -*-

import ast

from core import httptools
from core import scrapertools
from lib import jsunpack
from platformcode import config, logger


def test_video_exists(page_url):
    logger.debug("(page_url='%s')" % page_url)
    global data
    data = httptools.downloadpage(page_url, cookies=False).data
    if 'Video embed restricted for this domain' in data:
        headers = {'Referer': ''}
        data = httptools.downloadpage(page_url, headers=headers, cookies=False).data
    if 'File is no longer available as it expired or has been deleted' in data or 'fake-' in data:
        return False, config.getLocalizedString(70449) % "SuperVideo"

    return True, ""


def get_videoUrl(page_url, premium=False, user="", password="", video_password=""):
    logger.debug("url=" + page_url)
    videoUrls = []
    # data = httptools.downloadpage(page_url).data
    global data

    code_data = scrapertools.find_single_match(data, "<script type='text/javascript'>(eval.*)")
    if code_data:
        code = jsunpack.unpack(code_data)

        # corrections
        if 'file' in code and not '"file"'in code: code = code.replace('file','"file"')
        if 'label' in code and not '"label"'in code: code = code.replace('label','"label"')

        match = scrapertools.find_single_match(code, r'sources:(\[[^]]+\])')
        lSrc = ast.literal_eval(match)

        # lQuality = ['360p', '720p', '1080p', '4k'][:len(lSrc)-1]
        # lQuality.reverse()

        for source in lSrc:
            quality = source['label'] if 'label' in source else 'auto'
            videoUrls.append({'type':source['file'].split('.')[-1], 'res':quality, 'url':source['file']})

    else:
        matches = scrapertools.findMultipleMatches(data, r'src:\s*"([^"]+)",\s*type:\s*"[^"]+"(?:\s*, res:\s(\d+))?')
        for url, quality in matches:
            if url.split('.')[-1] != 'm3u8':
                videoUrls.append({'type':url.split('.')[-1], 'res':quality, 'url':url})
            else:
                videoUrls.append({'type':url.split('.')[-1], 'url':url})

    # videoUrls.sort(key=lambda x: x[0].split()[-2])
    return videoUrls
