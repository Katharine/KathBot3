def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == 'achievements':
        if len(args) == 1:
            user = args[0]
            achievements = Spore.GetAchievementsForUser(user, 0, 100)
            names = ', '.join([x.mName for x in achievements])
            m('irc_helpers').message(irc, channel, "Achievements for ~B%s~B: %s" % (user, names), 'Spore')
        elif len(args) == 2:
            user1 = args[0]
            user2 = args[1]
            ach1 = set([x.mName for x in Spore.GetAchievementsForUser(user1, 0, 100)])
            ach2 = set([x.mName for x in Spore.GetAchievementsForUser(user2, 0, 100)])
            common = ach1 & ach2
            user1only = ach1 - ach2
            user2only = ach2 - ach1
            m('irc_helpers').message(irc, channel, "~UComparing ~B%s~B and ~B%s~B~U" % (user1, user2), tag='Spore')
            m('irc_helpers').message(irc, channel, "Only ~B%s~B has: %s" % (user1, ', '.join(user1only)), tag='Spore')
            m('irc_helpers').message(irc, channel, "Only ~B%s~B has: %s" % (user2, ', '.join(user2only)), tag='Spore')
            m('irc_helpers').message(irc, channel, "Both ~B%s~B and ~B%s~B have: %s" % (user1, user2, ', '.join(common)), tag='Spore')