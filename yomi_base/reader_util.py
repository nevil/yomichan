# -*- coding: utf-8 -*-

# Copyright (C) 2013  Alex Yatskov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from PyQt4 import QtGui
import re
import codecs
import sqlite3


def decodeContent(content):
    encodings = ['utf-8', 'shift_jis', 'euc-jp', 'utf-16']
    errors = dict()

    for encoding in encodings:
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError, e:
            errors[encoding] = e[2]

    encoding = sorted(errors, key=errors.get, reverse=True)[0]
    return content.decode(encoding, 'replace'), encoding


def stripReadings(content):
    return re.sub(u'《[^》]+》', unicode(), content)


def findSentence(content, position):
    quotesFwd = {u'「': u'」', u'『': u'』', u"'": u"'", u'"': u'"'}
    quotesBwd = {u'」': u'「', u'』': u'『', u"'": u"'", u'"': u'"'}
    terminators = u'。．.？?！!'

    quoteStack = list()

    start = 0
    for i in xrange(position, start, -1):
        c = content[i]

        if not quoteStack and (c in terminators or c in quotesFwd or c == '\n'):
            start = i + 1
            break

        if quoteStack and c == quoteStack[0]:
            quoteStack.pop()
        elif c in quotesBwd:
            quoteStack.insert(0, quotesBwd[c])

    quoteStack = list()

    end = len(content)
    for i in xrange(position, end):
        c = content[i]

        if not quoteStack:
            if c in terminators:
                end = i + 1
                break
            elif c in quotesBwd:
                end = i
                break

        if quoteStack and c == quoteStack[0]:
            quoteStack.pop()
        elif c in quotesFwd:
            quoteStack.insert(0, quotesFwd[c])
    translation = ''
    translationStart = content.find('\t',end)
    if translationStart >= 0:
      translationEnd = content.find('\n',translationStart)
      if translationEnd == -1:
        translationEnd = len(content)
      translation = content[translationStart+1:translationEnd].strip() 
    return content[start:end].strip(), translation  


def formatFields(fields, markup):
    result = dict()
    for field, value in fields.items():
        try:
            result[field] = value.format(**markup)
        except KeyError:
            pass

    return result


def splitTags(tags):
    return filter(lambda tag: tag.strip(), re.split('[;,\s]', tags))


def markupVocabExp(definition):
    if definition['reading']:
        summary = u'{expression} [{reading}]'.format(**definition)
    else:
        summary = u'{expression}'.format(**definition)

    return {
        'expression': definition['expression'],
        'reading': definition['reading'] or unicode(),
        'glossary': definition['glossary'],
        'sentence': definition.get('sentence'),
        'translation': definition.get('translation'),
        'summary': summary
    }


def markupVocabReading(definition):
    if definition['reading']:
        return {
            'expression': definition['reading'],
            'reading': unicode(),
            'glossary': definition['glossary'],
            'sentence': definition.get('sentence'),
            'translation': definition.get('translation'),
            'summary': definition['reading']
        }


def copyVocabDef(definition):
    if definition['reading']:
        result = u'{expression}\t{reading}\t{glossary}\n'.format(**definition)
    else:
        result = u'{expression}\t{glossary}\n'.format(**definition)

    QtGui.QApplication.clipboard().setText(result)


def markupKanji(definition):
    return {
        'character': definition['character'],
        'onyomi': definition['onyomi'],
        'kunyomi': definition['kunyomi'],
        'glossary': definition['glossary'],
        'summary': definition['character']
    }


def copyKanjiDef(definition):
    return QtGui.QApplication.clipboard().setText(u'{character}\t{kunyomi}\t{onyomi}\t{glossary}'.format(**definition))


def buildDefHeader():
    palette = QtGui.QApplication.palette()
    toolTipBg = palette.color(QtGui.QPalette.Window).name()
    toolTipFg = palette.color(QtGui.QPalette.WindowText).name()

    return u"""
        <html><head><style>
        body {{ background-color: {0}; color: {1}; font-size: 11pt; }}
        span.expression {{ font-size: 15pt; }}
        </style></head><body>""".format(toolTipBg, toolTipFg)


def buildDefFooter():
    return '</body></html>'


def buildEmpty():
    return u"""
        <p>No definitions to display.</p>
        <p>Mouse over text with the <em>middle mouse button</em> or <em>shift key</em> pressed to search.</p>
        <p>You can also also input terms in the search box below."""


def buildVocabDef(definition, index, query):
    reading = unicode()
    if definition['reading']:
        reading = u'<span class="reading">[{0}]<br></span>'.format(definition['reading'])

    rules = unicode()
    if definition.get('rules'):
        rules = ' &lt; '.join(definition['rules'])
        rules = '<span class="rules">({0})<br></span>'.format(rules)

    links = '<a href="copyVocabDef:{0}"><img src="://img/img/icon_copy_definition.png" align="right"></a>'.format(index)
    if query is not None:
        if query('vocab', markupVocabExp(definition)):
            links += '<a href="addVocabExp:{0}"><img src="://img/img/icon_add_expression.png" align="right"></a>'.format(index)
        if query('vocab', markupVocabReading(definition)):
            links += '<a href="addVocabReading:{0}"><img src="://img/img/icon_add_reading.png" align="right"></a>'.format(index)

    html = u"""
        <span class="links">{0}</span>
        <span class="expression">{1}<br></span>
        {2}
        <span class="glossary">{3}<br></span>
        {4}
        <br clear="all">""".format(links, definition['expression'], reading, definition['glossary'], rules)

    return html


def buildVocabDefs(definitions, query):
    html = buildDefHeader()
    if len(definitions) > 0:
        for i, definition in enumerate(definitions):
            html += buildVocabDef(definition, i, query)
    else:
        html += buildEmpty()

    return html + buildDefFooter()


def buildKanjiDef(definition, index, query):
    links = '<a href="copyKanjiDef:{0}"><img src="://img/img/icon_copy_definition.png" align="right"></a>'.format(index)
    if query is not None and query('kanji', markupKanji(definition)):
        links += '<a href="addKanji:{0}"><img src="://img/img/icon_add_expression.png" align="right"></a>'.format(index)

    readings = ', '.join([definition['kunyomi'], definition['onyomi']])
    html = u"""
        <span class="links">{0}</span>
        <span class="expression">{1}<br></span>
        <span class="reading">[{2}]<br></span>
        <span class="glossary">{3}<br></span>
        <br clear="all">""".format(links, definition['character'], readings, definition['glossary'])

    return html


def buildKanjiDefs(definitions, query):
    html = buildDefHeader()

    if len(definitions) > 0:
        for i, definition in enumerate(definitions):
            html += buildKanjiDef(definition, i, query)
    else:
        html += buildEmpty()

    return html + buildDefFooter()


def extractKindleDeck(filename):
    words = list()

    try:
        with sqlite3.connect(unicode(filename)) as db:
            for row in db.execute('select word from WORDS'):
                words.append(row[0])
    except sqlite3.OperationalError:
        pass

    return words


def extractWordList(filename):
    words = list()

    with codecs.open(unicode(filename), 'rb', 'utf-8') as fp:
        words = re.split('[;,\s]', fp.read())

    return filter(None, words)
