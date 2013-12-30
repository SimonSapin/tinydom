# coding: utf8

from xml.parsers import expat

from ._compat import unicode, basestring, iteritems


def parse_xml(input, encoding=None):
    """Parse from XML, using pyexpat.

    :param input:
        A file-like object (anything with a :meth:`~file.read` method),
        a byte string,
        or an Unicode string.
    :returns:
        the :class:`Element` object for the root element.
    """
    if isinstance(input, unicode):
        input = input.encode('UTF-8')
        encoding = 'UTF-8'
    parser = XMLParser(encoding)
    if hasattr(input, 'read'):
        parser.expat.ParseFile(input)
    else:
        parser.expat.Parse(input, True)
    return parser.get_root()


class XMLParser(object):
    def __init__(self, encoding=None):
        self.stack = []
        self.elements = []
        # Namespace URLs can contains spaces, but element names can’t.
        # So we’ll split on the *last* space.
        self.expat = expat.ParserCreate(encoding, namespace_separator=' ')

        self.expat.StartElementHandler = self.start_element
        self.expat.EndElementHandler = self.end_element
        self.expat.CharacterDataHandler = self.charater_data

    def get_root(self):
        assert len(self.stack) == 0  # All elements are closed
        assert len(self.elements) == 1  # Only one top-level element, the root
        return self.elements[0]

    def start_element(self, name, attributes):
        elements = self.elements
        if elements:
            previous_element = elements[-1]
            previous_element.tail = ''.join(previous_element.tail)

        namespace_url, _, local_name = name.rpartition(' ')
        attributes = dict(
            ((namespace_url, local_name), value)
            for name, value in iteritems(attributes)
            for namespace_url, _, local_name in [name.rpartition(' ')]
        ),
        text = []
        new_children = []
        tail = []
        new_element = Element(
            namespace_url,
            local_name,
            attributes,
            text,
            new_children,
            tail,
            self.expat.CurrentLineNumber,
            self.expat.CurrentColumnNumber,
        )
        elements.append(new_element)
        self.stack.append(elements)
        self.elements = new_children

    def end_element(self, _name):
        elements = self.stack.pop()
        ended_element = elements[-1]
        ended_element.text = ''.join(ended_element.text)
        self.elements = elements

    def charater_data(self, data):
        elements = self.elements
        if elements:
            elements[-1].tail.append(data)
        else:
            self.stack[-1][-1].text.append(data)


def parse_html(input, encoding=None):
    """Parse from HTML, using html5lib.

    :param input:
        A file-like object (anything with a :meth:`~file.read` method),
        a byte string,
        or an Unicode string.
    :returns:
        the :class:`Element` object for the root element.
    """
    from .html import HTMLParser
    return HTMLParser().parse(input, encoding, useChardet=False)


def from_etree(etree_element):
    namespace_url, local_name = _split_etree_tag(etree_element.tag)
    return Element(
        namespace_url,
        local_name,
        attributes=dict(
            (_split_etree_tag(name), value)
            for name, value in etree_element.items()
        ),
        text=etree_element.text or '',
        children=[
            from_etree(etree_child)
            for etree_child in etree_element
            # Leave out comments and processing instructions:
            if isinstance(etree_child.tag, basestring)
        ],
        tail=etree_element.tail or '',
        line=getattr(etree_element, 'sourceline', None),
    )


def _split_etree_tag(tag):
    pos = tag.rfind('}')
    if pos == -1:
        return '', tag
    else:
        assert tag[0] == '{'
        return tag[1:pos], tag[pos + 1:]


class Element(object):
    def __init__(self, namespace_url, local_name, attributes,
                 text, children, tail, line=None, column=None):
        self.namespace_url = namespace_url
        self.local_name = local_name
        self.attributes = attributes
        self.text = text
        self.children = children
        self.tail = tail
        self.line = line
        self.column = column

    def __repr__(self):
        return '<Element %s%s at 0x%x>' % (
            '{%s}' % self.namespace_url if self.namespace_url else '',
            self.local_name,
            id(self),
        )
