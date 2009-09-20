"""
The input state
===============
"""
import gobject
from matplotlib.dates import num2date

class Viewing:
    """
    :param par: The parent container
    :type par: :class:`InputState`
    
    The default state. The user hasn't done anything and we're waiting for an action. """
    def __init__(self,par):
        self.parent = par
    def _get_limits(self,x,exclude=None):
        (limitl,limitr) = self.parent.model.find_boundings(x,exclude)
        if limitl is not None:
            limitl = limitl[1]
        if limitr is not None:
            limitr = limitr[1]
        return (limitl,limitr)
    def button_down(self,display,but,x,border_offset,time):
        if but==1:
            ann = self.parent.model.find_annotation(x)
            if len(ann) == 0:
                limitl,limitr = self._get_limits(x)
                return Selecting(self.parent,x,limitl,limitr)
            else:
                ctx,col,boundl,boundr = self.parent.model.get_annotation(ann[0])
                limitl,limitr = self._get_limits(x,ann[0])
                if boundl+border_offset > x: #Left border
                    return Resizing(self.parent,ann[0],False,x-boundl,boundr,limitl)
                elif boundr-border_offset < x: #Right border
                    return Resizing(self.parent,ann[0],True,x-boundr,boundl,limitr)
                else:
                    return Dragging(self.parent,ann[0],boundr-boundl,x-boundl,limitl,limitr)
        elif but==3:
            if self.parent.selection is not None:
                boundl = self.parent.selection[0]
                boundr = self.parent.selection[1]
                if x > boundl and x < boundr:
                    self.parent.emit('select-selection',display,boundl,boundr,time)
                    return self
            ann = self.parent.model.find_annotation(x)
            if len(ann) != 0:
                self.parent.emit('select-annotation',display,ann[0],time)
        return self
    def button_up(self,display,but,x,border_offset,time):
        return self
    def move(self,display,x,time):
        self.parent.set_message(num2date(x).strftime("%c, %fus"))
        return self

class Limited:
    def _limit(self,x):
        if self.limitl is not None and x < self.limitl:
            return self.limitl
        elif self.limitr is not None and x > self.limitr:
            return self.limitr
        else:
            return x

class Selecting(Limited):
    """
    :param par: The parent container
    :type par: :class:`InputState`
    :param x: The coordinate where the user started selecting
    :type x: :class:`float`
    :param limitl: The left-side limit of the selection or :const:`None` if there is no limit
    :type limitl: :class:`float`
    :param limitr: The right-side limit of the selection or :const:`None` if there is no limit
    :type limitr: :class:`float`
    
    The user has begun selecting a region. Waiting until she/he releases the mouse."""
    def __init__(self,par,x,limitl,limitr):
        self.parent = par
        self.start = x
        self.limitl = limitl
        self.limitr = limitr
    def _update(self,x):
        x = self._limit(x)
        if x < self.start:
            status = (x,self.start)
        else:
            status = (self.start,x)
        self.parent.set_message(num2date(status[0]).strftime("%c, %fus")+" - "+num2date(status[1]).strftime("%c, %fus"))
        self.parent.set_selection(status)
    def button_down(self,display,but,x,border_offset,time):
        return self
    def button_up(self,display,but,x,border_offset,time):
        self._update(x)
        return Viewing(self.parent)
    def move(self,display,x,time):
        self._update(x)
        return self

class Dragging(Limited):
    """
    :param par: The parent container
    :type par: :class:`InputState`
    :param id: The id of the annotation
    :type id: :class:`int`
    :param width: The width of the annotation
    :type width: :class:`float`
    :param drag_offset: The offset from the left border of the annotation where the user clicked
    :type drag_offset: :class:`float`
    :param limitl: The left-side limit of the dragging operation, or :const:`None` if there's none
    :type limitl: :class:`float`
    :param limitr: The right-side limit of the dragging operation, or :const:`None` if there's none
    :type limitr: :class:`float`
    
    The user begun to drag an annotation around. We're waiting for him/her to release the mouse. """
    def __init__(self,par,id,width,drag_offset,limitl,limitr):
        self.parent = par
        self.id = id
        self.width = width
        self.offset = drag_offset
        if limitl is None:
            self.limitl = None
        else:
            self.limitl = limitl+drag_offset
        if limitr is None:
            self.limitr = None
        else:
            self.limitr = limitr-width+drag_offset
        par.set_selection(None)
    def _update(self,x):
        x = self._limit(x)
        boundl = x-self.offset
        boundr = x-self.offset+self.width
        self.parent.set_message(num2date(boundl).strftime("%c, %fus")+" - "+num2date(boundr).strftime("%c, %fus"))
        self.parent.model.update_annotation(self.id,boundl,boundr)
    def button_down(self,display,but,x,border_offset,time):
        return self
    def button_up(self,display,but,x,border_offset,time):
        self._update(x)
        return Viewing(self.parent)
    def move(self,display,x,time):
        self._update(x)
        return self

