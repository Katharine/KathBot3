from irc import Network

networks = {
    'ajaxlife': Network(
        server='irc.ajaxlife.net',
        port=6667,
        nicks=('KathBot3',),
        realname="Katharine's third bot!",
        ident='kathbot3',
        primary_channel='#anything',
        name='ajaxlife'
    ),
}