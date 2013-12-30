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

try:
    basestring = basestring
except NameError:
    basestring = str


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
    from html5lib.treebuilders import _base

    class DocumentNode(object):
        def __init__(self):
            self.root = None

        def appendChild(self, root):
            assert self.root is None
            self.root = root

    class ElementNode(object):
        def __init__(self, name, namespace):
            self._element = Element(
                namespace, name, attributes={}, text='', children=[], tail='')
            self.nameTuple = (namespace, name)
            self.namespace = namespace
            self.name = name
            self.parent = None
            self._childNodes = []
            self._attributes = {}

        @property
        def attributes(self):
            return self._attributes

        @attributes.setter
        def attributes(self, new_attributes):
            self._attributes = new_attributes
            self._element.attributes = dict(
                ((key[2], key[1]) if isinstance(key, tuple) else key, value)
                for key, value in iteritems(new_attributes)
            )

        def hasContent(self):
            return bool(self._element.text or self._element.children)

        def appendChild(self, node):
            self._childNodes.append(node)
            self._element.children.append(node._element)
            node.parent = self

        def insertBefore(self, node, refNode):
            index = self._element.children.index(refNode._element)
            self._element.children.insert(index, node._element)
            node.parent = self

        def removeChild(self, node):
            self._element.children.remove(node._element)
            node.parent = None

        def insertText(self, data, insertBefore=None):
            if not self._element.children:
                self._element.text += data
            elif insertBefore is None:
                # Insert the text as the tail of the last child element
                self._element.children[-1].tail += data
            else:
                # Insert the text before the specified node
                index = self._element.children.index(insertBefore._element)
                self._element.children[index - 1].tail += data

        def cloneNode(self):
            element = ElementNode(self.name, self.namespace)
            element._element.attributes = self._element.attributes.copy()
            return element

        def reparentChildren(self, newParent):
            if newParent._element.children:
                newParent._element.children[-1].tail += self._element.text
            else:
                newParent._element.text += self._element.text
            self._element.text = ""
            for child in self._childNodes:
                newParent.appendChild(child)
            self._childNodes = []
            self._element.children = []


    class TreeBuilder(_base.TreeBuilder):
        documentClass = DocumentNode
        elementClass = ElementNode

        def insertDoctype(self, _token):
            pass

        def insertComment(self, _token, parent=None):
            pass

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


if __name__ == '__main__':
    xml = '''
        <r>
            <aé xmlns:n="U" n:b="c" />
        </r>
    '''
    parse_xml(xml)

    import xml.etree.ElementTree as etree
    from_etree(etree.fromstring(xml))

    t = parse_html('<!DOCTYPE html><p>a<b>c<!-- fuu --></b>d')
    print(t.local_name, t.children[1].children[0].children[0].text)
