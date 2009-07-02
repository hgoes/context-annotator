import numpy as np
#import matplotlib.pyplot as plt
import gtk
import datetime
from matplotlib.figure import Figure
from matplotlib.dates import date2num,num2date,MinuteLocator

# uncomment to select /GTK/GTKAgg/GTKCairo
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
#from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvas

from sources import *

class Display(FigureCanvas):
    def __init__(self,par,src):
        self.src = src
        self.click_handler = par
        xb = src.xBounds()
        yb = src.yBounds()
        #print xb
        self.figure = Figure(figsize=(5,4),dpi=100)
        self.plot = self.figure.add_subplot(111,xbound=xb,ybound=yb,autoscale_on=False)
        self.plot.get_xaxis().set_major_locator(MinuteLocator())
        self.plot.plot_date(src.getX(),src.getY(),'-')
        self.spanner = self.plot.axvspan(xb[0],xb[1],alpha=0.5)
        self.ctx_spanners = dict()
        for ctxd in par.contexts:
            self.notice_context(ctxd)
        FigureCanvas.__init__(self,self.figure)
        self.mpl_connect('button_press_event',self.on_click)
    def update_range(self,min,max):
        self.plot.set_xlim(min,max)
        self.draw_idle()
    def update_spanner(self,vall,valr):
        if self.spanner != None:
            self.spanner.remove()
            self.spanner = None
        if vall < valr:
            self.spanner = self.plot.axvspan(vall,valr,alpha=0.5)
        self.draw_idle()
    def on_click(self,event):
        if event.xdata != None and event.ydata != None:
            if event.button == 1:
                self.click_handler.set_boundl(event.xdata)
            elif event.button == 3:
                self.click_handler.set_boundr(event.xdata)
    def notice_context(self,descr):
        spans = []
        for (start,end) in descr.entries:
            spans.append(self.plot.axvspan(start,end,alpha=0.3,facecolor=descr.color))
        self.ctx_spanners[descr.name] = spans
    def notice_annotation(self,ctx,col,start,end):
        spans = self.ctx_spanners[ctx]
        spans.append(self.plot.axvspan(start,end,alpha=0.3,facecolor=col))
        self.draw_idle()
    def notice_context_removal(self,ctx):
        ctxd = self.ctx_spanners[ctx]
        for spanner in ctxd:
            spanner.remove()
        del self.ctx_spanners[ctx]
        self.draw_idle()

class CtxAnnotator(gtk.VBox):
    def __init__(self):
        self.policy = ScaleDisplayPolicy(10000,150)
        self.displays = []
        self.contexts = dict()
        self.context_colors = ['red','green','yellow','orange']
        
        self.scalel = gtk.HScale()
        self.scaler = gtk.HScale()
        self.adjl = gtk.Adjustment()
        self.adjr = gtk.Adjustment()

        self.scalel.set_adjustment(self.adjl)
        self.scaler.set_adjustment(self.adjr)

        self.scalel.set_digits(10)
        self.scaler.set_digits(10)
        self.scalel.connect("format-value",scale_display)
        self.scaler.connect("format-value",scale_display)
        self.scalel.connect("value-changed",self.update_spanners)
        self.scaler.connect("value-changed",self.update_spanners)
        self.display_box = gtk.VBox()
        self.context_box = gtk.HBox()
        add_button = gtk.Button(stock='gtk-add')
        add_button.connect('clicked',lambda but: self.create_context())
        self.context_box.pack_start(add_button,expand=False,fill=True)

        scr_win = gtk.ScrolledWindow()
        scr_win.add_with_viewport(self.display_box)
        scr_win.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

        gtk.VBox.__init__(self)
        self.pack_start(scr_win,expand=True,fill=True)
        self.pack_end(self.scaler,expand=False,fill=True)
        self.pack_end(self.scalel,expand=False,fill=True)
        self.pack_end(self.context_box,expand=False,fill=True)
        self.connect('key-press-event',self.on_key)
    def on_key(self,wid,ev):
        print ev.string
        if ev.string is '+':
            self.bigger()
        elif ev.string is '-':
            self.smaller()
        
    def update_spanners(self,obj):
        for d in self.displays:
            d.update_spanner(self.adjl.get_value(),self.adjr.get_value())
    def set_boundl(self,val):
        self.adjl.value = val
        self.adjl.value_changed()
    def set_boundr(self,val):
        self.adjr.value = val
        self.adjr.value_changed()
    def bigger(self):
        self.policy.biggerx()
        self.update_zoom()
    def smaller(self):
        self.policy.smallerx()
        self.update_zoom()
    def update_zoom(self):
        (w,h) = self.policy.display_sizes(num2date(self.xmax)-num2date(self.xmin))
        for d in self.displays:
            d.set_size_request(w,h)
            
    def recalculate(self):
        xmin = None
        xmax = None
        for d in self.displays:
            min,max = d.src.xBounds()
            if xmin is None or min < xmin:
                xmin = min
            if xmax is None or max > xmax:
                xmax = max
        self.xmin = xmin
        self.xmax = xmax
        if not xmin is None:
            self.adjl.lower = xmin
            self.adjr.lower = xmin
            self.adjl.upper = xmax
            self.adjr.upper = xmax
            self.adjl.value = xmin
            self.adjr.value = xmax

            self.adjl.changed()
            self.adjr.changed()
            self.adjl.value_changed()
            self.adjr.value_changed()

            for d in self.displays:
                d.update_range(xmin,xmax)

    def add_source(self,src):
        disp = Display(self,src)
        self.displays.append(disp)
        self.display_box.pack_start(disp,expand=True,fill=True)
        self.recalculate()
    def add_context(self,name):
        found_color = None
        for col in self.context_colors:
            avail = True
            for (ctx,but) in self.contexts.values():
                if ctx.color == col:
                    avail = False
                    break
            if avail:
                found_color = col
                break
        if found_color == None:
            print "HALP! I CAN'T HAZ COLOR!"
            return
        descr = ContextDescription(name,found_color)
        but = ContextButton(descr,self)
        but.show_all()
        self.context_box.pack_start(but,expand=False,fill=True)
        self.contexts[descr.name]=(descr,but)
        for d in self.displays:
            d.notice_context(descr)
    def remove_context(self,name):
        for d in self.displays:
            d.notice_context_removal(name)
        (descr,but) = self.contexts[name]
        self.context_box.remove(but)
        del self.contexts[name]
    def create_context(self):
        dialog = gtk.MessageDialog(None,
                                   gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                   gtk.MESSAGE_QUESTION,
                                   gtk.BUTTONS_OK, None)
        dialog.set_markup("Please enter the <b>name</b> of the context")
        entry = gtk.Entry()
        entry.connect("activate", lambda wid: dialog.response(gtk.RESPONSE_OK))
        dialog.vbox.pack_end(entry,expand=True,fill=True)
        dialog.show_all()
        dialog.run()
        self.add_context(entry.get_text())
        dialog.destroy()
    def create_annotation(self,name):
        start = self.adjl.value
        end = self.adjr.value
        (descr,but) = self.contexts[name]
        descr.entries.append((start,end))
        for d in self.displays:
            d.notice_annotation(name,descr.color,start,end)

