#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import types
import inspect
from decimal import Decimal
from StringIO import StringIO

from lxml import etree
DocumentInvalid = etree.DocumentInvalid

class UnknownXType(Exception):

    """
    Exception raised when a class prototype specifies a type which is not
    understood.
    """

class UnmatchedIdRef(Exception):

    """
    Exception raised when idref's cannot be matched with an id during
    XML generation.
    """

    def __str__(self):
        return ("Unmatched idref values during XML creation for id(s): %s"
                    % ",".join(str(x) for x in self.idList))

    def __init__(self, idList):
        self.idList = idList

class XType(object):

    def _isComplex(self):
        attributes = self._getAttributes()
        for key, val in self.pythonType.__dict__.iteritems():
            if (not isinstance(val, (types.FunctionType, types.MethodType))
                  and not key.startswith('_')
                  and key != 'text'
                  and key not in attributes):
                return True

        return False

    def _getAttributes(self):
        xobjMetadata = getattr(self.pythonType, '_xobj', None)
        if xobjMetadata is None:
            return {}
        return xobjMetadata.attributes

    def __init__(self, pythonType, forceList = False):
        self.pythonType = pythonType
        self.forceList = forceList

class XUnionType(XType):

    def __init__(self, d):
        self.d = {}
        for key, val in d.iteritems():
            self.d[key] = XTypeFromXObjectType(val)
            self.d[key].forceList = True

def XTypeFromXObjectType(xObjectType):

    if xObjectType == str or xObjectType == object:
        # Basic object's are static, making instantiating one pretty worthless.
        return XType(XObj)
    elif xObjectType == int:
        return XType(XObjInt)
    elif xObjectType == long:
        return XType(XObjLong)
    elif xObjectType == float:
        return XType(XObjFloat)
    elif xObjectType == Decimal:
        return XType(XObjFloat)
    elif type(xObjectType) == list:
        assert(len(xObjectType) == 1)
        return XType(XTypeFromXObjectType(xObjectType[0]).pythonType,
                     forceList = True)

    return XType(xObjectType)

class XObj(unicode):

    """
    Example class for all elements represented in XML. Subclasses of XObject
    can be used to specify how attributes and elements of the element are
    represented in python. For example, parsing the XML:

        <element intAttr="10" strAttr="hello">
           <subelement>Value</subelement>
        </element>

    using this class:

        class Element(xobj.XObj):

            intAttr = int                       # force an int
            subelement = [ str ]                # force a list

    (which is done with doc = xobj.parse("---xml string---",
                                    typeMap = { 'element' : Element } )
    will result in the object tree:

        doc.element.intAttr = 10
        doc.element.strAttr = 'hello'
        doc.element.subelement.text = [ 'Value' ]

    """

    def __repr__(self):
        if self:
            return unicode.__repr__(self)
        else:
            return object.__repr__(self)

class XObjInt(int):
    pass

class XObjFloat(float):
    pass

class XObjLong(long):
    pass

class XObjMetadata(object):

    __slots__ = [ 'elements', 'attributes', 'tag', 'text' ]

    def __init__(self, elements = None, attributes = None, text = None,
                 tag = None):
        if elements:
            self.elements = list(elements)
        else:
            self.elements = []

        if attributes:
            if isinstance(attributes, dict):
                self.attributes = attributes.copy()
            else:
                self.attributes = dict( (x, None) for x in attributes )
        else:
            self.attributes = dict()

        self.tag = tag
        self.text = text

    def copy(self):
        return self.__class__(elements=self.elements,
            attributes=self.attributes, text=self.text, tag=self.tag)

class XID(XObj):

    pass

class XIDREF(XObj):

    pass

def isMethod(func):
    return inspect.ismethod(func) or inspect.ismethoddescriptor(func)

def findPythonType(xobj, key):
    pc = xobj.__class__.__dict__.get(key, None)
    if pc is not None and not isMethod(pc):
        return pc

    md = getattr(xobj.__class__, '_xobj', None)
    if md is None:
        return None

    return md.attributes.get(key, None)

