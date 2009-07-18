import time

automode = {}
mutes = {}

def init():
    add_hook('connected', connected)
    add_hook('join', join)
    add_hook('privmsg', privmsg)
    
    channels = m('datastore').query("SELECT network, channel, automode FROM channels")
    for channel in channels:
        if not automode.get(channel[0]):
            automode[channel[0].lower()] = {}
        if channel[2] is not None:
            automode[channel[0].lower()][channel[1].lower()] = channel[2]
            logger.info("Set automode for %s to +%s" % (channel[1], channel[2]))

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if not command:
        return
    if not m('security').check_action_permissible(origin, command):
        return
    if command == 'chanmode':
        modes = ''
        if len(args) >= 1:
            modes = args[0]
        m('datastore').execute("UPDATE channels SET automode = ? WHERE network = ? AND channel = ?", modes, irc.network.name, target)
        automode[irc.network.name.lower()][target.lower()] = modes
        irc_helpers.message(irc, target, "Updated automode settings for %s" % target)
    elif command == 'addchan':
        if len(args) < 1:
            irc_helpers.message(irc, target, "You need to specify a channel.")
            return
        channel = args[0]
        key = None
        if len(args) > 1:
            key = args[1]
        irc_helpers.join(irc, channel, key)
        m('datastore').execute("INSERT INTO channels(channel, network, passkey) VALUES(?, ?, ?)", channel.lower(), irc.network.name, key)
        irc_helpers.message(irc, target, "Joined %s." % channel)
    elif command == 'automode':
        if len(args) < 1:
            irc_helpers.message(irc, target, "You need to specify who you're changing modes for.")
            return
        nick = m('security').get_canonical_nick(args[0])
        uid = m('datastore').query("SELECT id FROM users WHERE nick = ?", nick)
        if len(uid) == 0:
            irc_helpers.message(irc, target, "Only %s users can have modes." % irc.nick)
            return
        uid = uid[0][0]
        if len(args) > 1:
            modes = args[1]
        else:
            modes = None
        
        m('datastore').execute("REPLACE INTO chanmanage_modes (channel, uid, modes) VALUES (?, ?, ?)", target.lower(), uid, modes)
        irc.raw("MODE %s +%s %s" % (target, modes, (nick + " ") * len(modes)))
        irc_helpers.message(irc, target, "Set mode ~B+%s~B for ~B%s~B in ~B%s~B." % (modes, nick, target))
    elif command == 'mute':
        modes = automodes(irc.network.name, target)
        if modes == '':
            irc_helpers.message(irc, target, "This channel has no automode, so muting makes no sense")
        try:
            nick = args[0]
            period = int(args[1])
        except:
            irc_helpers.message(irc, target, "Usage: mute [nick] [time]")
        key = '%s/%s' % (irc.network, target)
        if key not in mutes:
            mutes[key] = set()
        mutes[key].add(nick.lower())
        irc.raw("MODE %s -%s %s" % (target, modes, (nick + ' ') * len(modes)))
        m('cron').add_at(time.time() + period * 60, unmute, irc, target, nick)
        irc_helpers.message(irc, target, "Muted %s for %s minutes." % (nick, period))

def connected(irc):
    channels = m('datastore').query("SELECT channel, passkey FROM channels WHERE network = ?", irc.network.name)
    for channel in channels:
        m('irc_helpers').join(irc, channel[0], channel[1])

def join(irc, origin, args):
    channel = args[0].lower()
    try:
        if origin.nick.lower() in mutes['%s/%s' % (irc.network, channel)]:
            return
    except:
        pass
    modes = automodes(irc.network.name, channel)
    
    uid = m('security').get_user_id(origin)
    if uid is not None:
        user_modes = m('datastore').query("SELECT modes FROM chanmanage_modes WHERE channel = ? AND uid = ?", channel, uid)
        if len(user_modes) > 0 and user_modes[0][0]:
            modes += user_modes[0][0]
    
    irc.raw("MODE %s +%s %s" % (channel, modes, (origin.nick + " ") * len(modes)))

def automodes(network, channel):
    if automode.get(network) and automode[network.lower()].get(channel):
        return automode[network][channel]
    return ''

def unmute(irc, channel, nick):
    key = '%s/%s' % (irc.network, channel)
    if key not in mutes:
        return
    if nick.lower() not in mutes[key]:
        return
    mutes[key].remove(nick.lower())
    modes = automodes(irc.network.name, channel)
    if modes:
        irc.raw("MODE %s +%s %s" % (channel, modes, (nick + ' ') * len(modes)))