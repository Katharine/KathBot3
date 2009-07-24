# encoding=utf-8
import datetime

def init():
    add_hook('message', message)
    m('webserver').add_handler('GET', quotes_page)

def shutdown():
    m('webserver').remove_handlers()

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
    if len(results) == 0:
        return None
    else:
        return Quote(number=results[0][0], quote=results[0][1], nick=results[0][2], added=results[0][3])

def message(irc, channel, origin, command, args):
    irc_helpers = m('irc_helpers')
    if command == 'addquote':
        nick = origin.nick
        nick = m('security').get_canonical_nick(nick)
        addquote(origin.nick, ' '.join(args).replace("\\n", "\n"))
        irc_helpers.message(irc, channel, "Added quote from %s." % nick)
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
            irc_helpers.message(irc, channel, "No quotes found.")
        else:
            irc_helpers.message(irc, channel, "~B[Quote]~B ~UQuote #%s~U" % quote.number)
            lines = quote.quote.split("\n")
            for line in lines:
                irc_helpers.message(irc, channel, "~B[Quote]~B %s" % line)
                
            irc_helpers.message(irc, channel, "~B[Quote]~B Added %s by %s." % (quote.format_added(), quote.nick))

def quotes_page(request):
    logger.info("Returning main quote page.")
    parts = request.path[1:].split('/')
    if len(parts) == 1:
        output = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
    <head>
        <title>KathBot3 quotes!</title>
        <script src="http://ajax.googleapis.com/ajax/libs/prototype/1.6.0.3/prototype.js" type="text/javascript"></script>
        <script src="/static/quotes/quotes.js" type="text/javascript"></script>
        <link href="/static/quotes/quotes.css" type="text/css" rel="stylesheet" />
    </head>
    <body>
        <h1>Quotes!</h1>
        <div id="quotes">"""
        quotes = m('datastore').query("SELECT id, nick, added FROM quotes")
        for quote in quotes:
            quote = Quote(number=quote[0], nick=quote[1], added=quote[2])
            output += u"""
            <div class="quote">
                <div class="quote-header">Quote #%s – added by %s %s</div>
                <div class="quote-content" id="content-%s" style="display: none;"></div>
            </div>""" % (quote.number, quote.nick, quote.format_added(), quote.number)
        
        output += """
        </div>
    </body>
</html>
"""
        return output
    else:
        return '<div class="quote">%s</div>' % getquote(number=int(parts[1])).quote.replace("\n", "<br />")
    
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
    
    def format_added(self):
        return self.added.strftime('at %l:%M%P on %A, %e %B, %Y').replace('  ',' ')