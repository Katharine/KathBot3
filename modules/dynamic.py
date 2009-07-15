# encoding=utf-8
# Warning: this is very ugly.
from __future__ import division
import random
import timelib # http://pypi.python.org/pypi/timelib/
import datetime
import os
import math
import textwrap

PARENT_TAGS = ('if', 'else', 'choose', 'choice', 'c', 'set', 'try', 'length', 'indefinite', 'capitalise', 'math', 'repeat', 'while', 'get')

class ParseError(Exception): pass

class ParseNode(object):
    name = ''
    closing = False
    children = None
    attribute = ''
    parent = None
    
    def __init__(self, tag=None, name=None):
        self.children = []
        if name is not None:
            self.name = name
        elif tag is not None:
            self.parse_tag(tag)
       
    def parse_tag(self, tag):
        tag = tag[1:-1].split(' ', 1)
        self.name = tag[0].lower()
        if self.name[0] == '/':
            self.name = self.name[1:]
            if not self.name in PARENT_TAGS:
                raise ParseError, "Unexpected closing tag [/%s], which cannot have children." % self.name
            self.closing = True
        if len(tag) > 1 and tag[1] is not None:
            self.attribute = tag[1]
    
    def add_child(self, child):
        if isinstance(child, StringNode) and child.attribute == '':
            return
        if isinstance(child, ParseNode):
            child.parent = self
        self.children.append(child)

class StringNode(ParseNode):
    def __init__(self, string):
        self.attribute = string

class TagNode(ParseNode): pass

def stringify(string):
    if isinstance(string, basestring):
        return string
    else:
        return str(string)

def parse_tree(line):
    parts = []
    current_part = ''
    in_token = False
    
    root = ParseNode(name='root')
    current_node = root
    
    for char in line:
        if char == '[':
            if not in_token:
                current_node.add_child(StringNode(current_part))
                current_part = ''
                in_token = 1
            else:
                in_token += 1
            current_part += '['
        elif char == ']' and in_token:
            current_part += ']'
            in_token -= 1
            if in_token > 0:
                continue
            in_token = False
            node = ParseNode(current_part)
            if node.name in PARENT_TAGS:
                if node.closing:
                    if node.name == current_node.name:
                        current_node = current_node.parent
                    else:
                        raise ParseError, "Mismatched closing [/%s]; expecting [/%s]." % (node.name, current_node.name)
                else:
                    current_node.add_child(node)
                    current_node = node
            else:
                current_node.add_child(node)
            current_part = ''
        else:
            current_part += char
    
    current_node.add_child(StringNode(current_part))
    return root

def parseline(irc, origin, args, channel, line):
    tree = parse_tree(line)
    return dotree(tree, irc, origin, args, channel)

def treelevel(node, irc, origin, args, channel, variables):
    value = ''
    for child in node.children:
        value += stringify(dotree(child, irc, origin, args, channel, variables))
    return value

