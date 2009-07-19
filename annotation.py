"""
The data model
==============
"""
import gobject
import calendar
import datetime
from matplotlib.dates import date2num,num2date
from timezone import UTC

class AnnotationsMeta(gobject.GObjectMeta):
    def __init__(cls,*kwds):
        gobject.GObjectMeta.__init__(cls,*kwds)
        cls.__gtype_name__ = cls.__name__
        gobject.signal_new('annotation-added', cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_INT,gobject.TYPE_STRING,gobject.TYPE_DOUBLE,gobject.TYPE_DOUBLE))
        gobject.signal_new('annotation-removed',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_INT,))
        gobject.signal_new('context-added',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,gobject.TYPE_STRING))
        gobject.signal_new('context-removed',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,))
        gobject.signal_new('annotation-changed',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_INT,gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_DOUBLE,gobject.TYPE_DOUBLE))
        gobject.type_register(cls)


class Annotations(gobject.GObject):
    """
    Provides the data model for annotations.
    It keeps track of all annotations and informs listeners if something changed.
    
    +---------------------+-------------------+-------------------------+
    |Signal               | Signature         | Description             |
    +=====================+===================+=========================+
    |"annotation-added"   | :class:`int`,     | Called with id, color,  |
    |                     | :class:`str`,     | start-time and end-time |
    |                     | :class:`float`,   | when a new annotation   |
    |                     | :class:`float`    | is added.               |
    +---------------------+-------------------+-------------------------+
    |"annotation-removed" | :class:`int`      | Called with the id of   |
    |                     |                   | an annotation that has  |
    |                     |                   | been removed.           |
    +---------------------+-------------------+-------------------------+
    |"annotation-changed" | :class:`int`,     | Called with the id,     |
    |                     | :class:`str`,     | context-name, color,    |
    |                     | :class:`str`,     | start- and end-time of  |
    |                     | :class:`float`,   | an annotation that has  |
    |                     | :class:`float`    | been changed.           |
    +---------------------+-------------------+-------------------------+
    |"context-added"      | :class:`str`,     | Called with the name and|
    |                     | :class:`str`      | color of a context that |
    |                     |                   | has been added.         |
    +---------------------+-------------------+-------------------------+
    | "context-removed"   | :class:`str`      | Called with the name of |
    |                     |                   | a context that has been |
    |                     |                   | removed.                |
    +---------------------+-------------------+-------------------------+
    """
    __metaclass__ = AnnotationsMeta
    def __init__(self):
        gobject.GObject.__init__(self)
        self.__contexts = dict()
        self.__annotations = dict()
        self.__counter = 0
        self.__colors = ['red','green','yellow','orange']
    def add_annotation(self,ctx,boundl,boundr):
        """
        :param ctx: The context name
        :type ctx: :class:`str`
        :param boundl: The start time
        :type boundl: :class:`float`
        :param boundr: The end time
        :type boundr: :class:`float`
        :returns: The id of the new annotation
        :rtype: :class:`int`
        
        Adds a new annotation for the context *ctx* and the start time *boundl* and end time *boundr*. """
        if ctx not in self.__contexts:
            self.add_context(ctx)
        id = self.__counter
        self.__counter += 1
        (color,entries) = self.__contexts[ctx]
        self.__annotations[id] = (ctx,boundl,boundr)
        entries.add(id)
        self.emit('annotation-added',id,color,boundl,boundr)
        return id
    def remove_annotation(self,id):
        """
        :param id: The id of the annotation to be removed
        :type id: :class:`int`
        
        Removes an annotation from the model. """
        (ctx,boundl,boundr) = self.__annotations[id]
        (color,entries) = self.__contexts[ctx]
        entries.remove(id)
        del self.__annotations[id]
        self.emit('annotation-removed',id)
    def add_context(self,ctx):
        """
        :param ctx: Name of the new context
        :type ctx: :class:`str`
        :returns: Generated color for the context
        :rtype: :class:`str`
        
        Adds a new context type to the model and generates a color for it. If the context already exists the color is looked up."""
        if ctx not in self.__contexts:
            color = self.free_color()
            if color is None:
                raise "HALP! I CAN'T HAZ COLOR"
            self.__contexts[ctx] = (color,set())
            self.emit('context-added',ctx,color)
            return color
        else:
            (color,entries) = self.__contexts[ctx]
            return color
    def free_color(self):
        for col in self.__colors:
            avail = True
            for (ccol,entries) in self.__contexts.itervalues():
                if ccol == col:
                    avail = False
                    break
            if avail:
                return col
        return None
    def remove_context(self,ctx):
        """
        :param ctx: The name of the context
        :type ctx: :class:`str`

        Removes a context from the model. The color used by the context becomes available to new contexts. """
        if ctx not in self.__contexts:
            return
        (color,entries) = self.__contexts[ctx]
        for id in entries:
            del self.__annotations[id]
            self.emit('annotation-removed',id)
        self.emit('context-removed',ctx)
        del self.__contexts[ctx]
    def find_annotation(self,x):
        """
        :param x: The time where to search
        :type x: :class:`float`
        :returns: A list of all annotations that include the timestamp
        :rtype: \[ :class:`int` \]

        Finds all annotations that include a given timestamp. If the timestamp lies within no annotation, it returns :const:`[]`."""
        hits = []
        for (id,(ctx,boundl,boundr)) in self.__annotations.iteritems():
            if x>=boundl and x<=boundr:
                hits.append(id)
        return hits
    def get_annotation(self,id):
        """
        :param id: The id of the annotation
        :type id: :class:`int`
        :returns: Context name, color, start-time and end-time of the annotation
        :rtype: (:class:`str`, :class:`str`, :class:`float`, :class:`float`)"""
        (ctx,boundl,boundr) = self.__annotations[id]
        (color,entries) = self.__contexts[ctx]
        return (ctx,color,boundl,boundr)
    def contexts(self):
        """
        :returns: An iterator over name and colors of all contexts in the model
        :rtype: :class:`iterator`"""
        return((name,color) for name,(color,entries) in self.__contexts.iteritems())
    def annotations(self):
        """
        :returns: An iterator over id, color, start-time and end-time of all annotations in the model.
        :rtype: :class:`iterator`"""
        return((id,self.__contexts[ctx][0],boundl,boundr) for (id,(ctx,boundl,boundr)) in self.__annotations.iteritems())
    def bounds(self):
        """
        :rtype: (:class:`float`, :class:`float`)
        
        Calculate the minimal start-time and maximal end-time of all annotations."""
        l = None
        r = None
        for (ctx,boundl,boundr) in self.__annotations.itervalues():
            if l is None or boundl < l:
                l = boundl
            if r is None or boundr > r:
                r = boundr
        return (l,r)
    def clear(self):
        """
        Removes all annotations and contexts from the model. """
        for i in self.__annotations:
            self.emit('annotation-removed',i)
        for c in self.__contexts:
            self.emit('context-removed',c)
        self.__annotations = dict()
        self.__contexts = dict()
        self.__counter = 0
    def find_boundings(self,x,exclude=None):
        """
        :param x: The x-position
        :type x: :class:`float`
        :param exclude: A context id not to consider or :const:`None` to consider all
        :type exclude: :class:`int` or :class:`None`
        :returns: The two nearest annotations as a tuple. Each can be :const:`None` if there is no annotation to the left or right.
        :rtype: (:class:`int`, :class:`int`)
        
        Given a x-position, it finds the two annotations nearest to the position on the left and right.
        """
        curl = None
        curr = None
        for (id,(ctx,boundl,boundr)) in self.__annotations.iteritems():
            if id is exclude:
                continue
            if boundl > x and (curr is None or curr[1] > boundl):
                curr = (id,boundl)
            if boundr < x and (curl is None or curl[1] < boundr):
                curl = (id,boundr)
        return (curl,curr)
    def update_annotation(self,id,boundl,boundr):
        """
        :param id: The id of the annotation
        :type id: :class:`int`
        :param boundl: The new start-time for the annotation
        :type boundl: :class:`float`
        :param boundr: The new end-time for the annotation
        :type boundr: :class:`float`

        Changes an annotation to new time-bounds. """
        (ctx,oldl,oldr) = self.__annotations[id]
        self.__annotations[id] = (ctx,boundl,boundr)
        (color,entries) = self.__contexts[ctx]
        self.emit('annotation-changed',id,ctx,color,boundl,boundr)
    def write(self,fn):
        """
        :param fn: The filename to write to
        :type fn: :class:`str`
        
        Writes the annotations to a file. The format is

        <context-name> <start-time> <end-time>
        
        The timestamps are seconds since 1.1.1970 (UNIX timestamps)"""
        utc = UTC()
        with open(fn,'w') as h:
            for (ctx,boundl,boundr) in self.__annotations.itervalues():
                h.write(ctx+" "+str(calendar.timegm(num2date(boundl,utc).utctimetuple()))+" "
                        +str(calendar.timegm(num2date(boundr,utc).utctimetuple()))+"\n")
    def read(self,fn):
        """
        :param fn: The filename from which to read
        :type fn: string

        The inverse of :func:`write`."""
        self.clear()
        utc = UTC()
        with open(fn,'r') as h:
            for ln in h:
                (name,start,end) = ln.split()
                self.add_annotation(name,
                                    date2num(datetime.datetime.utcfromtimestamp(float(start))),
                                    date2num(datetime.datetime.utcfromtimestamp(float(end))))
