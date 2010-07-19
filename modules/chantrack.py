from datetime import datetime
import modules
import networks
import struct
import socket

USER_MODES = 'ovhqa'
CHANNEL_MODES = 'cimnprstuzACGMKNOQRSTV'
ARG_MODES = 'befIjklL'
PREFIX_MODES = {'~': 'q', '&': 'a', '@': 'o', '%': 'h', '+': 'v'}

channels = {}

known_mibbits = {}

def init():
    add_hook('join', join)
    add_hook('332', initial_topic)
    add_hook('topic', topic)
    add_hook('353', userlist)
    add_hook('319', channel_list)
    add_hook('302', userhosts)
    add_hook('part', part)
    add_hook('kick', kick)
    add_hook('quit', quit)
    add_hook('nick', nick)
    add_hook('324', initial_mode)
    add_hook('mode', mode)
    
    for network in networks.networks:
        irc = networks.networks[network]
        if irc.connected:
            irc.raw("WHOIS %s" % irc.nick)

def channel_list(irc, origin, args):
    if args[1] == irc.nick:
        channels = [x.lstrip(''.join(PREFIX_MODES.keys())) for x in args[2].split(' ')]
        for channel in channels:
            irc.raw("NAMES %s" % channel)
            irc.raw("MODE %s" % channel)

def resolve_mibbit(user):
    if user.ident in known_mibbits:
        user.hostname = known_mibbits[user.ident]
        user.ident = 'mibbit'
    else:
        try:
            packed_ip = struct.pack('!I', int(user.ident, 16))
            dotted_ip = socket.inet_ntoa(packed_ip)
            try:
                hostname = socket.gethostbyaddr(dotted_ip)[0]
            except:
                hostname = dotted_ip
            known_mibbits[user.ident] = hostname
            user.ident = 'mibbit'
            user.hostname = hostname
        except Exception, e:
            logger.warn("Unable to resolve mibbit address: %s" % e)

def userhosts(irc, origin, args):
    data = args[1].strip().split(' ')
    for datum in data:
        if not datum:
            continue
        datum = datum.split('=', 1)
        nick = datum[0].rstrip('*')
        hostmask = datum[1].lstrip('+-').split('@', 1)
        ident = hostmask[0]
        host = hostmask[1]
        channels = nick_channels(irc, nick)
        if channels:
            for channame in channels:
                logger.debug("Updating %s in %s" % (nick, channame))
                channel = network(irc)[channame]
                user = channel.users[nick.lower()]
                user.ident = ident
                user.hostname = host
                if user.hostname.endswith('mibbit.com'):
                    resolve_mibbit(user)
            logger.debug("Updated ident/host for %s" % nick)
            

def network(irc):
    if not channels.get(irc.network.name):
        channels[irc.network.name] = {}
    return channels[irc.network.name]

def join(irc, origin, args):
    channel = args[0].lower()
    if origin.nick == irc.nick:
        network(irc)[channel] = Channel(name=channel)
        logger.debug("Added channel %s/%s" % (irc.network, channel))
        modules.call_hook('joined', irc, channel)
        irc.raw("MODE %s" % channel)
    else:
        logger.debug("Added nick %s to %s/%s" % (origin.nick, irc.network, channel))
    user = create_user(irc, origin.nick)
    network(irc)[channel].users[origin.nick.lower()] = user
    if not user.hostname:
        irc.raw("USERHOST %s" % origin.nick)

def mode(irc, origin, args):
    channel = args[0]
    modes = args[1]
    args = args[2:]
    try: # lazy solution (to a problem that shouldn't exist anyway)!
        channel = network(irc)[channel.lower()]
    except:
        return
    arg_pointer = 0
    direction = 1
    for mode in modes:
        if mode == '+':
            direction = 1
        elif mode == '-':
            direction = -1
        elif mode in USER_MODES:
            nick = args[arg_pointer]
            arg_pointer += 1
            if nick.lower() in channel.users:
                user = channel.users[nick.lower()]
                if direction > 0:
                    user.modes.add(mode)
                elif direction < 0 and mode in user.modes:
                    user.modes.remove(mode)
        elif mode in CHANNEL_MODES:
            if direction > 0:
                channel.modes.add(mode)
            elif direction < 0 and mode in channel.modes:
                channel.modes.remove(mode)
        elif mode in ARG_MODES:
            arg_pointer += 1

def initial_mode(irc, origin, args):
    mode(irc, origin, args[1:])
        

def initial_topic(irc, origin, args):
    channel = args[1].lower()
    network(irc)[channel].topic = args[2]
    logger.debug('Set topic for %s/%s to "%s"' % (irc.network, channel, args[2]))