class ElementGenerator(object):

    def getElementTree(self, xobj, tag, parentElement = None, nsmap = {}):

        def addns(s):
            for short, long in nsmap.iteritems():
                if short and s.startswith(short + '_'):
                    s = '{' + long + '}' + s[len(short) + 1:]

            return s

        if xobj is None:
            return

        tag = addns(tag)

        if type(xobj) in (int, long, float, bool, Decimal):
            xobj = unicode(xobj)

        if type(xobj) == str:
            # Only simple ASCII str are allowed, otherwise it
            # *must* be a unicode object. This is consistent with ET
            # and lxml, but forcing it here makes a better error.
            xobj = xobj.decode('ascii')

        if type(xobj) == unicode:
            element = etree.SubElement(parentElement, tag, {})
            element.text = xobj
            return element

        if isinstance(xobj, etree._Element):
            if parentElement is not None:
                parentElement.append(xobj)
            return xobj

        if hasattr(xobj, '_xobj'):
            attrSet = xobj._xobj.attributes

            if xobj._xobj.tag is not None:
                tag = xobj._xobj.tag
                tag = addns(tag)
        else:
            attrSet = set()

        attrs = {}
        elements = {}

        if getattr(xobj, '__dict__',None) is None:
            # be tolerant of invalid input, ideally we would log this
            return
 
        for key, val in xobj.__dict__.iteritems():
            if key[0] != '_':
                if key in attrSet:
                    pythonType = findPythonType(xobj, key)

                    if pythonType and issubclass(pythonType, XIDREF):
                        idVal = getattr(val, 'id', None)
                        if idVal is None:
                            # look for an id name in a different namespace
                            for idKey, idType in (
                                        val.__dict__.iteritems()):
                                if idKey.endswith('_id'):
                                    idVal = getattr(val, idKey)
                                    break

                        if idVal is None:
                            # look for something prorotyped XID
                            for idKey, idType in (
                                        val.__class__.__dict__.iteritems()):
                                if (idKey[0] != '_' and type(idType) == type
                                                and issubclass(idType, XID)):
                                    idVal = getattr(val, idKey)
                                    break

                        if idVal is None:
                            raise XObjSerializationException(
                                    'No id found for element referenced by %s'
                                    % key)
                        val = idVal
                        self.idsNeeded.add(idVal)
                    elif (key == 'id' or key.endswith('_id') or
                          (pythonType and issubclass(pythonType, XID))):
                        self.idsFound.add(val)

                    if val is not None:
                        key = addns(key)
                        attrs[key] = unicode(val)
                else:
                    l = elements.setdefault(key, [])
                    if type(val) == list:
                        l.extend(val)
                    else:
                        l.append(val)

        orderedElements = []
        
        if hasattr(xobj, '_xobj'):
            for name in xobj._xobj.elements:
                for val in elements.get(name, []):
                    orderedElements.append((name, val))
            for name in (set(elements) - set(xobj._xobj.elements)):
                for val in elements[name]:
                    orderedElements.append((name, val))
            attrSet = xobj._xobj.attributes
            if type(attrSet) != dict:
                # allow for ordered dictionaries
                orderedAttrs = xobj._xobj.attributes.__class__()
                for key in attrSet.keys():
                    if key in attrs:
                        orderedAttrs[key] = attrs.pop(key)
                for key in attrs.keys():
                    orderedAttrs[key] = attrs[key]
                attrs = orderedAttrs
        else:
            orderedElements = sorted(elements.iteritems())

        if parentElement is None:
            element = etree.Element(tag, attrs, nsmap = nsmap)
        else:
            element = etree.SubElement(parentElement, tag, attrs)


        if isinstance(xobj, basestring) and xobj:
            element.text = unicode(xobj)
        elif (hasattr(xobj, '_xobj') and xobj._xobj.text 
              and not orderedElements):
            # only add text if we don't have elements
            # can't have both.
            element.text = xobj._xobj.text

        for key, val in orderedElements:
            if val is not None:
                if type(val) == list:
                    for subval in val:
                        self.getElementTree(subval, key,
                                            parentElement = element,
                                            nsmap = nsmap)
                else:
                    self.getElementTree(val, key, parentElement = element,
                                        nsmap = nsmap)

        return element

    def tostring(self, prettyPrint = True, xml_declaration = True):
        return etree.tostring(self.element, pretty_print = prettyPrint,
                              encoding = 'UTF-8',
                              xml_declaration = xml_declaration)

    def __init__(self, xobj, tag, nsmap = {}, schema = None):
        self.idsNeeded = set()
        self.idsFound = set()
        self.element = self.getElementTree(xobj, tag, nsmap = nsmap)
        if (self.idsNeeded - self.idsFound):
            raise UnmatchedIdRef(self.idsNeeded - self.idsFound)

        if schema:
            schema.assertValid(self.element)

