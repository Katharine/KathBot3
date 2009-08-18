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
import inspect

parent_tags = set(('if', 'else', 'choose', 'choice', 'c', '|', 'set', 'try', 'math', 'repeat', 'while', 'get', 'func', 'switch', 'case', 'list', 'append', 'for'))
grouping_tags = set(('root', 'else', 'choice', 'c', '|', 'case'))
barhack_tags = set(('choose', 'switch', 'list', 'append'))
registered_tags = {} # tag => callback
module_registrations = {} # module => list

class ParseError(Exception): pass
class TagAlreadyExists(Exception): pass

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

class TagContext(dict):
    def __init__(self, irc, origin, args, channel, variables=None):
        self.irc = irc
        self.origin = origin
        self.args = args
        self.channel = channel
        self.variables = variables
        
        if self.variables is None:
            self.create_default_variables()
    
    def __getitem__(self, key):
        if key not in self.variables:
            return None
        value = self.variables[key]
        if isinstance(value, ParseNode):
            return typecast(treelevel(value, self))
        return value

    def __setitem__(self, key, value):
        self.variables[key] = value
    
    def __contains__(self, key):
        return key in self.variables
    
    def keys(self):
        return self.variables.keys()
    
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

        self.variables['arg'] = self.args

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
                    elif current_node.name == '|' and node.name in barhack_tags:
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

def get_var(name, context, attribute=None):
    if attribute is None:
        return context[name]
    elif name in context.variables:
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
        elif isinstance(value, list) or isinstance(value, basestring):
            # This is an array variable, yay
            # These are special in that they produce bacon on thursdays
            # Parse the indexes from the thingy
            try:
                # Ok, yes, I stole this from dyn_strstuff
                # Gave it an IOU for a cookie, so its all good
                if isinstance(value, basestring) and attribute == '':
                    return value
                parts = attribute.split(" ")
                indexpart = parts[0]
                seperator = ''
                if len(parts) > 1:
                    seperator = ' '.join(parts[1:])
                elif isinstance(value, list):
                    seperator = ' '

                parts = indexpart.split(":") 
                if parts[0] == '':
                    a = None
                else:
                    a = int(get_var_maybe(parts[0], context))
                
                if len(parts) == 1:
                    return stringify(value[a])
                else:
                    if parts[1] == '':
                        b = None
                    else:
                        b = int(get_var_maybe(parts[1], context))
                
                    if len(parts) > 2:
                        c = int(get_var_maybe(parts[2], context))
                    else:
                        c = None
                    
                    return stringify(seperator.join(value.__getitem__(slice(a, b, c))))
            except:
                return "[ERR]"
        else:
            return value
    else:
        return None
    
def get_var_maybe(name, context):
    value = context[name]
    if value is None:
        return name
    else:
        return value

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
    if "tag_%s" % node.name in globals():
        return globals()['tag_%s' % node.name](node, context)
    
    # If we have a tag registered by another module, try that.
    if node.name in registered_tags:
        return registered_tags[node.name](node, context)
    
    # If we get here, it's not a tag.
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
    if node.name != 'root' and (node.parent.name != 'choose' or node.name != '|' or node.parent.children[0] is not node):
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
    add_hook('unloaded', unloaded)
    try:
        m('webserver').add_handler('GET', weblist)
    except ModuleNotLoaded:
        pass

def add_tag(tag, handler, parent=False):
    if tag in registered_tags or 'tag_%s' % tag in globals():
        raise TagAlreadyExists, tag
    module = get_calling_module()
    registered_tags[tag] = handler
    if parent:
        parent_tags.add(tag)
    if module not in module_registrations:
        module_registrations[module] = []
    module_registrations[module].append(tag)

def unloaded(module):
    if module in module_registrations:
        for tag in module_registrations[module]:
            del registered_tags[tag]
            if tag in parent_tags:
                parent_tags.remove(tag)
        del module_registrations[module]

def find_command(command, version = None):
    if version is None:
        result = m('datastore').query("SELECT source FROM dynamic WHERE command = ? ORDER BY version DESC LIMIT 1", command)
    else:
        result = m('datastore').query("SELECT source FROM dynamic WHERE command = ? AND version = ?", command, version)
    if len(result) == 0:
        return None
    return result[0][0]

def command_has_existed(command):
    return bool(m('datastore').query("SELECT version FROM dynamic WHERE command = ?"))

def update_command(command, source, origin, create=True):
    sql = "INSERT INTO dynamic (command, source, version, creator) VALUES (?, ?, %s, ?)"
    if isinstance(origin, int) or origin is None:
        uid = origin
    else:
        uid = m('security').get_user_id(origin)
    if m('datastore').query("SELECT version FROM dynamic WHERE command = ?", command):
        sql = sql % "(SELECT version FROM dynamic WHERE command = ? ORDER BY version DESC LIMIT 1) + 1"
        args = (command, source, command, uid)
    else:
        if not create:
            return
        sql = sql % "1"
        args = (command, source, uid)
    m('datastore').execute(sql, *args)