def dotree(node, irc, origin, args, channel, variables=None):
    if isinstance(node, StringNode):
        return node.attribute
    
    if variables is None:
        variables = {
            'nick': origin.nick,
            'hostname': origin.hostname,
            'args': ' '.join(args),
            'argcount': len(args),
            '__builtins__': None, # Disable the builtin functions.
        }
        try:
            chantrack = m('chantrack')
            variables['usercount'] = len(chantrack.network(irc)[channel].users)
            variables['topic'] = chantrack.network(irc)[channel].topic
        except ModuleNotLoaded:
            pass
        for i in range(0, len(args)):
            variables['arg%s' % i] = args[i]

    if node.name in ('root', 'else', 'choice', 'c'):
        value = ''
        for child in node.children:
            value += stringify(dotree(child, irc, origin, args, channel, variables))
        return value
    
    
    
    # Do something useful with this node.
    if node.name in variables:
        return variables[node.name]
    elif node.name == 'if':
        try:
            test = eval(node.attribute, variables)
        except NameError:
            test = False
        if test:
            value = ''
            for child in node.children:
                if child.name != 'else':
                    value += stringify(dotree(child, irc, origin, args, channel, variables))
            return value
        else:
            value = ''
            for child in node.children:
                if child.name == 'else':
                    value += stringify(dotree(child, irc, origin, args, channel, variables))
            return value
    elif node.name == 'repeat':
        try:
            if node.attribute in variables:
                times = int(variables[node.attribute])
                
            else:
                times = int(node.attribute)
        except Exception, message:
            raise ParseError, "[random repeats] requires repeats to be an integer greater than zero. (%s)" % message
        if times > 25:
            raise ParseError, "Excessively large numbers of repeats are forbidden."
        variables['counter'] = 0
        value = ''
        while variables['counter'] < times:
            variables['counter'] += 1
            value += treelevel(node, irc, origin, args, channel, variables)
        return value
    elif node.name == 'while':
        try:
            counter = 0
            value = ''
            while eval(node.attribute, variables):
                value += treelevel(node, irc, origin, args, channel, variables)
                counter += 1
                if counter >= 50:
                    value += '~B[excessive looping; abandoning]~B'
                    break
            return value
        except (NameError, SyntaxError):
            return "~B[bad while loop]~B"    
    elif node.name == 'random':
        r = node.attribute.split(':')
        try:
            return stringify(random.randint(int(r[0]), int(r[1])))
        except:
            raise ParseError, "[random a:b] requires two integers a and b (a <= result <= b)"
    elif node.name == 'countdown':
        return timediff(timelib.strtodatetime(node.attribute) - datetime.datetime.utcnow())
    elif node.name == 'countup':
        return timediff(datetime.datetime.utcnow() - timelib.strtodatetime(node.attribute))
    elif node.name == 'choose':
        real_children = []
        for child in node.children:
            if child.name != '|':
                real_children.append(child)
        return dotree(random.choice(real_children), irc, origin, args, channel, variables)
    elif node.name == 'noun':
        word = word_from_file('data/nouns')
        if node.attribute == 'plural':
            vowels = 'aeiou'
            if word[-1] == 'y' and word[-2] not in vowels:
                return "%sies" % word[0:-1]
            elif word[-1] == 's':
                return "%ses" % word
            else:
                return "%ss" % word
        else:
            return word
    elif node.name == 'verb':
        verb = word_from_file('data/verbs')
        tense = node.attribute or 'root'
        if verb.find('|') != -1:
            # Figure out what we're going to do about this later...
            pass
        else:
            if tense == 'root':
                return verb
            elif tense == 'first' or tense == 'second':
                return verb
            elif tense == 'third':
                if verb[-1] in 'szx' or verb[-2:] in ('ch', 'sh'):
                    return '%ses' % verb
                elif verb[-1] == 'y' and verb[-2] not in 'aeiou':
                    return '%sies' % verb[:-1]
                else:
                    return '%ss' % verb
            else:
                if verb[-1] not in 'aeiouy' and verb[-2] in 'aeiou':
                    # This check sucks.
                    if (len(verb) == 3 or (len(verb) == 4 and verb[-1] == 'p')):
                        verb += verb[-1]
                
                if tense == 'pastpart' or tense == 'past':
                    if verb[-1] == 'e':
                        return '%sd' % verb
                    elif verb[-1] == 'y' and verb[-2] not in 'aeiou':
                        return '%sied' % verb[:-1]
                    else:
                        return '%sed' % verb
                elif tense == 'presentpart' or tense == 'gerund':
                    if verb[-1] == 'e':
                        return '%sing' % verb[:-1]
                    else:
                        return '%sing' % verb
                else:
                    return '~B[unknown tense "%s"]~B' % tense
    elif node.name == 'adjective':
        return word_from_file('data/adjectives')
    elif node.name == 'adverb':
        return word_from_file('data/adverbs')
    elif node.name == 'interjection':
        return word_from_file('data/interjections')
    elif node.name == '|':
        return ''
    elif node.name == 'rnick':
        try:
            return random.choice(m('chantrack').network(irc)[channel].users.values())
        except ModuleNotLoaded:
            return origin.nick
    elif node.name == 'try':
        if node.attribute in variables:
            return variables[node.attribute]
        else:
            return treelevel(node, irc, origin, args, channel, variables)
    elif node.name == 'set':
        variables[node.attribute] = treelevel(node, irc, origin, args, channel, variables)
        try:
            intvar = int(variables[node.attribute])
            floatvar = float(variables[node.attribute])
            if abs(intvar - floatvar) < 0.00001:
                variables[node.attribute] = intvar
            else:
                variables[node.attribute] = floatvar
        except:
            pass
        return ''
    elif node.name == 'get':
        name = treelevel(node, irc, origin, args, channel, variables)
        if name in variables:
            return variables[name]
        else:
            return 'None'
    elif node.name == 'length':
        return stringify(len(treelevel(node, irc, origin, args, channel, variables)))
    elif node.name == 'capitalise':
        contents = treelevel(node, irc, origin, args, channel, variables)
        if node.attribute == '' or node.attribute == 'first':
            if len(contents) > 0:
                contents = contents[0].upper() + contents[1:]
        elif node.attribute == 'words':
            words = contents.split(' ')
            contents = ''
            for word in words:
                contents += word[0].upper() + word[1:] + ' '
            return contents.strip()
        elif node.attribute == 'all':
            return contents.upper()
        else:
            return contents
        return contents
    elif node.name == 'indefinite':
        phrase = treelevel(node, irc, origin, args, channel, variables)
        if phrase[0] in 'aeiou':
            return "an %s" % phrase
        else:
            return "a %s" % phrase
    elif node.name == 'math':
        expression = treelevel(node, irc, origin, args, channel, variables)
        try:
            math_functions = {
                'pow': pow,
                'ceil': math.ceil,
                'floor': math.floor,
                'round': round,
                'sin': lambda theta: math.sin(theta * (math.pi/180)),
                'cos': lambda theta: math.cos(theta * (math.pi/180)),
                'tan': lambda theta: math.tan(theta * (math.pi/180)),
                'pi': math.pi,
                'sqrt': math.sqrt,
                '__builtins__': None,
            }
            result = eval(expression, math_functions, variables)
            if abs(result) < 0.000000001 and result != 0:
                result = 0.0
            return stringify(result)
        except:
            return '~B[unsolvable sums]~B'
    else:
        return "~B[unknown tag '%s']~B" % node.name

