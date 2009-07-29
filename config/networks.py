from irc import Network

networks = {
    'example': Network(
        server='irc.example.com',
        port=6667,
        nicks=('KathBot3', 'KittyBot3',),
        realname="Katharine's third bot!",
        ident='kathbot3',
        primary_channel='#kathbot3',
        name='example' # Must match the key. I think.
    ),
}