class Document(object):

    nameSpaceMap = {}
    typeMap = {}

    def __init__(self, schema = None):
        self._idsNeeded = []
        self._dynamicClassDict = {}
        self._ids = {}
        self.__explicitNamespaces = False
        self.__xmlNsMap = {}
        self._xobj = XObjMetadata()
        self.__schema = schema

    def toxml(self, nsmap = {}, prettyPrint = True, xml_declaration = True):
        items = sorted((key, value) for (key, value) in self.__dict__.items()
                if not key.startswith('_'))
        if not items:
            raise RuntimeError("Document has no root element.")
        rootName, rootValue = items[0]

        if nsmap:
            map = nsmap
        else:
            map = self.__xmlNsMap

        if self.__explicitNamespaces:
            map = map.copy()
            del map[None]

        gen = ElementGenerator(rootValue, rootName,
                nsmap=map, schema=self.__schema)
        return gen.tostring(prettyPrint = prettyPrint,
                            xml_declaration = xml_declaration)

    def fromElementTree(self, xml, rootXClass = None, nameSpaceMap = {},
                        unionTags = {}):

        def nsmap(s):
            for short, long in self.__xmlNsMap.iteritems():
                if self.__explicitNamespaces and short is None:
                    continue

                if s.startswith('{' + long + '}'):
                    if short:
                        s = short + '_' + s[len(long) + 2:]
                    else:
                        s = s[len(long) + 2:]

            return s

        def setAttribute(xobj, doc, key, val):
            expectedType = findPythonType(xobj, key)
            if expectedType is None:
                expectedType = doc.typeMap.get(key, None)

            if expectedType:
                expectedXType = XTypeFromXObjectType(expectedType)
                if (key == 'id' or key.endswith('_id') or
                            issubclass(expectedXType.pythonType, XID)):
                    doc._ids[val] = xobj
                elif issubclass(expectedXType.pythonType, XIDREF):
                    doc._idsNeeded.append((xobj, key, val))
                    return
                else:
                    val = expectedXType.pythonType(val)
            else:
                if (key == 'id' or key.endswith('_id')):
                    doc._ids[val] = xobj

                expectedXType = None

            addAttribute(xobj, key, val, xType = expectedXType)

        def addAttribute(xobj, key, val, xType = None):
            setItem(xobj, key, val, xType)
            if key not in xobj._xobj.attributes and (key not in
                                                    xobj._xobj.elements):
                # preserve any type information we copied in, but only if it
                # wasn't previously defined (either element or attribute).
                xobj._xobj.attributes[key] = None

        def addElement(xobj, key, val, xType = None):
            setItem(xobj, key, val, xType = xType)
            if key not in xobj._xobj.elements and (key not in
                                                    xobj._xobj.attributes):
                # preserve any type information we copied in, but only if it
                # wasn't previously defined (either element or attribute).
                xobj._xobj.elements.append(key)

        def setItem(xobj, key, val, xType = None):
            current = getattr(xobj, key, None)
            if xType:
                if xType.forceList:
                    # force the item to be a list, and use the type inside of
                    # this list as the type of elements of the list
                    if key not in xobj.__dict__:
                        current = []
                    setattr(xobj, key, current)
                # Avoid turning things into lists that are not defined as lists
                # in the type map.
                elif not isinstance(xobj, XObj):
                    setattr(xobj, key, val)
                    return

            if xobj.__dict__.get(key, None) is None:
                # This has not yet been set in the instance (because it's
                # missing) or it's been set to None (because we think we don't
                # have this value but it's actually an idref being filled in
                # later)
                setattr(xobj, key, val)
            elif type(current) == list:
                current.append(val)
            else:
                setattr(xobj, key, [ current, val ])

        def parseElement(element, parentXType = None, parentXObj = None,
                         parentUnionTags = {}):
            # handle the text for this tag
            if element.getchildren():
                # It's a complex type, so the text is meaningless.
                text = None
            else:
                text = element.text

            tag = nsmap(element.tag)

            if tag in self._dynamicClassDict:
                thisXType = self._dynamicClassDict[tag]
            else:
                if parentXObj is None:
                    parentXObj = self
                    parentXType = XTypeFromXObjectType(self.__class__)

                thisXType = None
                thisPyType = None

                if parentXType:
                    if tag in parentUnionTags:
                        thisPyType = parentUnionTags[tag][1].pythonType
                    else:
                        thisPyType = getattr(parentXType.pythonType, tag, None)

                if not thisPyType:
                    thisPyType = self.typeMap.get(tag, None)

                if thisPyType:
                    thisXType = XTypeFromXObjectType(thisPyType)

                self._dynamicClassDict[tag] = thisXType

            unionTags = {}
            if thisXType:
                if text is not None and thisXType._isComplex():
                    # This type has child elements, so it's complex, so
                    # the text is meaningless.
                    text = None

                if text:
                    # If we got here, it's either a simple type, or we have
                    # attributes and text.
                    if thisXType._getAttributes():
                        xobj = thisXType.pythonType()
                        # We need to create a dedicated metadata object. It
                        # really is unfortunate that we can't share the
                        # attributes and elements lists among all objects of
                        # the same class.
                        xobj._xobj = XObjMetadata(
                            tag=xobj._xobj.tag,
                            attributes=xobj._xobj.attributes,
                            elements=xobj._xobj.elements,
                            text=text)
                    else:
                        xobj = thisXType.pythonType(text)
                else:
                    xobj = thisXType.pythonType()

                # look for unions
                for key, val in thisXType.pythonType.__dict__.iteritems():
                    if key[0] == '_': continue
                    if isinstance(val, list) and isinstance(val[0], dict):
                        ut = XUnionType(val[0])
                        for a, b in ut.d.iteritems():
                            unionTags[a] = (key, b)
            else:
                localTag = nsmap(element.tag)
                # create a subclass for this type
                NewClass = type(localTag + '_XObj_Type', (XObj,), {})
                self._dynamicClassDict[tag] = XType(NewClass)

                if text:
                    xobj = NewClass(text)
                else:
                    xobj = NewClass()

            if not hasattr(xobj, '_xobj'):
                xobj._xobj = XObjMetadata()

            if not xobj._xobj.tag:
                xobj._xobj.tag = tag

            initialized = set()

            # handle children
            for childElement in element.getchildren():
                if types.BuiltinFunctionType == type(childElement.tag):
                    # this catches comments. this is ugly.
                    continue

                # Initialize values that are defined to be lists in the type
                # map. This overrides any default values from instantiating the
                # instance.
                if childElement.tag not in initialized:
                    attr = getattr(xobj, childElement.tag, None)
                    if attr and isinstance(attr, list):
                        setattr(xobj, childElement.tag, list())
                    initialized.add(childElement.tag)

                child = parseElement(childElement, parentXType = thisXType,
                                     parentXObj = xobj,
                                     parentUnionTags = unionTags)

            # handle attributes
            for (key, val) in element.items():
                key = nsmap(key)
                setAttribute(xobj, self, key, val)

            # Backfill any attributes that were not in the XML with None.
            for key, val in xobj._xobj.attributes.iteritems():
                key = nsmap(key)
                # Do not backfill values that are XIDREFs, they will be
                # handled later.
                if val is not None and issubclass(val, XIDREF):
                    continue
                if not hasattr(xobj, key):
                    setAttribute(xobj, self, key, val)

            # anything which is the same as in the class wasn't set in XML, so
            # set it to None
            # We even set lists to None as it is important to be
            # able to distinguish between not specifying a list and
            # specifying the empty list.
            for key, val in xobj.__class__.__dict__.items():
                if key[0] == '_': continue
                if getattr(xobj, key) == val:
                    setattr(xobj, key, None)

            if parentXObj is not None:
                if tag in parentUnionTags:
                    xobj._xobj.tag = tag
                    addElement(parentXObj, parentUnionTags[tag][0], xobj,
                                           parentUnionTags[tag][1])
                else:
                    addElement(parentXObj, tag, xobj, thisXType)

            return xobj

        rootElement = xml.getroot()

        if not self.nameSpaceMap:
            self.__xmlNsMap = rootElement.nsmap
        else:
            fullNsMap = dict((y,x) for (x,y) in self.nameSpaceMap.iteritems())
            for short, long in rootElement.nsmap.iteritems():
                if long not in fullNsMap:
                    fullNsMap[long] = short

            self.__xmlNsMap = dict((y,x) for (x,y) in fullNsMap.iteritems())

        self.__explicitNamespaces = False
        if None in self.__xmlNsMap:
            if [ y for (x, y) in self.__xmlNsMap.iteritems()
                    if x and y == self.__xmlNsMap[None] ]:
                self.__explicitNamespaces = True

        parseElement(rootElement)

        for (xobj, tag, theId) in self._idsNeeded:
            if theId not in self._ids:
                raise XObjIdNotFound(theId)
            addAttribute(xobj, tag, self._ids[theId])

