# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------
# autorenumber - Rinumera Automaticamente gli Episodi
# --------------------------------------------------------------------------------


import xbmc, xbmcgui, re, base64, sys
from core import jsontools, tmdb, filetools
from core.item import Item
from core.support import typo, Item
from platformcode import config, platformtools, logger
PY3 = True if sys.version_info[0] >= 3 else False
if PY3:
    from concurrent import futures
else:
    from concurrent_py2 import futures

# Json Var
RENUMBER = 'TVSHOW_AUTORENUMBER'
ID = 'id'
SEASONSDICT = 'seasons'
SEASON = 'season'
EPISODE = 'episode'
EPISODES = 'episodes'
SPECIALEPISODES = 'specials'
MANUALMODE = 'manual'
GROUP = 'info'

# helper Functions
def check(item, itemlist=None):
    if itemlist and itemlist[0].contentSeason:
        return True
    logger.debug()
    dict_series = load(item)
    title = item.fulltitle.rstrip()
    if title in dict_series: title = dict_series[title]
    return True if ID in title and EPISODE in title else False

def filename(item):
    logger.debug()
    name_file = item.channel + "_data.json"
    path = filetools.join(config.getDataPath(), "settings_channels")
    fname = filetools.join(path, name_file)
    return fname


def load(item):
    logger.debug()
    try: json = jsontools.load(open(filename(item), "r").read())[RENUMBER]
    except: json = {}
    return json


def write(item, json):
    logger.debug()
    js = jsontools.load(open(filename(item), "r").read())
    js[RENUMBER] = json
    with open(filename(item), "w") as file:
        file.write(jsontools.dump(js))
        file.close()

def b64(json, mode = 'encode'):
    if PY3: json = bytes(json, 'ascii')
    if mode == 'encode':
        ret = base64.b64encode(json)
        if PY3: ret = ret.decode()
    else:
        ret = jsontools.load(base64.b64decode(json))
    return ret

def find_episodes(item):
    logger.debug()
    ch = platformtools.channelImport(item.channel)
    itemlist = getattr(ch, item.action)(item)
    return itemlist

def busy(state):
    if state: xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    else: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def RepresentsInt(s):
    # Controllo Numro Stagione
    logger.debug()
    try:
        int(s)
        return True
    except ValueError:
        return False

# Main
def start(itemlist, item=None):
    if not itemlist: return
    if type(itemlist) == Item:
        item = itemlist
        if item.channel in ['autorenumber']:
            item.channel = item.from_channel
            item.action = item.from_action
            item.setrenumber = True
        busy(True)
        itemlist = find_episodes(item)
        busy(False)
    return autorenumber(itemlist, item)

