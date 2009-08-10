# This module allows us to store data in
# A persistant way with dynamic commands. :)
# Also, it makes bacon. Don't tell anyone though!

# The tags work like so:
# [cget vartoputin]channel var to load[/cget]
# [cset vartoexporte]var to save to[/cset]
# The g[gs]et vars work the same except they
# store to the global storage instead.

def add_tags():
    dynm = m('dynamic')
    # Channel local
    dynm.add_tag('cget', tag_cget, True)
    dynm.add_tag('cset', tag_cset, True)
    # Global
    dynm.add_tag('pget', tag_pget, True)
    dynm.add_tag('pset', tag_pset, True) 

def init():
    add_hook('loaded', evt_loaded)
    add_tags()

def evt_loaded(mod):
    if mod == 'dynamic':
        add_tags()

def tag_cget(node, context):
    destvar = node.attribute
    sourcevar = m('dynamic').treelevel(node, context)

    try:
        context[destvar] = m('datastore').channels[(context.irc, context.channel)]['dyn_' + sourcevar]
    finally:
        return ""

def tag_cset(node, context):
    sourcevar = node.attribute
    destvar = m('dynamic').treelevel(node, context)

    try:
        m('datastore').channels[(context.irc, context.channel)]['dyn_' + destvar] = context.variables[sourcevar]
    finally:
        return ""

def tag_pget(node, context):
    destvar = node.attribute
    sourcevar = m('dynamic').treelevel(node, context)

    try:
        context[destvar] = m('datastore').general['dyn_' + sourcevar]
    finally:
        return ""

def tag_pset(node, context):
    sourcevar = node.attribute
    destvar = m('dynamic').treelevel(node, context)

    try:
        m('datastore').general['dyn_' + destvar] = context.variables[sourcevar]
    finally:
        return ""