def scale_display(obj,value):
    if value == 0:
        return ""
    else:
        return num2date(value).strftime("%Y-%m-%d %H:%M:%S")

class ScaleDisplayPolicy:
    def __init__(self,pixel_per_hour,base_height=100):
        self.pixel_per_hour = pixel_per_hour
        self.base_height = base_height
        self.scales = [0.25,0.5,1.0,1.5,2.0,2.5,3.0]
        self.curx = 2
        self.cury = 2
    def biggerx(self):
        if self.curx < len(self.scales)-1:
            self.curx += 1
    def smallerx(self):
        if self.curx > 0:
            self.curx -= 1
    def biggery(self):
        if self.cury < len(self.scales)-1:
            self.cury += 1
    def smallery(self):
        if self.cury > 0:
            self.cury -= 1
    def display_sizes(self,tdelta):
        hours = float(tdelta.days)*24.0 + float(tdelta.seconds)/3600
        width = hours*self.pixel_per_hour*self.scales[self.curx]
        height = self.base_height*self.scales[self.cury]
        return (int(width),int(height))

class ContextButton(gtk.HBox):
    def __init__(self,descr,par):
        gtk.HBox.__init__(self)
        add_button = gtk.Button("")
        add_button.get_child().set_markup("<span bgcolor=\""+descr.color+"\">"+descr.name+"</span>")
        rem_button = gtk.Button(stock='gtk-delete')
        self.pack_start(add_button,expand=True,fill=True)
        self.pack_start(rem_button,expand=False,fill=True)
        rem_button.connect('clicked',lambda but: par.remove_context(descr.name))
        add_button.connect('clicked',lambda but: par.create_annotation(descr.name))

class ContextDescription:
    def __init__(self,name,color):
        self.name = name
        self.color = color
        self.entries = []
    def add_entry(self,start,end):
        self.entries.append((start,end))

if __name__=="__main__":
    win = gtk.Window()
    win.connect("destroy", lambda x: gtk.main_quit())

    win.set_default_size(400,300)
    win.set_title("Context Annotator")
    
    box = CtxAnnotator()
    box.add_source(MovementSource("examples/movement.log"))
    cur = datetime.datetime(2009,6,3,11,48,0)

    box.add_source(WaveSource("examples/01 - Elvenpath.wav",cur))
    box.add_context("Blub")
    box.add_context("Blah")
    win.add(box)

    win.show_all()
    gtk.main()
