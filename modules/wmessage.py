# encoding=utf-8
#
#Davy//16-7-09
#

cmdtag = '~B[Welcome Message]~B'

def init():
    add_hook('join',join)
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    irc_helpers = m('irc_helpers')
    target = channel
    if command == 'welcome':
        wmessage = m('datastore').query('SELECT message FROM wmessage WHERE channel = ? AND network = ?', target, irc.network.name)
        if len(wmessage) > 0:
            irc_helpers.message(irc,target,'%s "%s"' % (cmdtag, wmessage[0][0]))
        else:
            irc_helpers.message(irc,target,'%s No welcome message set for ~B%s~B.' % (cmdtag, target))
    elif not m('security').check_action_permissible(origin, command):
        return
    elif command == 'setwelcome':
        if len(args) != 0:
            message = ' '.join(args)
            m('datastore').execute('REPLACE INTO wmessage (channel, network, message) VALUES (?, ?, ?)', target, irc.network.name, message)
            irc_helpers.message(irc,target,"Welcome message for channel ~B%s~B was updated." % target)
        else:
            m('datastore').execute('DELETE FROM wmessage WHERE channel = ? AND network = ?', target, irc.network.name)
            irc_helpers.message(irc,target,"Removed welcome message for ~B%s~B." % target)
    elif command == 'delwelcome':
        m('datastore').execute('DELETE FROM wmessage WHERE channel = ? AND network = ?', target, irc.network.name)
        irc_helpers.message(irc,target,"Removed welcome message for ~B%s~B." % target)

def join(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target = args[0]
    wmessage = m('datastore').query('SELECT message FROM wmessage WHERE channel = ? AND network = ?', target, irc.network.name)
    if len(wmessage) > 0:
        irc_helpers.message(irc, target,'%s "%s"' % (cmdtag, wmessage[0][0]))