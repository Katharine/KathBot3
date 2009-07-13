# encoding=utf-8
import threading
import urllib2
import networks
import time
from irc import User

DATA_URL = "http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.txt"
POLL_INTERVAL = 60

class LastFMPoll(threading.Thread):
    running = True
    
    def get_latest(self, user):
        f = urllib2.urlopen(DATA_URL % user)
        data = f.read().decode('utf-8')
        f.close()
        most_recent = data.split("\n", 1)[0].split(',', 1)
        return most_recent
    
    def log_update(self, nick, song):
        artist, song = song.split(u' – ', 1)
        for network in networks.networks:
            irc = networks.networks[network]
            channels = m('chantrack').nick_channels(irc, nick)
            for channel in channels:
                #m('irc_helpers').message(irc, channel, "~B[last.fm]~B %s is listening to %s by %s" % (nick, song, artist))
                m('logger').privmsg(irc, User(nick=nick), [channel, '\x01ACTION is listening to "%s" by %s (last.fm).\x01' % (song, artist)])
    
    def update_all(self):
        users = m('datastore').query("SELECT nick, lastfm, lastid FROM lastfm")
        for user in users:
            try:
                data = self.get_latest(user[1])
            except Exception, message:
                logger.warn("Failed loading data for %s: %s." % (user[0], message))
                continue
            if user[2] is None or int(data[0]) != int(user[2]):
                m('datastore').execute("UPDATE lastfm SET lastid = ?, lastsong = ? WHERE nick = ?", data[0], data[1], user[0])
                self.log_update(user[0], data[1])
    
    def run(self):
        while self.running:
            self.update_all()
            time.sleep(POLL_INTERVAL)

poll = None

def init():
    global poll
    poll = LastFMPoll()
    poll.start()
    
    add_hook('privmsg', privmsg)

def shutdown():
    poll.running = False

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if command == 'lastfm':
        if len(args) != 1:
            irc_helpers.message(irc, target, "You must state your last.fm username.")
            return
        lastfm = args[0]
        try:
            now_playing = poll.get_latest(lastfm)
        except:
            irc_helpers.message(irc, target, "That username is invalid.")
            return
        m('datastore').execute("REPLACE INTO lastfm (nick, lastfm) VALUES (?, ?)", origin.nick, lastfm)
        irc_helpers.message(irc, target, "Set your last.fm username to %s (and you're currently listening to %s)" % (lastfm, now_playing[1]))