from irc import Network

networks = {
    'ajaxlife': Network(
        server='irc.ajaxlife.net',
        port=6667,
        nicks=('KathBot3', 'KittyBot3',),
        realname="Katharine's third bot!",
        ident='kathbot3',
        primary_channel='#kathbot3',
        name='ajaxlife'
    ),
    'darknet': Network(
        server='irc.chilkotardis.com',
        nicks=('KathBot3',),
        realname="Kitty's bot",
        ident="kathbot3",
        primary_channel="#kathbot3",
        name="darknet"
    ),
}