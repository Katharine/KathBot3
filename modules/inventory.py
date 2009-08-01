#Davy//8-1-09
import random #We WILL use this sometime! :p

def parse_actions(irc, target, usernick, userid, message):
    irch = m('irc_helpers')
    
    temp = m('datastore').query('SELECT name FROM inventory_items')
    items = []
    
    actions = ['trashes', 'deletes', 'drops', 'removes', 'throws', 'gives', 'hands', 'tosses']
    interactions = ['hug', 'kis', 'lic', 'cud', 'nuz', 'pet', 'snu', 'lov']
    
    for item in temp:
        if item.strip() != '' and item.strip() != None:
            items.append(item[0].strip().lower())
    nicks = ''
    
    temp = message.split()
    words = []
    pattern = []
    for word in words:
        if word in items:
            pattern.append('item')
            words.append(word)
        if word in actions:
            pattern.append('actions')
            words.append(word)
        if word in interactions:
            pattern.append('interactions')
            words.append(word[0:2])
        if word in nicks:
            pattern.append('nick')
            words.append(word)
    
    give_words = ['throws', 'gives', 'hands', 'tosses']
    trash_words = ['trashes', 'deletes', 'drops', 'removes']
    
    index = 0
    for kind in pattern:
        #Actions and interactions are initiators. Meaning if we find then, we look for things to go with them. If we can't find things to go with them, we bail.
        word = words[index]
        next = pattern[index+1]
        if kind == 'action':
            if next == 'item':
                if word in trash_words:
                    #User getting rid of their own item.
                    revoke_item(userid, item_id_by_name(word))
                    irch.message(irc, target, '~B[Inventory]~B [%s lost one %s.]' % (usernick, word))
                elif word in give_words:
                    #User is giving an item to someone.
                    if pattern[index+2] == 'nick':
                        target = m('chantrack').create_user(irc, words[index+2])
                        targetid = m('security').get_user_id(target)
                        irch.message(irc, target, '~B[Inventory]~B [%s lost one %s.]' % (usernick, word))
                        irch.message(irc, target, '~B[Inventory]~B [%s acquired one %s.]' % (target.nick, word))
                        revoke_item(userid, item_id_by_name(word))
                        give_item(targetid, item_id_by_name(word))
                        return
                    else:
                        return
                else:
                    return
            elif next == 'nick':
                if pattern[index+2] == 'interaction':
                    #User is saying (e.x)"gives nick a hug". Just pretend they said (e.x)"hugs nick"
                    target = m('chantrack').create_user(irc, words[index+1])
                    targetid = m('security').get_user_id(target)
                    give_stat(targetid, stat_id_by_name(words[index+2]))
                    irch.message(irc, target, '~B[Inventory]~B [%s has been %s.]' % (target.nick, get_stat_fullname(stat_id_by_name(words[index+2]))))
                    return
                else:
                    return
            else:
                return
        elif kind == 'interaction':
            if next == 'nick':
                #User is saying (e.x)"hugs nick"
                target = m('chantrack').create_user(irc, words[index+1])
                targetid = m('security').get_user_id(target)
                give_stat(targetid, stat_id_by_name(word))
                irch.message(irc, target, '~B[Inventory]~B [%s has been %s.]' % (target.nick, get_stat_fullname(stat_id_by_name(words[index+2]))))
                return
            else:
                return
        else:
            return
        
        
        index += 1
    

