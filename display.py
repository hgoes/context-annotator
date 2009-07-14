from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas

class Display(FigureCanvas):
    def __init__(self,par,src,model):
        self.src = src
        self.click_handler = par
        xb = src.xBounds()
        yb = src.yBounds()
        self.figure = Figure(figsize=(5,4),dpi=100)
        self.plot = self.figure.add_subplot(111,xbound=xb,ybound=yb,autoscale_on=False)
        self.plot.plot_date(src.getX(),src.getY(),'-')
        self.spanner = self.plot.axvspan(xb[0],xb[1],alpha=0.5)
        self.ctx_spanners = dict()
        FigureCanvas.__init__(self,self.figure)
        self.mpl_connect('button_press_event',self.on_press)
        self.mpl_connect('button_release_event',self.on_release)
        self.mpl_connect('motion_notify_event',self.on_move)
        model.connect('annotation-added',self.notice_annotation)
        model.connect('annotation-removed',self.notice_annotation_removal)

        for (id,color,boundl,boundr) in model.annotations():
            self.notice_annotation(model,id,color,boundl,boundr)
    def update_spanner(self,vall,valr):
        if self.spanner != None:
            self.spanner.remove()
            self.spanner = None
        if vall != valr:
            self.spanner = self.plot.axvspan(vall,valr,alpha=0.5)
        self.draw_idle()
    def update_zoom(self,policy):
        self.plot.set_xlim(*policy.get_bounds())
        self.plot.get_xaxis().set_major_locator(policy.get_locator())
        self.draw_idle()
    def on_press(self,event):
        if event.xdata != None and event.ydata != None:
            if event.button == 1:
                self.click_handler.bound_change_start(event.xdata)
            elif event.button == 3:
                self.click_handler.select(event.xdata,event.guiEvent.get_time(),self)
    def on_release(self,event):
        if event.xdata != None and event.ydata != None:
            if event.button == 1:
                self.click_handler.bound_change_end(event.xdata)
    def on_move(self,event):
        if event.xdata != None and event.ydata != None:
            self.click_handler.bound_change_update(event.xdata)
    def notice_annotation(self,model,id,col,start,end):
        self.ctx_spanners[id] = self.plot.axvspan(start,end,alpha=0.3,facecolor=col)
        self.draw_idle()
    def notice_annotation_removal(self,model,id):
        self.ctx_spanners[id].remove()
        del self.ctx_spanners[id]
        self.draw_idle()