class autorenumber():
    def __init__(self, itemlist, item=None):
        self.item = item
        self.itemlist = itemlist
        self.selectspecials = False
        self.manual = False
        self.auto = False

        if self.item:
            from core.videolibrarytools import check_renumber_options
            check_renumber_options(self.item)
            self.renumberdict = load(item)
            self.auto = config.getSetting('autorenumber', item.channel)
            self.title = self.item.fulltitle.strip()
            if item.contentSeason:
                item.exit = True
                return 

            self.series = self.renumberdict.get(self.title,{})
            self.id = self.series.get(ID, 0)
            self.episodes = self.series.get(EPISODES,{})
            self.seasonsdict = self.series.get(SEASONSDICT,{})
            self.season = self.series.get(SEASON, -1)
            self.episode = self.series.get(EPISODE, -1)
            self.manual = self.series.get(MANUALMODE, False)
            self.specials = self.series.get(SPECIALEPISODES, {})
            if self.id and self.episodes and self.season >= 0 and self.episode >= 0: 
                if self.item.setrenumber: self.config()
                else:self.renumber()
            elif self.auto or self.item.setrenumber:
                self.episodes = {}
                self.config()
        else:
            self.renumberdict = {}
            for item in self.itemlist:
                if item.contentType != 'movie':
                    item.context = [{"title": typo(config.getLocalizedString(70585), 'bold'),
                                     "action": "start",
                                     "channel": "autorenumber",
                                     "from_channel": item.channel,
                                     "from_action": item.action}]

    def config(self):
        # Pulizia del Titolo
        if any( word in self.title.lower() for word in ['specials', 'speciali']):
            self.title = re.sub(r'\s*specials|\s*speciali', '', self.title.lower())
        elif not self.item.infoLabels['tmdb_id']:
            self.item.contentSerieName = self.title.rstrip('123456789 ')

        self.item.contentType = 'tvshow'

        if not self.item.disabletmdb:
            self.item.infoLabels['imdb_id'] = ''
            self.item.infoLabels['tvdb_id'] = ''
            self.item.infoLabels['tmdb_id'] = ''
            self.item.infoLabels['year'] = '-'

            while not self.item.exit:
                tmdb.find_and_set_infoLabels(self.item)
                if self.item.infoLabels['tmdb_id']: self.item.exit = True
                else:self.item = platformtools.dialogInfo(self.item, 'tmdb')

        # Rinumerazione Automatica
        if (not self.id and self.auto) or self.item.setrenumber:
            self.id = self.item.infoLabels['tmdb_id'] if 'tmdb_id' in self.item.infoLabels else 0
            if self.id:
                self.series = {ID: self.id}
                self.renumberdict[self.title] = self.series
                if any(word in self.title.lower() for word in ['specials', 'speciali']): season = 0
                elif RepresentsInt(self.title.split()[-1]): season = int(self.title.split()[-1])
                else: season = 1
                self.season = self.series[SEASON] = season
                self.episode = 1
                self.renumber()


    def renumber(self):
        def sub_thread(item):
            if type(item.contentSeason) != int:
                number = str(item.contentEpisodeNumber)
                if number:
                    if not number in self.episodes: self.makelist()
                    if number in self.episodes:
                        item.contentSeason = int(self.episodes[number].split('x')[0])
                        item.contentEpisodeNumber = int(self.episodes[number].split('x')[1])

        # logger.dbg()
        # for i in self.itemlist:
        #     sub_thread(i)

        if not self.item.setrenumber and self.itemlist:
            with futures.ThreadPoolExecutor() as executor:
                renumber_list = [executor.submit(sub_thread, item,) for item in self.itemlist]

        else:
            self.makelist()


    def makelist(self):
        self.epdict = {}
        self.group = self.renumberdict[self.title].get(GROUP, None)
        busy(True)
        itemlist = self.itemlist if self.itemlist else find_episodes(self.item)


        if not self.group:
            self.group = tmdb.get_nfo(self.item)

        if not self.group:
            busy(False)
            return

        # if 'episode_group' in self.group:
        #     seasons =[]
        #     groupedSeasons = tmdb.get_group(self.group.replace('\n','').split('/')[-1])
        #     for groupedSeason in groupedSeasons:
        #         if groupedSeason['episodes'][0]['season_number'] > 0:
        #             seasons.append({'season_number':groupedSeason['episodes'][0]['season_number'], 'episode_count':len(groupedSeason['episodes']), 'start_from':groupedSeason['episodes'][0]['episode_number']})
        # else:
        seasons = tmdb.Tmdb(id_Tmdb=self.id).get_list_episodes()
        busy(False)
        count = 0
        for season in seasons:
            s = season['season_number']
            c = season['episode_count']
            fe = season['start_from']
            self.seasonsdict[str(s)] = c
            if s > 0:
                for e in range(1, c + 1):
                    count += 1
                    self.epdict[count] = '{}x{:02d}'.format(s, e + fe - 1)

        if self.item.setrenumber or self.manual:
            self.item.setrenumber = False
            self.season, self.episode, self.manual, self.specials, Manual, Exit = SelectreNumeration(self, itemlist)
            if Exit:
                self.item.exit = True
                return
        if self.manual:
            self.episodes = Manual

        else:
            firstep = 0
            if self.season > 1:
                for c in range(1, self.season):
                    firstep += self.seasonsdict[str(c)]
            firstep += self.episode - 1
            count = 0
            if self.epdict:
                for item in itemlist:
                    if not item.contentSeason:
                        # Otiene Numerazione Episodi
                        scraped_ep = item.contentEpisodeNumber
                        if scraped_ep:
                            episode = int(scraped_ep)
                            if episode == 0:
                                self.episodes[str(episode)] = '0x01'
                            elif str(episode) in self.specials:
                                self.episodes[str(episode)] = self.specials[str(episode)]
                                count += 1
                            elif episode - count + firstep in self.epdict:
                                self.episodes[str(episode)] = self.epdict[episode - count + firstep]
                            else:
                                self.episodes[str(episode)] = '0x{:02d}'.format(count + 1)
                                count += 1

        if self.episodes: self.renumberdict[self.title][EPISODES] = self.episodes
        if self.group: self.renumberdict[self.title][GROUP] = self.group
        self.renumberdict[self.title][MANUALMODE] = self.manual
        self.renumberdict[self.title][SEASON] = self.season
        self.renumberdict[self.title][EPISODE] = self.episode
        self.renumberdict[self.title][SPECIALEPISODES] = self.specials
        self.renumberdict[self.title][SEASONSDICT] = self.seasonsdict
        write(self.item, self.renumberdict)
        # if self.auto: self.renumber()









