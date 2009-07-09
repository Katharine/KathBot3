import datetime

def init():
    add_hook('privmsg', privmsg)

def addquote(nick, quote):
    m('datastore').execute("INSERT INTO quotes (quote, nick) VALUES (?, ?)", quote, nick)

def getquote(number=None, search=None):
    query = "SELECT id, quote, nick, added FROM quotes %s ORDER BY %s LIMIT ?,1"
    args = []
    if number is not None:
        limit = number - 1
        order = 'id'
    else:
        limit = 0
        order = 'RANDOM()'
    if search is not None:
        restriction = 'WHERE quote LIKE ?'
        args.append('%%%s%%' % search)
    else:
        restriction = ''
    
    args.append(limit)
    results = m('datastore').query(query % (restriction, order),  *args)
    logger.debug(results)
    if len(results) == 0:
        return None
    else:
        return Quote(number=results[0][0], quote=results[0][1], nick=results[0][2], added=results[0][3])

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    
    if command == 'addquote':
        nick = origin.nick
        nick = m('security').get_canonical_nick(nick)
        addquote(origin.nick, ' '.join(args).replace("\\n", "\n"))
        irc_helpers.message(irc, target, "Added quote from %s." % nick)
    elif command == 'quote':
        number = None
        search = None
        if len(args) > 0:
            try:
                number = int(args[0])
                if len(args) > 1:
                    search = ' '.join(args[1:])
            except ValueError:
                search = ' '.join(args)
        
        quote = getquote(search=search, number=number)
        if quote is None:
            irc_helpers.message(irc, target, "No quotes found.")
        else:
            irc_helpers.message(irc, target, "~B[Quote]~B ~UQuote #%s~U" % quote.number)
            lines = quote.quote.split("\n")
            for line in lines:
                irc_helpers.message(irc, target, "~B[Quote]~B %s" % line)
                
            irc_helpers.message(irc, target, "~B[Quote]~B Added at %s by %s." % (quote.added.strftime('%I:%M%P on %A, %e %B, %Y').replace('  ',' '), quote.nick))

class Quote(object):
    nick = ''
    quote = ''
    added = ''
    number = 0
    
    def __init__(self, nick='', quote='', added='', number=0):
        self.nick = nick
        self.quote = quote
        self.added = datetime.datetime.strptime(added, '%Y-%m-%d %H:%M:%S')
        self.number = number