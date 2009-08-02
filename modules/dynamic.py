# encoding=utf-8
# Warning: this is very ugly.
# 30/7/09 - now it's *really* ugly.
from __future__ import division
import random
import timelib # http://pypi.python.org/pypi/timelib/
import datetime
import os
import math
import textwrap

parent_tags = set(('if', 'else', 'choose', 'choice', 'c', '|', 'set', 'try', 'length', 'indefinite', 'indef', 'capitalise', 'math', 'repeat', 'while', 'get', 'func'))
grouping_tags = set(('root', 'else', 'choice', 'c', '|'))
registered_tags = {} # tag => callback

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
            if not self.name in parent_tags:
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

class TagContext(object):
    def __init__(self, irc, origin, args, channel, variables=None):
        self.irc = irc
        self.origin = origin
        self.args = args
        self.channel = channel
        self.variables = variables
        
        if self.variables is None:
            self.create_default_variables()
    
    def create_default_variables(self):
        simple_args = self.args
        args = []
        in_arg = False
        for arg in simple_args:
            if in_arg:
                if arg[-1] == '"':
                    args[-1].append(arg[0:-1])
                    args[-1] = ' '.join(args[-1])
                    in_arg = False
                else:
                    args[-1].append(arg)
            elif arg[0] == '"':
                args.append([arg[1:]])
                in_arg = True
            else:
                args.append(arg)
        self.args = args
        del args
        del simple_args
        self.variables = {
            'nick': self.origin.nick,
            'hostname': self.origin.hostname,
            'argcount': len(self.args),
            'channel': self.channel,
            '__builtins__': None, # Disable the builtin functions.
        }
        if self.channel[0] == '#':
            try:
                chantrack = m('chantrack')
                self.variables['usercount'] = len(chantrack.network(self.irc)[self.channel].users)
                self.variables['topic'] = chantrack.network(self.irc)[self.channel].topic
            except ModuleNotLoaded:
                pass
        else:
            self.variables['usercount'] = 1
            self.variables['topic'] = 'N/A'
        for i in range(0, len(self.args)):
            self.variables['arg%s' % i] = self.args[i]

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
            if node.name in parent_tags:
                if node.closing:
                    if node.name == current_node.name:
                        current_node = current_node.parent
                    elif node.name == 'if' and current_node.name == 'else' and current_node.parent and current_node.parent.name == 'if':
                        current_node = current_node.parent.parent
                    elif current_node.name == '|' and node.name == 'choose':
                        current_node = current_node.parent.parent
                    else:
                        raise ParseError, "Mismatched closing [/%s]; expecting [/%s]." % (node.name, current_node.name)
                else:
                    if node.name == 'choose':
                        hack = ParseNode(name='|')
                        node.add_child(hack)
                        current_node.add_child(node)
                        current_node = hack
                    else:
                        if current_node.name == '|' and node.name == '|':
                            current_node = current_node.parent
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
    context = TagContext(irc, origin, args, channel)
    return dotree(tree, context)

def treelevel(node, context):
    value = ''
    for child in node.children:
        value += stringify(dotree(child, context))
    return value

def get_var(name, context, attribute=''):
    if name in context.variables:
        value = context.variables[name]
        if isinstance(value, ParseNode):
            oldattr = context.variables.get('attr')
            attr = get_var(attribute, context) # Functions can have variables as args.
            if attr is not None:
                context.variables['attr'] = attr
            else:
                context.variables['attr'] = attribute
            output = treelevel(value, context)
            context.variables['attr'] = oldattr
            return output
        else:
            return value
    else:
        return None

