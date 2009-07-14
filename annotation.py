import gobject

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
        gobject.type_register(cls)

class Annotations(gobject.GObject):
    __metaclass__ = AnnotationsMeta
    def __init__(self):
        gobject.GObject.__init__(self)
        self.__contexts = dict()
        self.__annotations = dict()
        self.__counter = 0
        self.__colors = ['red','green','yellow','orange']
    def add_annotation(self,ctx,boundl,boundr):
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
        (ctx,boundl,boundr) = self.__annotations[id]
        (color,entries) = self.__contexts[ctx]
        entries.remove(id)
        del self.__annotations[id]
        self.emit('annotation-removed',id)
    def add_context(self,ctx):
        if ctx not in self.__contexts:
            color = self.free_color()
            if color is None:
                raise "HALP! I CAN'T HAZ COLOR"
            self.__contexts[ctx] = (color,set())
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
        (color,entries) = self.__contexts[ctx]
        for id in entries:
            del self.__annotations[id]
            self.emit('annotation-removed',id)
        del self.__contexts[ctx]
    def find_annotation(self,x):
        hits = []
        for (id,(ctx,boundl,boundr)) in self.__annotations.iteritems():
            if x>=boundl and x<=boundr:
                hits.append(id)
        return hits
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
