import numpy as np
#import matplotlib.pyplot as plt
import wave
import gtk
import datetime
from matplotlib.figure import Figure
from matplotlib.dates import date2num,num2date,MinuteLocator

# uncomment to select /GTK/GTKAgg/GTKCairo
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
#from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvas


class WaveSource:
    def __init__(self,fn,offset=datetime.date.min):
        wav_obj = wave.open(fn,'r')
        (chans,sampwidth,framerate,nframes,comptype,compname) = wav_obj.getparams()
        if sampwidth == 2:
            tp = np.dtype(np.int16)
        if sampwidth == 4:
            tp = np.dtype(np.int32)
        self.frames = np.frombuffer(buffer = wav_obj.readframes(nframes),dtype = tp)
        self.samplerate = framerate
        self.channels = chans
        self.nframes = nframes
        self.offset = offset
    def getY(self,sampling=10000,chan=0):
        return self.frames[chan::2*sampling]
    def getX(self,sampling=10000):
        #numd = date2num(self.offset)
        return np.fromiter([ date2num(self.offset + datetime.timedelta(seconds = float(i)/self.samplerate))
                             for i in range(0,self.nframes,sampling)],dtype=np.dtype(np.float))
    def xBounds(self):
        d1 = self.offset
        d2 = d1 + datetime.timedelta(seconds = float(self.nframes)/self.samplerate)
        return (date2num(d1),date2num(d2))
    def yBounds(self,chan=0):
        return (self.frames[chan::2].min(),self.frames[chan::2].max())

class MovementSource:
    def __init__(self,fn):
        f = open(fn,'r')
        lines = f.readlines()
        sz = len(lines)
        #print sz
        self.timedata = np.empty(sz,np.dtype(np.float))
        self.xdata = np.empty((sz,6),np.dtype(np.float))
        #self.xdata = np.empty(sz,np.dtype(np.float))
        for i in range(sz):
            (timestamp,ms,xv,xd,yv,yd,zv,zd) = lines[i].split()
            self.timedata[i] = date2num(datetime.datetime.fromtimestamp(int(timestamp))
                                        + datetime.timedelta(seconds = float("0."+ms)))
            #print self.timedata[i]
            #self.xdata[i] = float(xv)
            self.xdata[i,0] = float(xv)
            self.xdata[i,1] = float(xd)
            self.xdata[i,2] = float(yv)
            self.xdata[i,3] = float(yd)
            self.xdata[i,4] = float(zv)
            self.xdata[i,5] = float(zd)
    def getX(self):
        return self.timedata
    def getY(self):
        return self.xdata
    def xBounds(self):
        sz = self.timedata.size
        d1 = self.timedata[0]
        d2 = self.timedata[sz-1]
        return (d1,d2)
    def yBounds(self):
        return (self.xdata.min(),self.xdata.max())   

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
        FigureCanvas.__init__(self,self.figure)
        self.mpl_connect('button_press_event',self.on_click)
        self.mpl_connect('key_press_event',self.on_key)
        #self.set_size_request(3000,500)
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
    def on_key(self,event):
        if event.key == '+':
            self.click_handler.bigger()
        elif event.key == '-':
            self.click_handler.smaller()

class CtxAnnotator(gtk.VBox):
    def __init__(self):
        self.policy = ScaleDisplayPolicy(10000,150)
        self.displays = []
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

        scr_win = gtk.ScrolledWindow()
        scr_win.add_with_viewport(self.display_box)
        scr_win.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

        gtk.VBox.__init__(self)
        self.pack_start(scr_win,expand=True,fill=True)
        self.pack_end(self.scaler,expand=False,fill=True)
        self.pack_end(self.scalel,expand=False,fill=True)
        self.pack_end(ContextButton("Hello"),expand=False,fill=False)
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

class ContextButton(gtk.Button):
    def __init__(self,name):
        gtk.Button.__init__(self)
        #lbl = gtk.Label()
        #lbl.set_markup("<span bgcolor=\"red\">"+name+"</span>")
        #self.set_label(lbl)

if __name__=="__main__":
    win = gtk.Window()
    win.connect("destroy", lambda x: gtk.main_quit())
    win.set_default_size(400,300)
    win.set_title("Context Annotator")
    
    box = CtxAnnotator()
    box.add_source(MovementSource("movement.log"))
    cur = datetime.datetime(2009,6,3,11,48,0)

    box.add_source(WaveSource("01 - Elvenpath.wav",cur))
    
    win.add(box)

    win.show_all()
    gtk.main()
