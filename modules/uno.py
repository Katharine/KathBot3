import random

class UnoError(Exception): pass

class UnoCard(object):
    colour = ''
    number = ''
    
    def __init__(self, colour='', number=''):
        self.colour = colour
        self.number = str(number)

class UnoGame(object):
    discard_pile = []
    draw_pile = []
    players = []
    playing = False
    current_player = None
    current_index = None
    rotation = 1
    
    def __init__(self):
        self.generate_initial_pile()
    
    def generate_initial_pile(self):
        self.draw_pile = []
        colours = ('red', 'green', 'blue', 'yellow')
        numbers = (1, 2, 3, 4, 5, 6, 7, 8, 9, 'skip', 'draw 2', 'reverse')
        for colour in colours:
            for number in numbers:
                self.draw_pile.append(UnoCard(colour=colour, number=number))
                self.draw_pile.append(UnoCard(colour=colour, number=number))
            self.draw_pile.append(UnoCard(colour=colour, number=0))
        
        for i in range(0, 4):
            self.draw_pile.append(UnoCard(colour='wild'))
            self.draw_pile.append(UnoCard(colour='wild', number='draw four'))
    
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
        if len(self.draw_pile) == 0:
            self.move_discard_to_draw_pile()
    
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