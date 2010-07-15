# encoding: utf-8

from subprocess import Popen, PIPE
import locale

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == "sourcestats":
        files = int(Popen('ls -R ./ | grep .py$ | wc -l', stdout=PIPE, shell=True).communicate()[0].strip())
        count = Popen('cat *.py */*.py */*/*.py | wc -lcL', stdout=PIPE, shell=True).communicate()[0].strip().split(' ')
        count = [x for x in count if x != '']
        lines = locale.format('%d', int(count[0]), True)
        longest = locale.format('%d', int(count[2]), True)
        size = int(count[1])
        suffixes = ("bytes","KB","MB","GB","TB","PB","EB")
        suffix = 0
        while size > 1024 and suffix < len(suffixes):
            size /= 1024
            suffix += 1
        
        m('irc_helpers').message(irc, channel, u"Files: ~B%s~B · Lines of code: ~B%s~B · Longest line: ~B%s~B characters · Total size: ~B%s %s~B" % (files, lines, longest, size, suffixes[suffix]))
