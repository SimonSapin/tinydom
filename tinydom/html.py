from html5lib import HTMLParser as BaseHTMLParser
from html5lib.treebuilders import _base

from . import Element
from ._compat import iteritems


class HTMLParser(BaseHTMLParser):
    def __init__(self, *args, **kwargs):
        super(HTMLParser, self).__init__(TreeBuilder, *args, **kwargs)


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

    def insertComment(self, _token, _parent=None):
        pass

    def getDocument(self):
        return self.document.root._element