def SelectreNumeration(opt, itemlist, manual=False):
    class SelectreNumerationWindow(xbmcgui.WindowXMLDialog):
        def start(self, opt):
            self.episodes = opt.episodes if opt.episodes else {}
            self.renumberdict = opt.renumberdict
            self.item = opt.item
            self.title = opt.title
            self.season = opt.season
            self.episode = opt.episode
            self.manual = opt.manual
            self.sp = opt.selectspecials
            self.manual = opt.manual
            self.offset = 0
            self.Exit = False

            self.itemlist = opt.itemlist
            self.count = 1
            self.specials = opt.specials
            self.items = []
            self.selected = []
            self.seasons = {}
            self.seasonsdict = opt.seasonsdict

            self.doModal()
            return self.season, self.episode, self.manual, self.specials, self.seasons, self.Exit

        def onInit(self):
            # Compatibility with Kodi 18
            if config.getXBMCPlatform(True)['num_version'] < 18: self.setCoordinateResolution(2)
            fanart = self.item.fanart
            thumb = self.item.thumbnail
            self.getControl(SELECT).setVisible(False)
            self.getControl(SPECIALS).setVisible(False)
            self.getControl(MANUAL).setVisible(False)
            # MANUAL
            if self.manual:
                self.getControl(MANUAL).setVisible(True)
                self.getControl(MPOSTER).setImage(thumb)
                if fanart: self.getControl(MBACKGROUND).setImage(fanart)
                self.getControl(INFO).setLabel(typo(config.getLocalizedString(70822) + self.title, 'bold'))

                self.manual = True

                se = '1'
                ep = '1'
                position = 0
                for i, item in enumerate(self.itemlist):
                    title = str(item.contentEpisodeNumber)
                    it = xbmcgui.ListItem(title)
                    if int(title) <= len(self.episodes):
                        se, ep = self.episodes[title].split('x')
                    else:
                        if position == 0: position = i
                        ep = str(int(ep) + 1)
                    it.setProperties({'season': se, "episode": ep})
                    self.items.append(it)
                self.makerenumber()
                self.addseasons()
                season = self.getControl(MSEASONS).getSelectedItem().getLabel()
                self.getControl(MSEP).reset()
                self.getControl(MSEP).addItems(self.episodes[season])
                self.getControl(MLIST).addItems(self.items)
                self.setFocusId(MLIST)
                self.getControl(MLIST).selectItem(position)
            # MAIN / SPECIALS
            else:
                for item in self.itemlist:
                    if not item.contentSeason:
                        title = str(item.contentEpisodeNumber)
                        it = xbmcgui.ListItem(title)
                        if title not in self.specials.keys():
                            self.items.append(it)
                        else:
                            self.selected.append(it)
                            it.setProperty('title', title)

                self.getControl(POSTER).setImage(thumb)
                self.getControl(MPOSTER).setImage(thumb)
                if fanart:
                    self.getControl(BACKGROUND).setImage(fanart)
                    self.getControl(MBACKGROUND).setImage(fanart)
                self.getControl(INFO).setLabel(typo(config.getLocalizedString(70824) + self.title, 'bold'))
                self.getControl(LIST).addItems(self.items)
                self.getControl(SELECTED).addItems(self.selected)

                if self.sp:
                    self.getControl(SPECIALS).setVisible(True)
                    self.setFocusId(OK)
                else:
                    self.getControl(SELECT).setVisible(True)

                    self.getControl(S).setLabel(str(self.season))
                    self.getControl(E).setLabel(str(self.episode))

                    self.setFocusId(O)

        def onFocus(self, focus):
            if focus in [S]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70825), 'bold'))
            elif focus in [E]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70826), 'bold'))
            elif focus in [O]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70001), 'bold'))
            elif focus in [SS]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70827), 'bold'))
            elif focus in [M]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70828), 'bold'))
            elif focus in [D]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70829) + self.title, 'bold'))
            elif focus in [C]:
                self.getControl(108).setLabel(typo(config.getLocalizedString(70002), 'bold'))

        def onAction(self, action):
            action = action.getId()
            focus = self.getFocusId()
            # SEASON SELECT
            if 100 < focus < 200:
                s = int(self.getControl(S).getLabel())
                e = int(self.getControl(E).getLabel())
                if action in [RIGHT]:
                    if focus in [C]:
                        self.setFocusId(S)
                    else:
                        self.setFocusId(focus + 1)
                elif action in [LEFT]:
                    if focus in [S]:
                        self.setFocusId(C)
                    else:
                        self.setFocusId(focus - 1)
                elif action in [UP]:
                    if focus in [S]:
                        if str(s + 1) in self.seasonsdict:
                            s += 1
                            self.getControl(S).setLabel(str(s))
                    elif focus in [E]:
                        if self.seasonsdict[str(s)] > e:
                            e += 1
                            self.getControl(E).setLabel(str(e))
                elif action in [DOWN]:
                    if focus in [S]:
                        if str(s - 1) in self.seasonsdict: s -= 1
                        self.getControl(S).setLabel(str(s))
                    elif focus in [E]:
                        if e > 1: e -= 1
                        self.getControl(E).setLabel(str(e))
            # MANUAL
            if focus in [MS, ME]:
                s = int(self.getControl(MLIST).getSelectedItem().getProperty('season'))
                e = int(self.getControl(MLIST).getSelectedItem().getProperty('episode'))
                pos = self.getControl(MLIST).getSelectedPosition()
                # Set Season
                if focus in [MS] and action in [UP]:
                    s += 1
                elif focus in [MS] and action in [DOWN] and s > 0:
                    s -= 1
                # Set Episode
                if focus in [ME] and action in [UP]:
                    e += 1
                elif focus in [ME] and action in [DOWN] and e > 0:
                    e -= 1
                if action in [UP, DOWN]:
                    if s != self.season: e = 1
                    self.season = s
                    self.episode = e
                    self.makerenumber(pos)
                    self.addseasons()
                    season = self.getControl(MSEASONS).getSelectedItem().getLabel()
                    self.getControl(MSEP).reset()
                    self.getControl(MSEP).addItems(self.episodes[season])
                    self.getControl(MLIST).reset()
                    self.getControl(MLIST).addItems(self.items)
                    self.getControl(MLIST).selectItem(pos)
            if focus in [MSEASONS]:
                season = self.getControl(MSEASONS).getSelectedItem().getLabel()
                self.getControl(MSEP).reset()
                self.getControl(MSEP).addItems(self.episodes[season])

            # EXIT
            if action in [EXIT, BACKSPACE]:
                self.Exit = True
                self.close()

        def onClick(self, control_id):
            ## FIRST SECTION
            if control_id in [S]:
                selected = platformtools.dialogNumeric(0, config.getLocalizedString(70825),
                                                        self.getControl(S).getLabel())
                if selected: s = self.getControl(S).setLabel(selected)
            elif control_id in [E]:
                selected = platformtools.dialogNumeric(0, config.getLocalizedString(70826),
                                                        self.getControl(E).getLabel())
                if selected: e = self.getControl(E).setLabel(selected)
            # OPEN SPECIALS OR OK
            if control_id in [O, SS]:
                s = self.getControl(S).getLabel()
                e = self.getControl(E).getLabel()
                self.season = int(s)
                self.episode = int(e)
                if control_id in [O]:
                    self.close()
                elif control_id in [SS]:
                    self.getControl(SELECT).setVisible(False)
                    self.getControl(SPECIALS).setVisible(True)
                    self.setFocusId(OK)
            # OPEN MANUAL
            elif control_id in [M]:
                self.getControl(INFO).setLabel(typo(config.getLocalizedString(70823) + self.title, 'bold'))
                self.manual = True
                if self.episodes:
                    items = []
                    se = '1'
                    ep = '1'
                    for item in self.items:
                        if int(item.getLabel()) <= len(self.episodes) - 1:
                            se, ep = self.episodes[item.getLabel()].split('x')
                        else:
                            ep = str(int(ep) + 1)
                        item.setProperties({'season': se, "episode": ep})
                        items.append(item)
                        self.seasons[item.getLabel()] = '{}x{}'.format(se, ep)
                    self.items = items
                else:
                    self.makerenumber()
                self.addseasons()
                season = self.getControl(MSEASONS).getSelectedItem().getLabel()
                self.getControl(MSEP).reset()
                self.getControl(MSEP).addItems(self.episodes[season])
                self.getControl(MLIST).addItems(self.items)
                self.getControl(SELECT).setVisible(False)
                self.getControl(MANUAL).setVisible(True)
                self.setFocusId(OK)
            # CLOSE
            elif control_id in [C]:
                self.Exit = True
                self.close()
            # DELETE
            if control_id in [D]:
                self.Exit = True
                self.renumberdict.pop(self.title)
                write(self.item, self.renumberdict)
                self.close()

            ## SPECIAL SECTION
            # ADD TO SPECIALS
            p1 = self.getControl(SELECTED).getSelectedPosition()
            if control_id in [LIST]:
                item = self.getControl(LIST).getSelectedItem()
                it = xbmcgui.ListItem(str(len(self.selected) + 1))
                it.setProperty('title', item.getLabel())
                self.selected.append(it)
                index = self.getControl(SELECTED).getSelectedPosition()
                self.getControl(SELECTED).reset()
                self.getControl(SELECTED).addItems(self.selected)
                self.getControl(SELECTED).selectItem(index)

                index = self.getControl(LIST).getSelectedPosition()
                self.items.pop(index)
                self.getControl(LIST).reset()
                self.getControl(LIST).addItems(self.items)
                if index == len(self.items): index -= 1
                self.getControl(LIST).selectItem(index)
            # MOVE SPECIALS
            elif control_id in [SU]:
                p2 = p1 - 1
                if p2 > -1:
                    self.selected[p1], self.selected[p2] = self.selected[p2], self.selected[p1]
                    for i, it in enumerate(self.selected):
                        it.setLabel(str(i + 1))
                    self.getControl(SELECTED).reset()
                    self.getControl(SELECTED).addItems(self.selected)
                    self.getControl(SELECTED).selectItem(p2)

            elif control_id in [SD]:
                p2 = p1 + 1
                if p2 < len(self.selected):
                    self.selected[p1], self.selected[p2] = self.selected[p2], self.selected[p1]
                    for i, it in enumerate(self.selected):
                        it.setLabel(str(i + 1))
                    self.getControl(SELECTED).reset()
                    self.getControl(SELECTED).addItems(self.selected)
                    self.getControl(SELECTED).selectItem(p2)
            # REMOVE FROM SPECIALS
            elif control_id in [SR]:
                item = self.getControl(SELECTED).getSelectedItem()
                it = xbmcgui.ListItem(item.getProperty('title'))
                if int(item.getProperty('title')) < int(self.items[-1].getLabel()):
                    for i, itm in enumerate(self.items):
                        if int(itm.getLabel()) > int(item.getProperty('title')):
                            self.items.insert(i, it)
                            break
                else:
                    self.items.append(it)
                self.getControl(LIST).reset()
                self.getControl(LIST).addItems(self.items)
                index = self.getControl(SELECTED).getSelectedPosition()
                self.selected.pop(index)
                self.getControl(SELECTED).reset()
                self.getControl(SELECTED).addItems(self.selected)

                if index == len(self.selected): index -= 1
                self.getControl(SELECTED).selectItem(index)
            # RELOAD SPECIALS
            if control_id in [SELECTED]:
                epnumber = platformtools.dialogNumeric(0, config.getLocalizedString(60386))
                if epnumber:
                    it = self.getControl(SELECTED).getSelectedItem()
                    it.setLabel(str(epnumber))
                    self.selected.sort(key=lambda it: int(it.getLabel()))
                    for i, it in enumerate(self.selected):
                        if it.getLabel() == epnumber: pos = i
                        self.selected.sort(key=lambda it: int(it.getLabel()))
                        self.getControl(SELECTED).reset()
                        self.getControl(SELECTED).addItems(self.selected)
                        self.getControl(SELECTED).selectItem(pos)
                        break
            if len(self.selected) > 0:
                self.getControl(SPECIALCOMMANDS).setVisible(True)
            else:
                self.setFocusId(LIST)
                self.getControl(SPECIALCOMMANDS).setVisible(False)

            ## MANUAL SECTION
            # SELECT SEASON EPISODE (MANUAL)
            if control_id in [MS, ME]:
                s = int(self.getControl(MLIST).getSelectedItem().getProperty('season'))
                e = int(self.getControl(MLIST).getSelectedItem().getProperty('episode'))
                pos = self.getControl(MLIST).getSelectedPosition()
                if control_id in [MS]:
                    selected = platformtools.dialogNumeric(0, config.getLocalizedString(70825), str(s))
                    if selected: s = int(selected)
                elif control_id in [ME]:
                    selected = platformtools.dialogNumeric(0, config.getLocalizedString(70826), str(e))
                    if selected: e = int(selected)
                if s != self.season or e != self.episode:
                    self.season = s
                    self.episode = 1 if s != self.season else e
                    self.makerenumber(pos)
                    self.addseasons()
                    season = self.getControl(MSEASONS).getSelectedItem().getLabel()
                    self.getControl(MSEP).reset()
                    self.getControl(MSEP).addItems(self.episodes[season])
                    self.getControl(MLIST).reset()
                    self.getControl(MLIST).addItems(self.items)
                    self.getControl(MLIST).selectItem(pos)
            # OK
            if control_id in [OK]:
                if not self.selected:
                    self.specials = {}
                for it in self.selected:
                    self.specials[it.getProperty('title')] = '0x' + it.getLabel()
                self.close()
            # CLOSE
            elif control_id in [CLOSE]:
                self.Exit = True
                self.close()

        def makerenumber(self, pos=0):
            items = []
            currentSeason = self.items[pos].getProperty('season')
            previousSeason = self.items[pos - 1 if pos > 0 else 0].getProperty('season')
            prevEpisode = self.items[pos - 1 if pos > 0 else 0].getProperty('episode')
            if currentSeason != str(self.season):
                if str(self.season) == previousSeason:
                    prevEpisode = int(prevEpisode) + 1
                else:
                    prevEpisode = 1
            else:
                prevEpisode = self.episode

            for i, item in enumerate(self.items):
                if (i >= pos and item.getProperty('season') == currentSeason) or not item.getProperty('season'):
                    if i > pos: prevEpisode += 1
                    item.setProperties({'season': self.season, 'episode': prevEpisode})
                items.append(item)
                self.seasons[item.getLabel()] = '{}x{}'.format(item.getProperty('season'), item.getProperty('episode'))
            self.items = items
            logger.debug('SELF', self.seasons)

        def addseasons(self):
            seasonlist = []
            seasons = []
            self.episodes = {}
            for ep, value in self.seasons.items():
                season = value.split('x')[0]
                if season not in seasonlist:
                    item = xbmcgui.ListItem(season)
                    seasonlist.append(season)
                    seasons.append(item)
                if season in seasonlist:
                    if season not in self.episodes:
                        self.episodes[season] = []
                    item = xbmcgui.ListItem('{} - Ep. {}'.format(value, ep))
                    item.setProperty('episode', ep)
                    self.episodes[season].append(item)
                    logger.log('EPISODES', self.episodes[season])
                self.episodes[season].sort(key=lambda it: int(it.getProperty('episode')))

            seasons.sort(key=lambda it: int(it.getLabel()))
            self.getControl(MSEASONS).reset()
            self.getControl(MSEASONS).addItems(seasons)

    opt.itemlist = itemlist
    opt.manual = manual
    return SelectreNumerationWindow('Renumber.xml', path).start(opt)

# Select Season
SELECT = 100
S = 101
E = 102
O = 103
SS = 104
M = 105
D = 106
C = 107

# Main
MAIN = 10000
INFO = 10001
OK=10002
CLOSE = 10003

# Select Specials
SPECIALS = 200
POSTER= 201
LIST = 202
SELECTED = 203
BACKGROUND = 208

SPECIALCOMMANDS = 204
SU = 205
SD = 206
SR = 207

# Select Manual
MANUAL = 300
MPOSTER= 301
MLIST = 302
MSEASONS = 303
MSEP = 304
MBACKGROUND = 310

MANUALEP = 305
MS = 306
ME = 307
MSS = 308
MC = 309

# Actions
LEFT = 1
RIGHT = 2
UP = 3
DOWN = 4
EXIT = 10
BACKSPACE = 92

path = config.getRuntimePath()