def topic(irc, origin, args):
    channel = args[0].lower()
    topic = args[1]
    network(irc)[channel].topic = topic
    logger.debug('Updated topic for %s/%s to "%s"' % (irc.network, channel, topic))

def userlist(irc, origin, args):
    channel_name = args[2].lower()
    if channel_name not in network(irc):
        network(irc)[channel_name] = Channel(name=args[2])
    channel = network(irc)[channel_name]
    nicks = args[3].split(' ')
    lookup = []
    for nick in nicks:
        user = create_user(irc, nick)
        channel.users[user.nick.lower()] = user
        if not user.hostname:
            lookup.append(user.nick)
        logger.debug("Added nick %s to %s/%s" % (user.nick, irc.network, channel))
    if lookup:
        for i in range(0, len(lookup), 5):
            irc.raw("USERHOST %s" % ' '.join(lookup[i:i+5]))

def part(irc, origin, args):
    channel = args[0].lower()
    if irc.nick == origin.nick:
        del network(irc)[channel]
        logger.debug("Removed channel %s/%s" % (irc.network, channel))
        modules.call_hook('parted', irc, channel)
    else:
        del network(irc)[channel].users[origin.nick.lower()]
        logger.debug("Removed nick %s from %s/%s" % (origin.nick, irc.network, channel))

def kick(irc, origin, args):
    channel = args[0].lower()
    nick = args[1].lower()
    if nick == irc.nick.lower():
        del network(irc)[channel]
        logger.debug("Removed channel %s/%s" % (irc.network.name, channel))
        modules.call_hook('parted', irc, channel)
    else:
        del network(irc)[channel].users[nick]
        logger.debug("Removed nick %s from %s/%s" % (nick, irc.network, channel))

def quit(irc, origin, args):
    if origin.nick == irc.nick:
        return
    nick = origin.nick.lower()
    for channel_name in network(irc):
        channel = network(irc)[channel_name]
        if channel.users.get(nick):
            del channel.users[nick]
            logger.debug("Removed nick %s from %s/%s" % (origin.nick, irc.network, channel))

def nick(irc, origin, args):
    newnick = args[0]
    if origin.nick == irc.nick:
        irc.nick = newnick
    else:
        for channel_name in network(irc):
            channel = network(irc)[channel_name]
            if channel.users.get(origin.nick.lower()):
                channel.users[newnick.lower()] = channel.users[origin.nick.lower()]
                channel.users[newnick.lower()].nick = newnick
                del channel.users[origin.nick.lower()]
                logger.debug("Renamed %s to %s in %s/%s" % (origin.nick, newnick, irc.network, channel))

# Information access

def nick_channels(irc, nick):
    channels = []
    for channel_name in network(irc):
        channel = network(irc)[channel_name]
        if nick.lower() in channel.users:
            channels.append(channel_name)
    
    return channels

def create_user(irc, nick):
    existing = nick_channels(irc, nick)
    user = User(nick=nick)
    if existing:
        existing = network(irc)[existing[0]].users[nick.lower()]
        user.ident = existing.ident
        user.hostname = existing.hostname
    return user

def uid_channels(irc, uid):
    nick = m('security').get_user_nick(uid)
    aliases = set([x.lower() for x in m('security').get_nick_aliases(nick)])
    aliases.add(nick.lower())
    channels = {}
    for channel_name in network(irc):
        channel = network(irc)[channel_name]
        intersection = aliases.intersection(channel.users.keys())
        if len(intersection) != 0:
            nick = channel.users[intersection.pop()].nick
            channels[channel.name] = nick
    return channels
    

class Channel(object):
    users = None
    topic = ''
    joined = None
    name = ''
    modes = None
    
    def __init__(self, name='', topic=''):
        self.users = {}
        joined = datetime.now()
        self.name = name
        self.topic = topic
        self.modes = set()
        
    def __str__(self):
        return self.name

class User(object):
    nick = ''
    hostname = ''
    modes = None
    ident = ''
    
    def __init__(self, nick='', hostname='', modes=None, ident=''):
        self.modes = modes
        if self.modes is None:
            self.modes = set()
        
        modechar = nick[0]
        if modechar in PREFIX_MODES:
            nick = nick[1:]
            self.modes.add(PREFIX_MODES[modechar])
        self.nick = nick
        self.hostname = hostname
        self.ident = ident
    
    def __str__(self):
        return '%s!%s@%s' % (self.nick, self.ident, self.hostname)
    
    def __repr__(self):
        return '<%s>' % self.__str__()