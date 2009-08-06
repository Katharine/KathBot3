from __future__ import with_statement
import threading
import pickle
import random
from array import array

COMMON_THRESHOLD = 0.008 # See if we can make it work this out itself.

verbs = set()
index = {}
total_words = 0

activity_lock = threading.RLock()

def init():
    add_hook('privmsg', privmsg)
    add_hook('message', message)
    load_caches()
    try:
        m('cron').add_cron(600, save_caches)
    except ModuleNotLoaded:
        logger.warn("Load the cron module for periodic cache saves.")

def shutdown():
    save_caches()

def message(irc, channel, origin, command, args):
    if command == 'aistats':
        longest_word = ''
        most_popular = ''
        most_popular_uses = 0
        very_common = []
        for word in index:
            if len(word) > len(longest_word):
                longest_word = word
            uses = len(index[word])
            if uses > most_popular_uses:
                most_popular = word
                most_popular_uses = uses
            if uses > total_words * COMMON_THRESHOLD:
                very_common.append(word)
        
        most_popular_verb = ''
        verb_uses = 0
        for verb in verbs:
            try:
                if len(index[verb]) > verb_uses:
                    most_popular_verb = verb
                    verb_uses = len(index[verb])
            except KeyError:
                continue
        
        learning = m('datastore').channels[(irc, channel)].get('ai_learn', False)
        response_frequency = int(m('datastore').channels[(irc, channel)].get('ai_respond', 0))
        m('irc_helpers').message(irc, channel, "Learning: %s. Response frequency: %i%%" % ('yes' if learning else 'no', response_frequency))
        m('irc_helpers').message(irc, channel, "I know ~B%i~B unique words, of which ~B%i~B are verbs. I have heard ~B%s~B words in total." % (len(index), len(verbs), total_words))
        m('irc_helpers').message(irc, channel, "The longest word is ~B%s~B. The most popular word is ~B%s~B (which has been used ~B%i~B times)." % (longest_word, most_popular, most_popular_uses))
        m('irc_helpers').message(irc, channel, "The most popular verb is ~B%s~B, and it's been used ~B%i~B times." % (most_popular_verb, verb_uses))
        m('irc_helpers').message(irc, channel, "I know ~B%i~B very common words: %s" % (len(very_common), ', '.join(very_common)))
    elif command == 'ailearn':
        enabled = (args[0].lower() == 'on') if len(args) else False
        m('datastore').channels[(irc, channel)]['ai_learn'] = enabled
        m('irc_helpers').message(irc, channel, "Learning %s." % 'enabled' if enabled else 'disabled')
    elif command == 'airespond':
        try:
            frequency = int(args[0])
            if frequency < 0 or frequency > 100:
                raise ValueError
        except:
            m('irc_helpers').message(irc, channel, "Please specify a frequency between 0 and 100.")
            return
        m('datastore').channels[(irc, channel)]['ai_respond'] = frequency
        m('irc_helpers').message(irc, channel, "Response frequency set to %i%%." % frequency)

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
        verbs.add(words[0].strip('.,;:"/?\'()!<>'))
    
    line = []
    for word in words:
        word = word.strip('.,;:"/?\'()!<>').lower()
        if word != '':
            line.append(word)
    line = ' '.join(line)
    response_frequency = int(m('datastore').channels[(irc, channel)].get('ai_respond', 0))
    if response_frequency > 0 and (random.randint(0, 100) < response_frequency or irc.nick.lower() in line):
        respond(irc, channel, line)
    if m('datastore').channels[(irc, channel)].get('ai_learn', False):
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
            if len(index[word]) > total_words * COMMON_THRESHOLD or len(index[second_word]) > total_words * COMMON_THRESHOLD:
                logger.info("Words too common; ignoring.")
                continue
            # Woo, two words we know! Can we put them together?
            logger.debug("We know '%s' and '%s'" % (word, second_word))
            options = []
            for a in index[word]:
                for b in index[second_word]:
                    if b > a and b - a < 100: # Arbitrary, but must be less than 500.
                        logger.debug("Found nearby positions %i - %i" % (a, b))
                        options.append((a, b))
            random.shuffle(options)
            with open('data/ai/memory', 'r') as memory:
                for option in options:
                    a = option[0]
                    b = option[1]
                    memory.seek(a)
                    content = memory.read(b - a) + second_word + ' '
                    logger.debug("Read %s." % content)
                    if '\n' in content:
                        logger.debug("Invalid entry - newline!")
                        continue
                    if last_word == word:
                        content = content[len(word)+1:]
                    response += content
                    last_word = second_word
                    logger.info("Added %s to the response!" % content)
                    break
    if response and response.strip() != line.strip():
        first_word = response.split(' ')[0]
        if first_word in verbs:
            response = '/me ' + response
        m('irc_helpers').message(irc, channel, response)
    else:
        logger.info("Response failed. :(")
                

def save_line(line):
    with activity_lock:
        with open('data/ai/memory', 'a+') as memory:
            global total_words
            memory.seek(0, 2)
            start_pos = int(memory.tell())
            memory.write("%s\n" % line)
            words = line.split(' ')
            pos = start_pos
            for word in words:
                if not word in index:
                    index[word] = array('I')
                index[word].append(pos)
                pos += len(word) + 1
            total_words += len(words)

def load_caches():
    with activity_lock:
        logger.info("Loading caches...")
        try:
            with open('data/ai/verbs', 'r') as verbf:
                while True:
                    line = verbf.readline()
                    if line == '':
                        break
                    verbs.add(line.strip())
        except IOError:
            logger.warn("Failed to load verb cache.")
            pass
        
        try:
            with open('data/ai/index', 'rb') as indexf:
                global index
                index = pickle.load(indexf)
            count_words()
        except IOError:
            logger.warn("Failed to load memory.")

def save_caches():
    with activity_lock:
        logger.info("Saving cache.")
        with open('data/ai/verbs', 'w') as verbf:
            verbf.write('\n'.join(verbs))
        
        with open('data/ai/index', 'wb') as indexf:
            pickle.dump(index, indexf, pickle.HIGHEST_PROTOCOL)

def count_words():
    with activity_lock:
        global total_words
        total_words = 0
        for word in index:
            total_words += len(index[word])