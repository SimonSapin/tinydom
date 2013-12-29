# coding: utf8
from xml.parsers import expat


try:
    iteritems = dict.iteritems
except AttributeError:
    iteritems = dict.items


try:
    unicode = unicode
except NameError:
    unicode = str


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
    # Use a one-element list to work around the lack on nonlocal on 2.x
    stack_top = [root]

    def handler(function):
        setattr(parser, function.__name__, function)

    @handler
    def StartElementHandler(name, attributes):
        namespace_url, _, local_name = name.rpartition(' ')
        attributes = dict(
            ((namespace_url, local_name), value)
            for name, value in iteritems(attributes)
            for namespace_url, _, local_name in [name.rpartition(' ')]
        ),
        children = []
        new_element = Element(
            namespace_url,
            local_name,
            attributes,
            children,
            parser.CurrentLineNumber,
            parser.CurrentColumnNumber,
        )
        stack_top[0].append(new_element)
        stack.append(stack_top[0])
        stack_top[0] = children

    @handler
    def EndElementHandler(_name):
        stack_top[0] = stack.pop()

    @handler
    def CharacterDataHandler(data):
        stack_top[0].append(TextNode(data))

    if hasattr(input, 'read'):
        parser.ParseFile(input)
    else:
        parser.Parse(input, True)

    assert len(stack) == 0  # All elements are closed
    assert len(root) == 1  # The top-level only has one node, the root element.
    return root[0]


def from_etree(etree_element):
    namespace_url, local_name = _split_etree_tag(etree_element.tag)
    attributes = dict(
        (_split_etree_tag(name), value)
        for name, value in etree_element.items()
    ),
    children = []

    if etree_element.text:
        children.append(TextNode(etree_element.text))

    for etree_child in etree_element:
        children.append(from_etree(etree_child))
        if etree_child.tail:
            children.append(TextNode(etree_child.tail))

    return Element(
        namespace_url,
        local_name,
        attributes,
        children,
        line=getattr(etree_element, 'sourceline', None),
        column=None,
    )


def _split_etree_tag(tag):
    pos = tag.rfind('}')
    if pos == -1:
        return '', tag
    else:
        assert tag[0] == '{'
        return tag[1:pos], tag[pos + 1:]


class Element(object):
    def __init__(self, namespace_url, local_name, attributes, children,
                 line, column):
        self.namespace_url = namespace_url
        self.local_name = local_name
        self.attributes = attributes
        self.children = children
        self.line = line
        self.column = column


class TextNode(object):
    def __init__(self, text):
        self.text = text


if __name__ == '__main__':
    xml = '''
        <r>
            <aé xmlns:n="U" n:b="c" />
        </r>
    '''
    parse_xml(xml)
    import xml.etree.ElementTree as etree
    from_etree(etree.fromstring(xml))