class Resizing(Limited):
    """
    :param par: The parent container
    :type par: :class:`InputState`
    :param id: The id of the annotation that is being resized
    :type id: :class:`int`
    :param which: Which side of the annotation is dragged: :const:`False` for left, :const:`True` for right
    :type which: :class:`bool`
    :param drag_offset: The offset from the left border of the annotation where the user clicked
    :type drag_offset: :class:`float`
    :param other: The coordinate of the other side of the annotation
    :type other: :class:`float`
    :param limit: The limit on the resizing operation, :const:`None` if there is no limit
    :type limit: :class:`float`

    The user has clicked on the border of an annotation and thus is resizing the annotation.
    """
    def __init__(self,par,id,which,drag_offset,other,limit):
        self.parent = par
        self.id = id
        if which: #Right border
            self.limitl = other+drag_offset
            if limit is None:
                self.limitr = None
            else:
                self.limitr = limit+drag_offset
        else: #Left border
            if limit is None:
                self.limitl = None
            else:
                self.limitl = limit+drag_offset
            self.limitr = other+drag_offset
        self.offset = drag_offset
        self.which = which
        self.other = other
        par.set_selection(None)
    def _update(self,x):
        x = self._limit(x)
        if self.which:
            boundl = self.other
            boundr = x-self.offset
        else:
            boundl = x-self.offset
            boundr = self.other
        self.parent.set_message(num2date(boundl).strftime("%c, %fus")+" - "+num2date(boundr).strftime("%c, %fus"))
        self.parent.model.update_annotation(self.id,boundl,boundr)
    def move(self,display,x,time):
        self._update(x)
        return self
    def button_up(self,display,but,x,border_offset,time):
        self._update(x)
        return Viewing(self.parent)
    def button_down(self,display,but,x,border_offset,time):
        return self
    
class InputStateMeta(gobject.GObjectMeta):
    def __init__(cls,*kwds):
        gobject.GObjectMeta.__init__(cls,*kwds)
        cls.__gtype_name__ = cls.__name__
        gobject.signal_new('selection-changed', cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_DOUBLE,gobject.TYPE_DOUBLE))
        gobject.signal_new('selection-removed', cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ())
        gobject.signal_new('message-changed',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,))
        gobject.signal_new('select-selection',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_PYOBJECT,gobject.TYPE_DOUBLE,gobject.TYPE_DOUBLE,gobject.TYPE_INT))
        gobject.signal_new('select-annotation',cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_PYOBJECT,gobject.TYPE_INT,gobject.TYPE_INT))
        gobject.type_register(cls)

class InputState(gobject.GObject):
    """
    :param model: The model on which to operate
    :type model: :class:`annotation.Annotations`
    
    Represents the current state of input processing

    +---------------------+------------------------+-------------------------+
    |Signal               | Signature              | Description             |
    +=====================+========================+=========================+
    |"selection-changed"  |:class:`float`,         | Called whenever the user|
    |                     |:class:`float`          | selects an area. Gives  |
    |                     |                        | the time bounds as      |
    |                     |                        | parameter.              |
    +---------------------+------------------------+-------------------------+
    |"selection-removed"  |                        | Called when the         |
    |                     |                        | selection is removed.   |
    +---------------------+------------------------+-------------------------+
    |"message-changed"    |:class:`str`            | Called when there's a   |
    |                     |                        | new information for the |
    |                     |                        | user (e.g. statusbar).  |
    +---------------------+------------------------+-------------------------+
    |"select-selection"   |:class:`display.Display`| Called when the user    |
    |                     |, :class:`float`,       | right-clicks the        |
    |                     |:class:`float`,         | selected area in a      |
    |                     |:class:`int`            | certain display.        |
    +---------------------+------------------------+-------------------------+
    |"select-annotation"  |:class:`display.Display`| Called when the user    |
    |                     |, :class:`int`,         | right-clicks an         |
    |                     |:class:`int`            | annotation in a certain |
    |                     |                        | display.                |
    +---------------------+------------------------+-------------------------+
    
    .. attribute:: state
    
       Contains the current state of the input processing.
       Can be one of :class:`Viewing`, :class:`Selecting`, :class:`Dragging` or :class:`Resizing`
    """
    __metaclass__ = InputStateMeta
    def __init__(self,model):
        gobject.GObject.__init__(self)
        self.state = Viewing(self)
        self.model = model
        self.selection = None
    def set_selection(self,new):
        """
        :param new: The new selection as two time-bounds or :const:`None`
        :type new: :class:`None` or (:class:`float`, :class:`float`)

        Sets the selection to a new value. Informs listeners about this.
        """
        self.selection = new
        if new is None:
            self.emit('selection-removed')
        else:
            self.emit('selection-changed',new[0],new[1])
    def set_message(self,str):
        self.emit('message-changed',str)
    def button_down(self,display,but,x,border_offset,time):
        self.state = self.state.button_down(display,but,x,border_offset,time)
    def button_up(self,display,but,x,border_offset,time):
        self.state = self.state.button_up(display,but,x,border_offset,time)
    def move(self,display,x,time):
        self.state = self.state.move(display,x,time)