class XObjParseException(Exception):

    pass

class XObjIdNotFound(XObjParseException):

    def __str__(self):
        return "XML ID '%s' not found in document" % self.theId

    def __init__(self, theId):
        self.theId = theId

class XObjSerializationException(Exception):

    pass

def parsef(f, schemaf = None, documentClass = Document, typeMap = {}):
    if schemaf:
        schemaObj = etree.XMLSchema(file = schemaf)
    else:
        schemaObj = None

    if typeMap:
        newClass = type('XObj_Dynamic_Document', (documentClass,),
                        { 'typeMap' : typeMap})
        document = newClass(schema = schemaObj)
    else:
        document = documentClass(schema = schemaObj)

    parser = etree.XMLParser(schema = schemaObj)
    xml = etree.parse(f, parser)
    document.fromElementTree(xml)

    return document

def parse(s, schemaf = None, documentClass = Document, typeMap = {}):
    s = StringIO(s)
    return parsef(s, schemaf, documentClass = documentClass, typeMap = typeMap)

def toxml(xobj, tag = None, prettyPrint = True, xml_declaration = True,
          schemaf = None, nsmap = {}):
    if schemaf:
        schemaObj = etree.XMLSchema(file = schemaf)
    else:
        schemaObj = None

    if tag is None and hasattr(xobj, '_xobj') and xobj._xobj.tag is None:
        raise TypeError, 'must specify a tag'

    gen = ElementGenerator(xobj, tag, schema = schemaObj, nsmap = nsmap)

    return gen.tostring(prettyPrint = prettyPrint,
                        xml_declaration = xml_declaration)
