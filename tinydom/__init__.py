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

    # Namespace URLs can contains spaces, but element names can’t.
    # So we’ll split on the *last* space.
    parser = expat.ParserCreate(encoding, namespace_separator=' ')

    root = []
    stack = []
    # Use a one-item list to work around the lack on nonlocal on 2.x
    nonlocal_elements = [root]

    def handler(function):
        setattr(parser, function.__name__, function)

    @handler
    def StartElementHandler(name, attributes):
        elements = nonlocal_elements[0]
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
            parser.CurrentLineNumber,
            parser.CurrentColumnNumber,
        )
        elements.append(new_element)
        stack.append(elements)
        nonlocal_elements[0] = new_children

    @handler
    def EndElementHandler(_name):
        elements = stack.pop()
        ended_element = elements[-1]
        ended_element.text = ''.join(ended_element.text)
        nonlocal_elements[0] = elements

    @handler
    def CharacterDataHandler(data):
        elements = nonlocal_elements[0]
        if elements:
            elements[-1].tail.append(data)
        else:
            stack[-1][-1].text.append(data)

    if hasattr(input, 'read'):
        parser.ParseFile(input)
    else:
        parser.Parse(input, True)

    assert len(stack) == 0  # All elements are closed
    assert len(root) == 1  # The top-level only has one node, the root element.
    return root[0]


def parse_html(input, encoding=None):
    """Parse from HTML, using html5lib.

    :param input:
        A file-like object (anything with a :meth:`~file.read` method),
        a byte string,
        or an Unicode string.
    :returns:
        the :class:`Element` object for the root element.
    """
    from html5lib import HTMLParser
    from .html import TreeBuilder

    parser = HTMLParser(TreeBuilder)
    document = parser.parse(input, encoding, useChardet=False)
    return document.root._element


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
