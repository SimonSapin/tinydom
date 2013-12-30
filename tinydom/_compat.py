try:
    iteritems = dict.iteritems
except AttributeError:
    iteritems = dict.items

try:
    unicode = unicode
except NameError:
    unicode = str

try:
    basestring = basestring
except NameError:
    basestring = str
