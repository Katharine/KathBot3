# encoding: utf-8

from lupa import LuaError

def init():
    # Fix up modules our submodules need but can't get at.
    web.interpreter = interpreter
    web.m = m
    interpreter.m = m

    add_hook('message', message)
    m('webserver').add_handler('GET', web.editor)
    m('webserver').add_handler('POST', web.editor)



def message(irc, channel, origin, command, args):
    if command == 'lua':
        if not m('security').check_action_permissible(origin, command):
            return
        try:
            output = interpreter.execute(' '.join(args))
        except LuaError as e:
            m('irc_helpers').message(irc, channel, "%s" % e)
        else:
            m('irc_helpers').message(irc, channel, '[lua] %s' % (', '.join([unicode(x) for x in output])))
    elif command == 'editlua':
        if not m('security').check_action_permissible(origin, command):
            return
        m('irc_helpers').message(irc, origin.nick, web.generate_url(origin))

    interpreter.handle_message(irc, channel, origin, command, args)