###
def give_item(userid, itemid):
    #~Add user if they don't exist BEFORE interacting!~#
    if len(m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, stat_id_by_name('ALIVE'))) == 0:
        m('datastore').execute('REPLACE INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, item_id_by_name('Fork'), 1)
        m('datastore').execute('REPLACE INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, stat_id_by_name('ALIVE'), 1)
    #~#
    
    count = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        m('datastore').execute('INSERT INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, itemid, 1)
    else:
        m('datastore').execute("UPDATE inventory_user_items SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] + 1, userid, itemid)

###       
def revoke_item(userid, itemid):
    #~Add user if they don't exist BEFORE interacting!~#
    if len(m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, stat_id_by_name('ALIVE'))) == 0:
        m('datastore').execute('REPLACE INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, item_id_by_name('Fork'), 1)
        m('datastore').execute('REPLACE INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, stat_id_by_name('ALIVE'), 1)
    #~#
    
    count = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        #Uh..They don't have the item. >.>
        return #Return and do nothing, though we should never get here.
    elif count[0][0] - 1 <= 0:
        m('datastore').execute('DELETE FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    else:
        m('datastore').execute("UPDATE inventory_user_items SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] - 1, userid, itemid)

def give_stat(userid, itemid):
    #~Add user if they don't exist BEFORE interacting!~#
    if len(m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, stat_id_by_name('ALIVE'))) == 0:
        m('datastore').execute('REPLACE INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, item_id_by_name('Fork'), 1)
        m('datastore').execute('REPLACE INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, stat_id_by_name('ALIVE'), 1)
    #~#
    
    count = m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        m('datastore').execute('INSERT INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, itemid, 1)
    else:
        m('datastore').execute("UPDATE inventory_user_items SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] + 1, userid, itemid)

###
def add_item(name, description, effects):
    if len(m('datastore').query('SELECT description FROM inventory_items WHERE name = ?', name)) == 0:
        m('datastore').execute('INSERT INTO inventory_items (name, description, effects) VALUES (?, ?, ?)', name, description, effects)
        return True
    return False

###
def add_effect(name, description):
    if len(m('datastore').query('SELECT description FROM inventory_effects WHERE name = ?', name)) == 0:
        m('datastore').execute('INSERT INTO inventory_effects (name, description) VALUES (?, ?)', name, description)
        return True
    else:
        return False

###
def add_stat(shortname, fullname):
    if len(m('datastore').query('SELECT fullname FROM inventory_stats WHERE shortname = ?', shortname)) == 0:
        m('datastore').execute('INSERT INTO inventory_stats (shortname, fullname) VALUES (?, ?)', shortname, fullname)
        return True
    return False

###
def user_has_effect(userid, effectquery):
    data = m('datastore').query('SELECT itemid FROM inventory_user_items WHERE userid = ?', userid)
    effects = []
    for item in data:
        effects.extend(m('datastore').query('SELECT effects FROM inventory_items WHERE userid = ? AND itemid = ?', userid, item[0]).split(','))
    if effectquery in effects:
        return True
    return False

###     
def user_has_item(userid, itemquery):
    data = m('datastore').query('SELECT itemid FROM inventory_user_items WHERE userid = ?', userid)
    items = []
    for item in data:
        items.extend(item[0])
    if itemquery in items:
        return True
    return False

###     
def return_user_stat(userid, statquery):
    data = m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND name = ?', userid, statquery)
    items = []
    for item in data:
        items.extend(item[0])
    if itemquery in items:
        return True
    return False

###
def item_id_by_name(name):
    ID = m('datastore').query('SELECT id FROM inventory_items WHERE name = ?', name)
    if len(ID) <= 0:
        return ''
    return ID[0][0]

###
def item_name_by_id(ID):
    name = m('datastore').query('SELECT name FROM inventory_items WHERE id = ?', ID)
    if len(name) <= 0:
        return ''
    return name[0][0]

###
def effect_id_by_name(name):
    ID = m('datastore').query('SELECT id FROM inventory_effects WHERE name = ?', name)
    if len(ID) <= 0:
        return ''
    return ID[0][0]

###
def effect_name_by_id(ID):
    name = m('datastore').query('SELECT name FROM inventory_effects WHERE id = ?', ID)
    if len(name) <= 0:
        return ''
    return name[0][0]

###
def stat_id_by_name(shortname):
    ID = m('datastore').query('SELECT id FROM inventory_stats WHERE shortname = ?', shortname)
    if len(ID) <= 0:
        return ''
    return ID[0][0]

###
def stat_name_by_id(ID):
    shortname = m('datastore').query('SELECT shortname FROM inventory_stats WHERE id = ?', ID)
    if len(shortname) <= 0:
        return ''
    return shortname[0][0]

###
def get_item_description(ID):
    description = m('datastore').query('SELECT description FROM inventory_items WHERE id = ?', ID)
    if len(description) <= 0:
        return ''
    return description[0][0]

###
def get_effect_description(ID):
    description = m('datastore').query('SELECT description FROM inventory_effects WHERE id = ?', ID)
    if len(description) <= 0:
        return ''
    return description[0][0]
    
###
def get_stat_fullname(ID):
    description = m('datastore').query('SELECT fullname FROM inventory_stats WHERE id = ?', ID)
    if len(description) <= 0:
        return ''
    return description[0][0]

###
def list_inventory(userid):
    ids = m('datastore').query('SELECT itemid FROM inventory_user_items WHERE userid = ?', userid)
    counts = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ?', userid)
    inventory = {}
    index = 0
    while index < len(ids):
        inventory[item_name_by_id(ids[index][0])] = counts[index][0]
        index += 1
    return inventory;

###
def list_stats(userid):
    ids = m('datastore').query('SELECT itemid FROM inventory_user_stats WHERE userid = ?', userid)
    counts = m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ?', userid)
    stats = {}
    index = 0
    while index < len(ids):
        stats[get_stat_fullname(ids[index][0])] = counts[index][0]
        index += 1
    return stats;

######################
######################
def init():
    add_hook('message', message)
    add_hook('privmsg', privmsg)

COMMANDS = frozenset(('inventory', 'inspect', 'examine', 'give', 'trash', 'delete', 'addeffect', 'additem', 'addstat'))

def message(irc, channel, origin, command, args):
    irch = m('irc_helpers')
    target = channel
    if command not in COMMANDS:
        return
    userid = int(m('security').get_user_id(origin))
    
    #~Add user if they don't exist BEFORE interacting!~#
    if len(m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, stat_id_by_name('ALIVE'))) == 0:
        m('datastore').execute('REPLACE INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, item_id_by_name('Fork'), 1)
        m('datastore').execute('REPLACE INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, stat_id_by_name('ALIVE'), 1)
    #~#
    
    if command == 'inventory':
        itemlist = list_inventory(userid)
        istring = '%s has ' % m('security').get_canonical_nick(origin.nick)
        for item in itemlist:
            istring += '%s %s, ' % (itemlist[item], item)
        istring += 'and '
        statlist = list_stats(userid)
        if len(statlist) == 1:
            istring += "doesn't currenly have any statistics, but is noted to be alive."
        else:
            istring += 'has gotten '
            for stat in statlist:
                istring += '%s %s, ' % (statlist[stat], stat)
            istring = istring[0:len(istring)-2]
            istring += ', and is noted to be alive.'
        irch.message(irc, target, '~B[Inventory]~B ' + istring)
    elif command == 'inspect' or command == 'examine':
        #!examine item   -or-   !inspect item
        if len(args) >= 1:
            name = ' '.join(args).strip()
            description = get_item_description(item_id_by_name(name))
            if description != '' and description != None:
                irch.message(irc, target, "~B[Inventory]~(Examining '%s')~B %s" % (name, description))
            else:
                irch.message(irc, target, "~B[Inventory]~B You don't have one of those to examine.")
    elif command == "give":
        #!give nick item
        item = args[1]
        target = args[0]
        target = m('chantrack').create_user(irc, target)
        targetid = m('security').get_user_id(target)
        irch.message(irc, target, '~B[Inventory]~B [%s lost one %s.]' % (origin.nick, item))
        irch.message(irc, target, '~B[Inventory]~B [%s acquired one %s.]' % (target.nick, item))
        revoke_item(userid, item_id_by_name(item))
        give_item(targetid, item_id_by_name(item))
    elif command == 'trash' or command == 'delete':
    #!trash item   -or-   !delete item
        item = args
        irch.message(irc, target, '~B[Inventory]~B [%s lost one %s.]' % (origin.nick, item))
        revoke_item(userid, item_id_by_name(item))
    elif command == 'addeffect':
        #!addeffect name (description)
        name = args[0:args.find('(')]
        description = args[args.find('(')+1:args.find(')')]
        add_effect(name, description)
    elif command == 'addstat':
        #!addstat name (description)
        name = args[0:args.find('(')]
        description = args[args.find('(')+1:args.find(')')]
        add_stat(name, description)
    elif command == 'additem':
        #!additem name (description) with (effect1, effect2, effect3, etc..)
        name = args[0:args.find('(')]
        description = args[args.find('(')+1:args.find(')')]
        temp = args[args.find('with (')+6:len(args)-2].split(',')
        effects = []
        for effect in temp:
            if effect.strip() != '' and effect.strip() != None:
                effects.append(effect.strip())
        effects = ','.join(effects)
        add_item(name, description, effects)



def privmsg(irc, origin, args):
    irch = m('irc_helpers')
    target, command, args = irch.parse(args)
    userid = int(m('security').get_user_id(origin))
    
    if args == None:
        return #What the fuck? Why should this happen?? #...Right, it's PRIVMSG.
    
    message = ' '.join(args)
    
    if '\x01ACTION' not in message:
        return
    
    #~Add user if they don't exist BEFORE interacting!~#
    if len(m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, stat_id_by_name('ALIVE'))) == 0:
        m('datastore').execute('REPLACE INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, item_id_by_name('Fork'), 1)
        m('datastore').execute('REPLACE INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, stat_id_by_name('ALIVE'), 1)
    #~#
    
    message = message[7:len(message)-2]
    irch.message(irc, target, '')
    parse_actions(irc, target, m('security').get_canonical_nick(origin.nick), userid, message)
