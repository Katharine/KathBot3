# encoding: utf-8


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
            m('irc_helpers').message(irc, channel, 'Access denied.')
            return
        try:
            lua = interpreter.LuaModule()
            output = lua.run(' '.join(args))
        except LuaError as e:
            m('irc_helpers').message(irc, channel, "%s" % e)
        else:
            try:
                output = list(output)
                success = output.pop(0)
            except:
                success = output
                output = []
            if success:
                m('irc_helpers').message(irc, channel, '[lua] %s' % (', '.join([unicode(x) for x in output])))
            else:
                m('irc_helpers').message(irc, channel, '[lua error] %s' % ', '.join(output))
    elif command == 'luatest':
        module_name = args[0]
        source = ' '.join(args[1:])
        l = interpreter.LuaModule()
        l.run(source)
        interpreter.lua_modules[module_name] = l
    elif command == 'editlua':
        m('irc_helpers').message(irc, origin.nick, web.generate_url(origin))

    interpreter.handle_message(irc, channel, origin, command, args)
