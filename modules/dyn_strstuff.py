import re

def add_tags():
    m('dynamic').add_tag('regex', tag_regex, True)
    m('dynamic').add_tag('indef', tag_indefinite, True)
    m('dynamic').add_tag('indefinite', tag_indefinite, True)
    m('dynamic').add_tag('length', tag_length, True)
    m('dynamic').add_tag('capitalise', tag_capitalise, True)

def init():
    add_hook('loaded', evt_loaded)
    add_tags()

def evt_loaded(mod):
    if mod == 'dynamic':
        add_tags()

def tag_regex(node, context):
    Body = m('dynamic').treelevel(node, context)
    RegEx = node.attribute
    
    reg = re.search(RegEx, Body)
    if reg is None:
        return ""
    results = reg.groups()

    context.variables["match0"] = reg.group(0)

    i = 1
    for res in results:
        context.variables["match%s" % i] = res
        i += 1

    return ""

def tag_length(node, context):
    return m('dynamic').stringify(len(m('dynamic').treelevel(node, context)))

def tag_capitalise(node, context):
    contents = m('dynamic').treelevel(node, context)
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

def tag_indefinite(node, context):
    phrase = m('dynamic').treelevel(node, context)
    if phrase[0].lower() in 'aeiou':
        return "an %s" % phrase
    else:
        return "a %s" % phrase