def dotree(node, context):
    # Strings are just strings
    if isinstance(node, StringNode):
        return node.attribute
    
    # Grouping nodes do nothing interesting other than recurse.
    if node.name in grouping_tags:
        value = ''
        for child in node.children:
            value += stringify(dotree(child, context))
        return value
    
    # Variable nodes should be returned immediately
    value = get_var(node.name, context, node.attribute)
    if value is not None:
        return value
    
    # If we have a locally defined function for a tag, call that.
    if "tag_%s" % node.name in locals():
        return locals()[node.name](node, context)
    
    # If we have a tag registered by another module, try that.
    if node.name in registered_tags:
        return registered_tags[node.name](node, context)
    
    # Any code beyond this point should be refactored.
    if node.name == 'if':
        try:
            test = eval(node.attribute, context.variables)
        except NameError:
            test = False
        if test:
            value = ''
            for child in node.children:
                if child.name != 'else':
                    value += stringify(dotree(child, context))
            return value
        else:
            value = ''
            for child in node.children:
                if child.name == 'else':
                    value += stringify(dotree(child, context))
            return value
    # include courtesy Selig.
    elif node.name == 'include':
        source = find_command(node.attribute)
        try:
            if source is not None:
                return stringify(dotree(parse_tree(source), context))
        except:
            return ""
        return "~B[Could not include: %s]~B" % node.attribute
    elif node.name == 'import':
        source = find_command(node.attribute)
        if source is not None:
            variables[node.attribute] = parse_tree(source)
            return "";
        return "~B[Could not import: %s]~B" % node.attribute
    elif node.name == 'l':
        return '['
    elif node.name == 'r':
        return ']'
    elif node.name == 'repeat':
        try:
            value = get_var(node.attribute, context)
            if value is not None:
                times = int(value)
            else:
                times = int(node.attribute)
        except Exception, message:
            raise ParseError, "[random repeats] requires repeats to be an integer greater than zero. (%s)" % message
        if times > 25:
            raise ParseError, "Excessively large numbers of repeats are forbidden."
        context.variables['counter'] = 0
        counter = 0
        value = ''
        while counter < times:
            context.variables['counter'] += 1
            counter += 1
            value += treelevel(node, context)
        return value
    elif node.name == 'args':
        try:
            if not node.attribute:
                return ' '.join(context.args)
            else:
                if ':' not in node.attribute:
                    return context.args[int(node.attribute)]
                else:
                    start, finish = node.attribute.split(':')
                    return ' '.join(context.args[int(start):int(finish)])
        except:
            return '~B[bad arg numbers %s]~B' % node.attribute
    elif node.name == 'while':
        try:
            counter = 0
            value = ''
            while eval(node.attribute, context.variables):
                value += treelevel(node, context)
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
            a = get_var(r[0], context)
            b = get_var(r[1], context)
            return stringify(random.randint(int(a or r[0]), int(b or r[1])))
        except:
            raise ParseError, "[random a:b] requires two integers a and b (a <= result <= b)"
    elif node.name == 'countdown':
        return timediff(timelib.strtodatetime(node.attribute) - datetime.datetime.utcnow())
    elif node.name == 'countup':
        return timediff(datetime.datetime.utcnow() - timelib.strtodatetime(node.attribute))
    elif node.name == 'choose':
        # Deal with the old [c]..[/c] format.
        if len(node.children) == 1 and node.children[0].name == '|':
            real_children = node.children[0].children
        else:
            real_children = node.children
        return dotree(random.choice(real_children), context)
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
    elif node.name == 'place':
        return word_from_file('data/places')
    elif node.name == '|':
        return ''
    elif node.name == 'rnick':
        if context.channel[0] != '#':
            return random.choice((context.irc.nick, context.channel))
        else:
            try:
                return random.choice(m('chantrack').network(context.irc)[context.channel].users.values()).nick
            except ModuleNotLoaded:
                return context.origin.nick
    elif node.name == 'try':
        value = get_var(node.attribute, context)
        if value is not None:
            return value
        else:
            return treelevel(node, context)
    elif node.name == 'func':
        context.variables[node.attribute] = node
        return ''
    elif node.name == 'set':
        context.variables[node.attribute] = treelevel(node, context)
        try:
            intvar = int(context.variables[node.attribute])
            floatvar = float(context.variables[node.attribute])
            if abs(intvar - floatvar) < 0.00001:
                context.variables[node.attribute] = intvar
            else:
                context.variables[node.attribute] = floatvar
        except:
            pass
        return ''
    elif node.name == 'get':
        name = treelevel(node, context)
        return stringify(get_var(name, context, node.attribute))
    elif node.name == 'length':
        return stringify(len(treelevel(node, context)))
    elif node.name == 'capitalise':
        contents = treelevel(node, context)
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
    elif node.name == 'indefinite' or node.name == 'indef':
        phrase = treelevel(node, context)
        if phrase[0].lower() in 'aeiou':
            return "an %s" % phrase
        else:
            return "a %s" % phrase
    elif node.name == 'math':
        expression = treelevel(node, context)
        try:
            math_functions = {
                'pow': pow,
                'ceil': math.ceil,
                'floor': math.floor,
                'round': round,
                'sin': lambda theta: math.sin(math.radians(theta)),
                'cos': lambda theta: math.cos(math.radians(theta)),
                'tan': lambda theta: math.tan(math.radians(theta)),
                'asin': lambda x: math.degrees(math.asin(x)),
                'acos': lambda x: math.degrees(math.acos(x)),
                'atan': lambda x: math.degrees(math.atan(x)),
                'log': math.log,
                'ln': lambda a: math.log(a),
                'log10': math.log10,
                'e': math.e,
                'pi': math.pi,
                'sqrt': math.sqrt,
                '__builtins__': None,
            }
            result = eval(expression, math_functions, context.variables)
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
    if node.name != 'root' and (node.name != '|' or node.parent.children[0] is not node):
        value = '~B\x03%s[%s%s]\x03~B' % (depth, node.name, attribute)
    else:
        value = ''
    if node.children:
        first = True
        for child in node.children:
            value += format_source(child)
        if node.name != 'root' and node.name != '|':
            value += '~B\x03%s[/%s]\x03~B' % (depth, node.name)
        return value
    else:
        return value

