import os
import xml.dom.minidom as dom
import random

current_question = {}

def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if not command:
        return
    if command == 'theory':
        letters = 'ABCDEFGH'
        key = '%s/%s' % (irc.network, target)
        if len(args) == 0:
            question = get_question()
            irc_helpers.message(irc, target, '~B[Theory] %s' % question.text)
            irc_helpers.message(irc, target, '~B[Theory]~B (%s)' % question.prompt)
            for i in range(0, len(question.options)):
                irc_helpers.message(irc, target, '~B[Theory]~B %s: ~U%s~U' % (letters[i], question.options[i].text))
            current_question[key] = question
        else:
            if key not in current_question:
                irc_helpers.message(irc, target, "You can't answer a question until one has been asked.")
            else:
                answers = [x.upper().strip() for x in ' '.join(args).split(',')]
                answers.sort()
                expected = []
                question = current_question[key]
                for i in range(0, len(question.options)):
                    option = question.options[i]
                    if option.correct:
                        expected.append(letters[i])
                if answers == expected:
                    irc_helpers.message(irc, target, "~B[Theory] Correct! :D~B")
                else:
                    irc_helpers.message(irc, target, "~B[Theory] Incorrect. The correct answer was %s" % ', '.join(expected))
                del current_question[key]
                

def get_question(filename=None):
    if filename is None:
        filename = random.choice(os.listdir('data/driving'))
    xml = dom.parse('data/driving/' + filename)
    question = xml.getElementsByTagName('question')[0].getElementsByTagName('text')[0].firstChild.data
    prompt = xml.getElementsByTagName('prompt')[0].firstChild.data
    options = []
    for option in xml.getElementsByTagName('answer'):
        options.append(Option(text=option.getElementsByTagName('text')[0].firstChild.data, correct=(option.getAttribute('correct') == 'yes')))
    
    xml.unlink()
    return Question(text=question, prompt=prompt, options=options, filename=filename)

class Option(object):
    def __init__(self, text='', correct=False):
        self.text = text
        self.correct = correct

class Question(object):
    def __init__(self, text='', prompt='', options=None, filename=None):
        self.text = text
        self.prompt = prompt
        self.options = options
        self.filename = filename
        if options is None:
            self.options = []