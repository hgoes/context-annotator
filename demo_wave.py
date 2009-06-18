import numpy as np
#import matplotlib.pyplot as plt
import wave
import gtk
from matplotlib.figure import Figure

# uncomment to select /GTK/GTKAgg/GTKCairo
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
#from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvas

class WaveSource:
    def __init__(self,fn):
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
    def getY(self,sampling,chan=0):
        return self.frames[chan::2*sampling]
    def getX(self,sampling):
        return np.fromiter([ float(i)/self.samplerate for i in range(0,self.nframes,sampling)],dtype=np.dtype(np.float))
    def xBounds(self):
        return (0,float(self.nframes)/self.samplerate)
    def yBounds(self,chan=0):
        return (self.frames[chan::2].min(),self.frames[chan::2].max())

class Display(FigureCanvas):
    def __init__(self,src):
        xb = src.xBounds()
        yb = src.yBounds()
        self.figure = Figure(figsize=(5,4),dpi=100)
        self.plot = self.figure.add_subplot(111,xbound=xb,ybound=yb,autoscale_on=False)
        self.plot.plot(src.getX(10000),src.getY(10000))
        self.spanner = self.plot.axvspan(xb[0],xb[1],alpha=0.5)
        FigureCanvas.__init__(self,self.figure)
    def update_spanner(self,vall,valr):
        if self.spanner != None:
            self.spanner.remove()
            self.spanner = None
        if vall < valr:
            self.spanner = self.plot.axvspan(vall,valr,alpha=0.5)
        self.draw_idle()
        

win = gtk.Window()
win.connect("destroy", lambda x: gtk.main_quit())
win.set_default_size(400,300)
win.set_title("Context Annotator")

source = WaveSource("01 - Elvenpath.wav")

display = Display(source)

scalel = gtk.HScale()
scaler = gtk.HScale()

(lower,upper) = source.xBounds()
adjl = gtk.Adjustment(lower,lower,upper);
adjr = gtk.Adjustment(upper,lower,upper);

scalel.set_adjustment(adjl)
adjl.connect("value-changed",lambda obj: display.update_spanner(adjl.get_value(),adjr.get_value()))



scaler.set_adjustment(adjr)
adjr.connect("value-changed",lambda obj: display.update_spanner(adjl.get_value(),adjr.get_value()))

box = gtk.VBox()
box.pack_start(display,expand=True,fill=True)
box.pack_start(scalel,expand=False,fill=True)
box.pack_start(scaler,expand=False,fill=True)

win.add(box)

win.show_all()
gtk.main()