def init():
    add_hook('message', message)
    try:
        m('webserver').add_handler('GET', weblist)
    except ModuleNotLoaded:
        pass

def find_command(command):
    result = m('datastore').query("SELECT source FROM dynamic WHERE command = ?", command)
    if len(result) == 0:
        return None
    return result[0][0]

def message(irc, channel, origin, command, args):
    irc_helpers = m('irc_helpers')
    if command in ('add', 'delete', 'source', 'append', 'eval'):
        if not m('security').check_action_permissible(origin, "%s" % command):
            return
        
        if command == 'add':
            if len(args) < 2:
                irc_helpers.message(irc, channel, "You must provide a command name and something for it to do.")
            else:
                c = args[0]
                source = ' '.join(args[1:])
                m('datastore').execute("REPLACE INTO dynamic (command, source) VALUES (?, ?)", c, source)
                irc_helpers.message(irc, channel, "Added command ~B%s~B." % args[0])
        elif command == 'append':
            if len(args) < 2:
                irc_helpers.message(irc, channel, "You must provide a command name and something for it to do.")
            else:
                c = args[0]
                original = find_command(c)
                if original is None:
                    irc_helpers.message(irc, channel, "That command doesn't exist yet.")
                    return
                source = original + ' '.join(args[1:])
                m('datastore').execute("UPDATE dynamic SET source = ? WHERE command = ?", source, c)
                irc_helpers.message(irc, channel, "Updated ~B%s~B." % c)
        elif command == 'delete':
            if len(args) != 1:
                irc_helpers.message(irc, channel, "You must specify what you want to delete.")
            else:
                m('datastore').execute("DELETE FROM dynamic WHERE command = ?", args[0])
                irc_helpers.message(irc, channel, "Deleted command ~B%s~B." % args[0])
        elif command == 'source':
            if len(args) != 1:
                irc_helpers.message(irc, channel, "You must specify what you want the source for.")
            else:
                source = find_command(args[0])
                if source is not None:
                    try:
                        source = format_source(parse_tree(source))
                    except ParseError, message:
                        irc_helpers.message(irc, channel, "~BParse error (%s); highlighting disabled.~B" % message)
                    irc_helpers.message(irc, channel, source, tag=args[0])
                else:
                    irc_helpers.message(irc, channel, "The command ~B%s~B does not exist." % args[0])
        elif command == 'eval':
            try:
                irc_helpers.message(irc, channel, parseline(irc, origin, args, channel, ' '.join(args).replace(r'\n', '\n')))
            except ParseError, error:
                irc_helpers.message(irc, channel, "%s" % error)
    else:
        source = find_command(command)
        if source is not None:
            try:
                lines = parseline(irc, origin, args, channel, source).split(r"\n")
            except ParseError, message:
                lines = [message]
            for line in lines:
                irc_helpers.message(irc, channel, line)

def weblist(request):
    content = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
    <head>
        <title>Dynamic command listing</title>
    </head>
    <body>
        <h1>Dynamic commands</h1>
        <ul>
"""
    commands = m('datastore').query("SELECT command FROM dynamic")
    for command in commands:
        content += """
        <li>%s</li>""" % command[0]
    
    content += """
        </ul>
    </body>
</html>"""
    return content

def timediff(delta):
    seconds = delta.days * 86400 + delta.seconds
    if seconds < 0:
        return 'in the past'
    years = seconds // 31557600
    seconds -= years * 31557600
    months = seconds // 2629800
    seconds -= months * 2629800
    weeks = seconds // (86400 * 7)
    seconds -= weeks * 86400 * 7
    days = seconds // 86400
    seconds -= days * 86400
    hours = seconds // 3600
    seconds -= hours * 3600
    minutes = seconds // 60
    seconds = seconds % 60
    
    parts = []
    if years > 0:
        parts.append("%s year%s" % (years, 's' if years > 1 else ''))
    if months > 0:
        parts.append("%s month%s" % (months, 's' if months > 1 else ''))
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
    while f.read(1) != "\n":
        f.seek(-2, os.SEEK_CUR)
    word = ''
    while True:
        char = f.read(1)
        if char == "\n" or char == "":
            break
        word += char
    return word.strip()
