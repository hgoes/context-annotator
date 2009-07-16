import gobject
import gtk
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas

class DisplayMeta(gobject.GObjectMeta):
    def __init__(cls,*kwds):
        gobject.GObjectMeta.__init__(cls,*kwds)
        cls.__gtype_name__ = cls.__name__
        gobject.signal_new('cursor-move', cls,
                           gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_DOUBLE,gobject.TYPE_DOUBLE))
        gobject.type_register(cls)

class Display(FigureCanvas):
    __metaclass__ = DisplayMeta
    def __init__(self,par,src,model,state):
        self.src = src
        self.model = model
        self.click_handler = par
        self.__state = state
        state.connect('selection-changed',self.update_spanner)
        state.connect('selection-removed',self.remove_spanner)
        xb = src.xBounds()
        yb = src.yBounds()
        figure = Figure(dpi=100)
        self.plot = figure.add_subplot(111,xbound=xb,ybound=yb,autoscale_on=False)
        self.plot.plot_date(src.getX(),src.getY(),'-')
        self.spanner = self.plot.axvspan(xb[0],xb[1],alpha=0.5)
        self.ctx_spanners = dict()
        FigureCanvas.__init__(self,figure)
        self.mpl_connect('button_press_event',self.on_press)
        self.mpl_connect('button_release_event',self.on_release)
        self.mpl_connect('motion_notify_event',self.on_move)
        model.connect('annotation-added',self.notice_annotation)
        model.connect('annotation-removed',self.notice_annotation_removal)
        model.connect('annotation-changed',self.notice_annotation_change)

        for (id,color,boundl,boundr) in model.annotations():
            self.notice_annotation(model,id,color,boundl,boundr)
    def update_spanner(self,state,vall,valr):
        self.remove_spanner(state)
        if vall != valr:
            self.spanner = self.plot.axvspan(vall,valr,alpha=0.5)
        self.draw_idle()
    def remove_spanner(self,state):
        if self.spanner is not None:
            self.spanner.remove()
            self.spanner = None
    def update_zoom(self,policy):
        self.plot.set_xlim(*policy.get_bounds())
        self.plot.get_xaxis().set_major_locator(policy.get_locator())
        self.draw_idle()
    def _border_offset(self):
        (startx,starty) = self.figure.get_axes()[0].transData.inverted().transform_point((0,0))
        (endx,endy)     = self.figure.get_axes()[0].transData.inverted().transform_point((10,10))
        return endx-startx
    def on_press(self,event):
        #print (event.x,self.figure.get_axes()[0].transData.transform_point((event.xdata,event.ydata)))
        if event.xdata is not None and event.ydata is not None:
            if event.guiEvent is None:
                time = 0
            else:
                time = event.guiEvent.get_time()
            self.__state.button_down(self,event.button,event.xdata,self._border_offset(),time)
    def on_release(self,event):
        if event.xdata != None and event.ydata != None:
            if event.guiEvent is None:
                time = 0
            else:
                time = event.guiEvent.get_time()
            self.__state.button_up(self,event.button,event.xdata,self._border_offset(),time)
    def on_move(self,event):
        if event.xdata != None and event.ydata != None:
            if event.guiEvent is None:
                time = 0
            else:
                time = event.guiEvent.get_time()
            self.__state.move(self,event.xdata,time)
    def notice_annotation(self,model,id,col,start,end):
        self.ctx_spanners[id] = self.plot.axvspan(start,end,alpha=0.3,facecolor=col)
        self.draw_idle()
    def notice_annotation_removal(self,model,id):
        self.ctx_spanners[id].remove()
        del self.ctx_spanners[id]
        self.draw_idle()
    def notice_annotation_change(self,model,id,ctx,col,start,end):
        self.ctx_spanners[id].remove()
        self.ctx_spanners[id] = self.plot.axvspan(start,end,alpha=0.3,facecolor=col)
        self.draw_idle()
