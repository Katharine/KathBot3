# Note that this module assumes use of a hacked pisg.

from __future__ import with_statement
import os
import subprocess
import threading

PISG_OUTPUT = "data/web/pisg/"
PISG_WEB_URL = "%sstatic/pisg/%s/%s.html"

pisg_in_progress = set()
progress_lock = threading.Lock()
def run_pisg(network, channel, irc=None):
    with progress_lock:
        pisg_in_progress.add((network, channel))
    update_nicks()
    if irc is not None:
        m('irc_helpers').message(irc, channel, "Generating stats...")
    if not os.path.exists(PISG_OUTPUT+network):
        os.mkdir(PISG_OUTPUT+network)
    subprocess.check_call([
        'pisg',
        '-co', 'data/pisg/base.cfg',
        '-ne', network,
        '-ch', channel,
        '-o', "%s%s/%s.html" % (PISG_OUTPUT, network.replace('/','_'), channel[1:].replace('/','_')),
        '-l', 'data/logs/%s/%s.log' % (network.replace('/','_'), channel.replace('/','_')),
    ])
    if irc is not None:
        url = PISG_WEB_URL % (m('webserver').get_root_address(), network, channel[1:])
        m('irc_helpers').message(irc, channel, "Stats generation completed. You can see them at %s" % url)
    with progress_lock:
        pisg_in_progress.remove((network, channel))

def update_nicks():
    users = m('datastore').query("SELECT nick FROM users")
    nicks = {}
    for user in users:
        nick = user[0]
        nicks[nick] = StatUser(nick)
    more_users = m('datastore').query("SELECT nick FROM pisg_data")
    for user in more_users:
        nick = user[0]
        if nick not in nicks:
            nicks[nick] = StatUser(nick)
    with open('data/pisg/nicks.cfg', 'w') as f:
        for nick in nicks:
            user = nicks[nick]
            f.write('<user nick="%s" alias="%s" sex="%s">\n' % (nick, ' '.join(user.aliases), user.gender))

def pisg(network, channel, irc=None):
    with progress_lock:
        if (network, channel) in pisg_in_progress:
            if irc:
                m('irc_helpers').message(irc, channel, "Stats generation is in progress. Please be patient.")
            return
    thread = threading.Thread(target=run_pisg, name="pisg-manual-%s-%s" % (network, channel), args=(network, channel), kwargs={'irc': irc})
    thread.start()

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == 'stats':
        pisg(irc.network.name, channel, irc)
    elif command == 'gender':
        gender = args[0] if len(args) > 0 else None
        nick = m('security').get_canonical_nick(origin.nick)
        if gender in ('m', 'f', 'b'):
            count = m('datastore').query("SELECT COUNT(nick) FROM pisg_data WHERE nick = ?", nick)[0][0]
            if count:
                m('datastore').execute("UPDATE pisg_data SET gender = ? WHERE nick = ?", gender, nick)
            else:
                m('datastore').execute("INSERT INTO pisg_data (nick, gender) VALUES (?, ?)", nick, gender)
            m('irc_helpers').message(irc, channel, "Gender updated.")
        else:
            m('irc_helpers').message(irc, channel, "Please specify 'm' for male, 'f' for female, or 'b' for bot.")

class StatUser(object):
    aliases = None
    nick = ''
    gender = ''
    
    def __init__(self, nick):
        self.nick = nick
        self.aliases = [x[0] for x  in m('datastore').query("SELECT alias FROM aliases WHERE canon = ?", nick)]
        data = m('datastore').query("SELECT gender FROM pisg_data WHERE nick = ?", nick)
        if len(data) > 0:
            self.gender = data[0][0].lower()