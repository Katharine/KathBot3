import random

UNO_CARDS = (
    'red 0', 'red 1', 'red 1', 'red 2', 'red 2', 'red 3', 'red 3', 'red 4', 'red 4', 'red 5', 'red 5',
    'red 6', 'red 6', 'red 7', 'red 7', 'red 8', 'red 8', 'red 9', 'red 9', 'red skip', 'red skip',
    'red draw 2', 'red draw 2', 'red reverse', 'red reverse',

    'green 0', 'green 1', 'green 1', 'green 2', 'green 2', 'green 3', 'green 3', 'green 4', 'green 4', 'green 5', 'green 5',
    'green 6', 'green 6', 'green 7', 'green 7', 'green 8', 'green 8', 'green 9', 'green 9', 'green skip', 'green skip',
    'green draw 2', 'green draw 2', 'green reverse', 'green reverse',
    
    'blue 0', 'blue 1', 'blue 1', 'blue 2', 'blue 2', 'blue 3', 'blue 3', 'blue 4', 'blue 4', 'blue 5', 'blue 5',
    'blue 6', 'blue 6', 'blue 7', 'blue 7', 'blue 8', 'blue 8', 'blue 9', 'blue 9', 'blue skip', 'blue skip',
    'blue draw 2', 'blue draw 2', 'blue reverse', 'blue reverse',
    
    'yellow 0', 'yellow 1', 'yellow 1', 'yellow 2', 'yellow 2', 'yellow 3', 'yellow 3', 'yellow 4', 'yellow 4', 'yellow 5', 'yellow 5',
    'yellow 6', 'yellow 6', 'yellow 7', 'yellow 7', 'yellow 8', 'yellow 8', 'yellow 9', 'yellow 9', 'yellow skip', 'yellow skip',
    'yellow draw 2', 'yellow draw 2', 'yellow reverse', 'yellow reverse',
)    

class UnoError(Exception): pass

class UnoGame(object):
    discard_pile = []
    draw_pile = []
    players = []
    playing = False
    current_player = None
    current_index = None
    rotation = 1
    
    def __init__(self):
        self.draw_pile = list(UNO_CARDS)
    
    def discard_top(self):
        if len(self.discard_pile):
            return self.discard_pile[0]
        else:
            return None
    
    def add_player(self, nick):
        if self.is_playing(nick):
            raise UnoError, "%s is already playing" % nick
        
        if len(self.players) >= 12:
            raise UnoError, "This game is already full."
            
        if self.playing and len(self.draw_pile) < 7:
            raise UnoError, "There aren't enough cards on the draw pile to join."
        
        player = UnoPlayer(nick)
        self.players.append(player)
        if self.playing:
            self.deal_cards(player=player)
        
        return True
    
    def is_playing(self, nick):
        for player in self.players:
            if player.nick == nick:
                return True
        return False
    
    def start_game(self):
        if self.playing:
            raise UnoError, "The game is already in progress."
        
        if self.players < 2:
            raise UnoError, "You need at least two players to start the game."
        
        self.shuffle_draw_pile()
        self.deal_cards()
        self.discard_pile = [self.draw_pile.pop()] # Move the top of the draw pile to the discard pile.
        self.playing = True
        self.current_index = random.randint(0, len(self.players) - 1)
        self.current_player = self.players[self.current_index]
    
    def player_draw(self):
        if self.players[self.turn].drawn:
            raise UnoError, "You can only draw once each turn."
        
        if len(self.draw_pile) == 0:
            raise UnoError, "You can't draw, because there are no cards left!"
        
        drawn = self.draw_pile.pop()
        self.current_player.drawn = True
        self.current_player.hand.append(drawn)
        self.current_player.permitted = drawn
    
    def shuffle_draw_pile(self):
        random.shuffle(self.draw_pile)
    
    def deal_cards(self, player=None):
        if nick is None:
            for player in self.players:
                self.deal_cards(player=player)
            return
        
        for i in range(0, 7):
            player.hand.append(self.draw_pile.pop())
            if len(self.draw_pile) == 0:
                self.move_discard_to_draw_pile()
    
    def move_discard_to_draw_pile(self):
        self.draw_pile.extend(self.discard_pile)
        self.shuffle_draw_pile()
        discard_pile = [self.draw_pile.pop()]
    

class UnoPlayer(object):
    hand = []
    permitted = '*'
    drawn = False
    nick = ''
    
    def __init__(self, nick):
        self.nick = nick