def message(irc, channel, origin, command, args):
    irc_helpers = m('irc_helpers')
    if command in ('add', 'delete', 'source', 'append', 'eval', 'revisions', 'revert',):
        if not m('security').check_action_permissible(origin, "%s" % command):
            return
        
        if command == 'add':
            if len(args) < 2:
                irc_helpers.message(irc, channel, "You must provide a command name and something for it to do.")
            else:
                source = ' '.join(args[1:])
                update_command(args[0], ' '.join(args[1:]), origin)
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
                update_command(c, source, origin)
                irc_helpers.message(irc, channel, "Updated ~B%s~B." % c)
        elif command == 'delete':
            if len(args) != 1:
                irc_helpers.message(irc, channel, "You must specify what you want to delete.")
            else:
                update_command(args[0], None, origin, create=False)
                irc_helpers.message(irc, channel, "Deleted command ~B%s~B." % args[0])
        elif command == 'source':
            if len(args) < 1:
                irc_helpers.message(irc, channel, "You must specify what you want the source for.")
            else:
                if len(args) > 1:
                    source = find_command(args[0], args[1])
                else:
                    source = find_command(args[0])
                if source is not None:
                    try:
                        source = format_source(parse_tree(source))
                    except ParseError, message:
                        irc_helpers.message(irc, channel, "~BParse error (%s); highlighting disabled.~B" % message)
                    irc_helpers.message(irc, channel, source, tag=args[0])
                elif len(args) == 1:
                    irc_helpers.message(irc, channel, "The command ~B%s~B does not exist." % args[0])
                elif m('datastore').query("SELECT version FROM dynamic WHERE command = ? and version = ?", args[0], args[1]):
                    irc_helpers.message(irc, channel, "During that revision, the command had been deleted.")
                else:
                    irc_helpers.message(irc, channel, "There has been no revision %s." % args[1])
        elif command == 'revisions':
            revisions = m('datastore').query("SELECT version, creator, time, source FROM dynamic WHERE command = ? ORDER BY version DESC LIMIT 7", args[0])
            if not revisions:
                m('irc_helpers').message(irc, channel, "That command has never existed.", tag='dynamic')
            else:
                m('irc_helpers').message(irc, channel, "~URevisions of ~B%s~B:~U" % args[0], tag='dynamic')
                i = 0
                for revision in revisions:
                    num = revision[0]
                    if revision[1] is not None:
                        creator = m('security').get_user_nick(revision[1])
                    else:
                        creator = 'Unknown'
                    if revision[2] is not None:
                        time = datetime.datetime.strptime(revision[2], '%Y-%m-%d %H:%M:%S').strftime('%H:%M, %d/%m/%Y')
                    else:
                        time = 'Unknown'
                    source = revision[3]
                    i += 1
                    if i < len(revisions):
                        previous = revisions[i][3] or ''
                    else:
                        previous = ''
                    if source is None:
                        message = 'Command deleted'
                    elif len(source) < len(previous):
                        message = 'Deleted %s characters' % (len(previous) - len(source))
                    elif len(previous) < len(source):
                        message = 'Added %s characters' % (len(source) - len(previous))
                    elif previous == source:
                        message = 'No change'
                    else:
                        message = 'Length unchanged'
                    m('irc_helpers').message(irc, channel, "Revision ~B#%s~B by ~B%s~B (~B%s~B): %s" % (num, creator, time, message), tag='dynamic')
        elif command == 'revert':
            old = m('datastore').query("SELECT source, creator FROM dynamic WHERE command = ? AND version = ?", args[0], args[1])
            if not old:
                m('irc_helpers').message(irc, channel, "That revision has never existed.")
            else:
                update_command(args[0], old[0][0], old[0][1])
                m('irc_helpers').message(irc, channel, "Reverted ~B%s~B to revision ~B%s~B." % (args[0], args[1]))
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
        <ul>"""
    commands = m('datastore').query("SELECT command FROM dynamic GROUP BY command ORDER BY command")
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

def typecast(value):
    try:
        intvar = int(value)
        floatvar = float(value)
        if abs(intvar - floatvar) < 0.00001:
            return intvar
        else:
            return floatvar
    except:
        return value

def get_calling_module():
    record = inspect.stack()[2][1]
    filename = os.path.split(record)
    if filename[1].startswith('__init__.py'):
        filename = os.path.split(filename[0])
    
    module = filename[1].split('.')[0]
    
    return module

# Tag defintions

def tag_if(node, context):
    try:
        test = eval(node.attribute, context)
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

# Thanks to Selig.
def tag_include(node, context):
    source = find_command(node.attribute)
    try:
        if source is not None:
            return stringify(dotree(parse_tree(source), context))
    except:
        return ""
    return "~B[Could not include: %s]~B" % node.attribute

def tag_import(node, context):
    source = find_command(node.attribute)
    if source is not None:
        context.variables[node.attribute] = parse_tree(source)
        return "";
    return "~B[Could not import: %s]~B" % node.attribute
    
def tag_l(node, context):
    return '['

def tag_r(node, context):
    return ']'

def tag_repeat(node, context):
    try:
        times = int(get_var_maybe(node.attribute, context))
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

def tag_args(node, context):
    try:
        if not node.attribute:
            return ' '.join(context.args)
        else:
            if ':' not in node.attribute:
                return context.args[int(node.attribute)]
            else:
                start, finish = node.attribute.split(':')
                return ' '.join(context.args[int(get_var_maybe(start, context)):int(get_var_maybe(finish, context))])
    except:
        return '~B[bad arg numbers %s]~B' % node.attribute

def tag_while(node, context):
    try:
        counter = 0
        value = ''
        while eval(node.attribute, context):
            value += treelevel(node, context)
            counter += 1
            if counter >= 50:
                value += '~B[excessive looping; abandoning]~B'
                break
        return value
    except (NameError, SyntaxError):
        return "~B[bad while loop]~B"  

def tag_random(node, context):
    r = node.attribute.split(':')
    try:
        a = get_var_maybe(r[0], context)

        if isinstance(a, list):
            return random.choice(a)

        b = get_var_maybe(r[1], context)
        return stringify(random.randint(int(a), int(b)))
    except:
        raise ParseError, "[random a:b] requires two integers a and b (a <= result <= b)"

def tag_countdown(node, context):
    return timediff(timelib.strtodatetime(node.attribute) - datetime.datetime.utcnow())

def tag_countup(node, context):
    return timediff(datetime.datetime.utcnow() - timelib.strtodatetime(node.attribute))

def tag_choose(node, context):
    # Deal with the old [c]..[/c] format.
        if len(node.children) == 1 and node.children[0].name == '|':
            real_children = node.children[0].children
        else:
            real_children = node.children
        return dotree(random.choice(real_children), context)

def tag_noun(node, context):
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

def tag_verb(node, context):
    verb = word_from_file('data/verbs')
    tense = node.attribute or 'root'
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

def tag_adjective(node, context):
    return word_from_file('data/adjectives')

def tag_adverb(node, context):
    return word_from_file('data/adverbs')

def tag_interjection(node, context):
    return word_from_file('data/interjections')

def tag_place(node, context):
        return word_from_file('data/places')

def tag_rnick(node, context):
    if context.channel[0] != '#':
        return random.choice((context.irc.nick, context.channel))
    else:
        try:
            return random.choice(m('chantrack').network(context.irc)[context.channel].users.values()).nick
        except ModuleNotLoaded:
            return context.origin.nick

def tag_try(node, context):
    value = get_var(node.attribute, context)
    if value is not None:
        return value
    else:
        return treelevel(node, context)

def tag_func(node, context):
    context.variables[node.attribute] = node
    return ''

def tag_set(node, context):
    context.variables[node.attribute] = typecast(treelevel(node, context))
    return ''

def tag_get(node, context):
    name = treelevel(node, context)
    return stringify(get_var(name, context, node.attribute))


def tag_math(node, context):
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
        result = eval(expression, context, math_functions)
        if abs(result) < 0.000000001 and result != 0:
            result = 0.0
        return stringify(result)
    except:
        return '~B[unsolvable sums]~B'

def tag_switch(node, context):
    test = get_var_maybe(node.attribute, context)
    for child in node.children:
        if get_var_maybe(child.attribute, context) == test:
            return treelevel(child, context)
            break
    return ''

# Selig was here

def tag_list(node, context):
    varname = node.attribute
    value = []
    for child in node.children:
        value.append(dotree(child, context))
    context[varname] = value
    return ''

def tag_append(node, context):
    varname = node.attribute
    value = []
    varval = context[varname]
    if isinstance(varval, list):
        value = context[varname]
    elif isinstance(varval, basestring):
        value = [varval]
    else:
        return "~B[Can not append to unknown variable type]~B"

    for child in node.children:
        value.append(dotree(child, context))

    if isinstance(varval, basestring):
        value = ''.join(value)
    
    context[varname] = value
    return ''

def tag_for(node, context):
    parts = node.attribute.split(' in ')
    varname = parts[0]
    varlist = parts[1]

    vals = context[varlist] #get_var(varlist)

    ret = ''

    for val in vals:
        print "Val:(%s) %s" % (type(val), val)
        context[varname] = val
        ret += treelevel(node, context)
    
    return ret

def tag_delete(node, context):
    parts = node.attribute.split(" ")
    varname = parts[0]
    try:
        index = parts[1]
    except:
        index = ''

    value = context.variables[varname]

    if index == '' or isinstance(value, basestring):
        del context.variables[varname]

    try:
        parts = index.split(':')
        if parts[0] == '':
            a = None
        else:
            a = int(get_var_maybe(parts[0], context))
        
        if len(parts) == 1:
            what = a
        else:
            if parts[1] == '':
                b = None
            else:
                b = int(get_var_maybe(parts[1], context))
        
            if len(parts) > 2:
                c = int(get_var_maybe(parts[2], context))
            else:
                c = None
            what = slice(a, b, c)

        context.variables[varname].__delitem__(what)
    except:
        # We should probably error or soemthing
        pass
    finally:
        return ''