def format_source(node):
    if isinstance(node, StringNode):
        return node.attribute
    
    depth = 1
    temp = node
    while temp.parent is not None:
        depth += 1
        temp = temp.parent
    
    if node.attribute != '':
        attribute = ' ' + node.attribute
    else:
        attribute = ''
    if node.name != 'root':
        value = '~B\x03%s[%s%s]\x03~B' % (depth, node.name, attribute)
    else:
        value = ''
    if node.children:
        for child in node.children:
            value += format_source(child)
        if node.name != 'root':
            value += '~B\x03%s[/%s]\x03~B' % (depth, node.name)
        return value
    else:
        return value

def init():
    add_hook('privmsg', privmsg)

def find_command(command):
    result = m('datastore').query("SELECT source FROM dynamic WHERE command = ?", command)
    if len(result) == 0:
        return None
    return result[0][0]

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if command in ('add', 'delete', 'source', 'append'):
        if not m('security').check_action_permissible(origin, "%s" % command):
            irc_helpers.message(irc, target, "You don't have permission to do this.")
            return
        
        if command == 'add':
            if len(args) < 2:
                irc_helpers.message(irc, target, "You must provide a command name and something for it to do.")
            else:
                c = args[0]
                source = ' '.join(args[1:])
                m('datastore').execute("REPLACE INTO dynamic (command, source) VALUES (?, ?)", c, source)
                irc_helpers.message(irc, target, "Added command ~B%s~B." % args[0])
        elif command == 'append':
            if len(args) < 2:
                irc_helpers.message(irc, target, "You must provide a command name and something for it to do.")
            else:
                c = args[0]
                original = find_command(c)
                if original is None:
                    irc_helpers.message(irc, target, "That command doesn't exist yet.")
                    return
                source = original + ' '.join(args[1:])
                m('datastore').execute("UPDATE dynamic SET source = ? WHERE command = ?", source, c)
                irc_helpers.message(irc, target, "Updated command ~B%s~B." % args[0])
        elif command == 'delete':
            if len(args) != 1:
                irc_helpers.message(irc, target, "You must specify what you want to delete.")
            else:
                m('datastore').execute("DELETE FROM dynamic WHERE command = ?", args[0])
                irc_helpers.message(irc, target, "Deleted command ~B%s~B." % args[0])
        elif command == 'source':
            if len(args) != 1:
                irc_helpers.message(irc, target, "You must specify what you want the source for.")
            else:
                source = find_command(args[0])
                if source is not None:
                    try:
                        source = format_source(parse_tree(source))
                    except ParseError, message:
                        irc_helpers.message(irc, target, "~BParse error (%s); highlighting disabled.~B" % message)
                    lines = textwrap.wrap(source, 480)
                    for line in lines:
                        irc_helpers.message(irc, target, '~U%s~U: %s' % (args[0], line))
                else:
                    irc_helpers.message(irc, target, "The command ~B%s~B does not exist." % args[0])
    else:
        source = find_command(command)
        if source is not None:
            try:
                lines = parseline(irc, origin, args, target, source).split(r"\n")
            except ParseError, message:
                lines = [message]
            for line in lines:
                irc_helpers.message(irc, target, line)
                
def timediff(delta):
    seconds = delta.days * 86400 + delta.seconds
    if seconds < 0:
        return 'in the past'
    weeks = seconds // (86400 * 7)
    seconds -= weeks * 86400 * 7
    days = seconds // 86400
    seconds -= days * 86400
    hours = seconds // 3600
    seconds -= hours * 3600
    minutes = seconds // 60
    seconds = seconds % 60
    
    parts = []
    if weeks > 0:
        parts.append('%s week%s' % (weeks, 's' if weeks > 1 else ''))
    if days > 0:
        parts.append('%s day%s' % (days, 's' if days > 1 else ''))
    if hours > 0:
        parts.append('%s hour%s' % (hours, 's' if hours > 1 else ''))
    if minutes > 0:
        parts.append('%s minute%s' % (minutes, 's' if minutes > 1 else ''))
    if seconds > 0:
        parts.append('%s second%s' % (seconds, 's' if seconds > 1 else ''))
    
    if len(parts) == 0:
        return 'no time'
    if len(parts) == 1:
        return parts[0]
    string = ', '.join(parts[0:-1])
    string = '%s and %s' % (string, parts[-1])
    return string

def word_from_file(path):
    size = os.stat(path).st_size
    pos = random.randint(0, size - 1)
    f = open(path)
    f.seek(pos)
    while f.tell() != 0 and f.read(1) != "\n": pass
    word = ''
    try:
        while True:
            char = f.read(1)
            if char == "\n":
                break
            word += char
    except EOFError:
        pass
    return word.strip()
