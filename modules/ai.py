from __future__ import with_statement
import threading
import pickle
import random

verbs = set()
index = {}

activity_lock = threading.Lock()

def init():
    add_hook('privmsg', privmsg)
    add_hook('message', message)
    load_caches()

def shutdown():
    save_caches()

def message(irc, channel, origin, command, args):
    if command == 'aistats':
        longest_word = ''
        most_popular = ''
        most_popular_uses = 0
        for word in index:
            if len(word) > len(longest_word):
                longest_word = word
            if len(index[word]) > most_popular_uses:
                most_popular = word
                most_popular_uses = len(index[word])
        
        m('irc_helpers').message(irc, channel, "I know ~B%i~B words, of which ~B%i~B are verbs." % (len(index), len(verbs)))
        m('irc_helpers').message(irc, channel, "The longest word is ~B%s~B. The most popular word is ~B%s~B (which has been used ~B%i~B times)." % (longest_word, most_popular, most_popular_uses))

def privmsg(irc, origin, args):
    channel = args[0]
    message = args[1]
    if message[0] in ('!', '@', '.', '&') or message.startswith('KB3'):
        return
    if message.startswith('\x01ACTION') and message.endswith('\x01'):
        message = "/me %s" % message[8:-1]
    
    words = message.split(' ')
    if words[0] == '/me':
        words.pop(0)
        # Should we check for ending in 's'?
        verbs.add(words[0])
    
    line = []
    for word in words:
        word = word.strip('.,;:"/?\'()!<>').lower()
        line.append(word)
    line = ' '.join(line)
    #if random.randint(0,4) == 1 or irc.nick.lower() in line:
    #respond(irc, channel, line)
    save_line(line)

def respond(irc, channel, line):
    logger.info("Attempting a response.")
    with activity_lock:
        response = ''
        words = line.split(' ')
        last_word = ''
        for i in range(len(words) - 1):
            word = words[i]
            if word not in index:
                continue
            second_word = words[i + 1]
            if second_word not in index:
                continue
            if word == irc.nick.lower() or second_word == irc.nick.lower():
                continue
            # Woo, two words we know! Can we put them together?
            logger.info("We know '%s' and '%s'" % (word, second_word))
            options = []
            for a in index[word]:
                for b in index[second_word]:
                    if b > a and b - a < 200: # Arbitrary, but must be less than 500.
                        logger.info("Found nearby positions %i - %i" % (a, b))
                        options.append((a, b))
            random.shuffle(options)
            with open('data/ai/memory', 'r') as memory:
                for option in options:
                    a = option[0]
                    b = option[1]
                    memory.seek(a)
                    content = memory.read(b - a) + second_word + ' '
                    logger.info("Read %s." % content)
                    if '\n' in content:
                        logger.info("Invalid entry - newline!")
                        continue
                    if last_word == word:
                        response = response[len(word)+1:]
                    response += content
                    last_word = second_word
                    logger.info("Added %s to the response!" % content)
                    break
    if response:
        first_word = response.split(' ')[0]
        if first_word in verbs:
            response = '/me ' + response
        m('irc_helpers').message(irc, channel, response)
    else:
        logger.info("Response failed. :(")
                

def save_line(line):
    with activity_lock:
        with open('data/ai/memory', 'a+') as memory:
            memory.seek(0, 2)
            start_pos = int(memory.tell())
            memory.write("%s\n" % line)
            words = line.split(' ')
            pos = start_pos
            for word in words:
                if not word in index:
                    index[word] = []
                index[word].append(pos)
                pos += len(word) + 1

def load_caches():
    with activity_lock:
        logger.info("Loading caches...")
        try:
            with open('data/ai/verbs', 'r') as verbf:
                while True:
                    line = verbf.readline().strip()
                    if not line:
                        break
                    verbs.add(line)
        except IOError:
            logger.warn("Failed to load verb cache.")
            pass
        
        try:
            with open('data/ai/index', 'rb') as indexf:
                global index
                index = pickle.load(indexf)
        except IOError:
            logger.warn("Failed to load memory.")

def save_caches():
    with activity_lock:
        logger.info("Saving cache.")
        with open('data/ai/verbs', 'w') as verbf:
            verbf.write('\n'.join(verbs))
        
        with open('data/ai/index', 'wb') as indexf:
            pickle.dump(index, indexf, pickle.HIGHEST_PROTOCOL)