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
        :type ctx: string
        :param boundl: The start time
        :type boundl: float
        :param boundr: The end time
        :type boundr: float
        :returns: The id of the new annotation
        :rtype: int
        
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
        :type id: int
        
        Removes an annotation from the model. """
        (ctx,boundl,boundr) = self.__annotations[id]
        (color,entries) = self.__contexts[ctx]
        entries.remove(id)
        del self.__annotations[id]
        self.emit('annotation-removed',id)
    def add_context(self,ctx):
        """
        :param ctx: Name of the new context
        :type ctx: string
        :returns: Generated color for the context
        :rtype: string
        
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
        if ctx not in self.__contexts:
            return
        (color,entries) = self.__contexts[ctx]
        for id in entries:
            del self.__annotations[id]
            self.emit('annotation-removed',id)
        self.emit('context-removed',ctx)
        del self.__contexts[ctx]
    def find_annotation(self,x):
        hits = []
        for (id,(ctx,boundl,boundr)) in self.__annotations.iteritems():
            if x>=boundl and x<=boundr:
                hits.append(id)
        return hits
    def get_annotation(self,id):
        (ctx,boundl,boundr) = self.__annotations[id]
        (color,entries) = self.__contexts[ctx]
        return (ctx,color,boundl,boundr)
    def contexts(self):
        return((name,color) for name,(color,entries) in self.__contexts.iteritems())
    def annotations(self):
        return((id,self.__contexts[ctx][0],boundl,boundr) for (id,(ctx,boundl,boundr)) in self.__annotations.iteritems())
    def bounds(self):
        l = None
        r = None
        for (ctx,boundl,boundr) in self.__annotations.itervalues():
            if l is None or boundl < l:
                l = boundl
            if r is None or boundr > r:
                r = boundr
        return (l,r)
    def clear(self):
        for i in self.__annotations:
            self.emit('annotation-removed',i)
        for c in self.__contexts:
            self.emit('context-removed',c)
        self.__annotations = dict()
        self.__contexts = dict()
        self.__counter = 0
    def find_boundings(self,x,exclude=None):
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
    def update_annotation(self,ind,boundl,boundr):
        (ctx,oldl,oldr) = self.__annotations[ind]
        self.__annotations[ind] = (ctx,boundl,boundr)
        (color,entries) = self.__contexts[ctx]
        self.emit('annotation-changed',ind,ctx,color,boundl,boundr)
    def write(self,fn):
        utc = UTC()
        with open(fn,'w') as h:
            for (ctx,boundl,boundr) in self.__annotations.itervalues():
                h.write(ctx+" "+str(calendar.timegm(num2date(boundl,utc).utctimetuple()))+" "
                        +str(calendar.timegm(num2date(boundr,utc).utctimetuple()))+"\n")
    def read(self,fn):
        self.clear()
        utc = UTC()
        with open(fn,'r') as h:
            for ln in h:
                (name,start,end) = ln.split()
                self.add_annotation(name,
                                    date2num(datetime.datetime.utcfromtimestamp(float(start))),
                                    date2num(datetime.datetime.utcfromtimestamp(float(end))))
