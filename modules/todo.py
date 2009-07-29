COMMANDS = frozenset(('todo', 'done', 'whattodo',))

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command not in COMMANDS:
        return
    irch = m('irc_helpers')
    uid = m('security').get_user_id(origin)
    if not uid:
        irch.message(irc, channel, "You can't use the todo module unless you are a registered user.")
        return
    if command == 'todo':
        if len(args) == 0:
            todos = m('datastore').query("SELECT todo FROM todo WHERE uid = ?", uid)
            if len(todos) == 0:
                irch.message(irc, channel, "You have nothing to do.", tag='todo')
            else:
                i = 0
                for todo in todos:
                    i += 1
                    todo = todo[0]
                    irch.message(irc, channel, "%i) %s" % (i, todo), tag='todo')
        else:
            todo = ' '.join(args)
            m('datastore').execute("INSERT INTO todo (uid, todo) VALUES (?, ?)", uid, todo)
            irch.message(irc, channel, "Added todo item.", tag='todo')
    elif command == 'whattodo':
        todo = m('datastore').query("SELECT todo FROM todo WHERE uid = ? ORDER BY RANDOM() LIMIT 1", uid)
        if len(todo) == 0:
            irch.message(irc, channel, "I don't know.", tag='todo')
        else:
            irch.message(irc, channel, todo[0][0], tag='todo')
    elif command == 'done':
        if len(args) == 0:
            irch.message(irc, channel, "What have you done?")
        else:
            if args[0].lower() == 'everything':
                m('datastore').query("DELETE FROM todo WHERE uid = ?", uid)
                irch.message(irc, channel, "Cleared your todo list.", tag='todo')
            else:
                try:
                    todo = int(args[0])
                except:
                    irch.message(irc, channel, "Please specify the number from the 'todo' command of the todo to delete.")
                rowid = m('datastore').query("SELECT rowid FROM todo WHERE uid = ? LIMIT ?,1", uid, todo - 1)
                if len(rowid) == 0:
                    irch.message(irc, channel, "Invalid todo #%i" % todo, tag='todo')
                else:
                    m('datastore').execute("DELETE FROM todo WHERE rowid = ?", rowid[0][0])
                    irch.message(irc, channel, "Dropped todo #%i" % todo, tag='todo')