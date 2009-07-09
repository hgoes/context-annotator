import numpy as np
#import matplotlib.pyplot as plt
import gtk
import datetime
import time
import calendar
import scikits.audiolab
from matplotlib.figure import Figure
from matplotlib.dates import date2num,num2date,MinuteLocator
import gettext
from dateentry import DateEdit

gettext.install('context-annotator','po')

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
        self.figure = Figure(figsize=(5,4),dpi=100)
        self.plot = self.figure.add_subplot(111,xbound=xb,ybound=yb,autoscale_on=False)
        self.plot.get_xaxis().set_major_locator(MinuteLocator(tz=UTC()))
        self.plot.plot_date(src.getX(),src.getY(),'-')
        self.spanner = self.plot.axvspan(xb[0],xb[1],alpha=0.5)
        self.ctx_spanners = dict()
        FigureCanvas.__init__(self,self.figure)
        self.mpl_connect('button_press_event',self.on_press)
        self.mpl_connect('button_release_event',self.on_release)
        self.mpl_connect('motion_notify_event',self.on_move)
    def update_range(self,min,max):
        self.plot.set_xlim(min,max)
        self.draw_idle()
    def update_spanner(self,vall,valr):
        if self.spanner != None:
            self.spanner.remove()
            self.spanner = None
        if vall != valr:
            self.spanner = self.plot.axvspan(vall,valr,alpha=0.5)
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
    def notice_annotation_removal(self,ctx,pos):
        self.ctx_spanners[ctx][pos].remove()
        del self.ctx_spanners[ctx][pos]
        self.draw_idle()

class InputState:
    def __init__(self,par):
        self.bounds = None
        self.tmpl = 0.0
        self.tmpr = 0.0
        self.par = par
        self.bound_change = False
        self.selection = None
    def propagate_marker(self):
        for d in self.par.displays:
            d.update_spanner(self.tmpl,self.tmpr)
    def bound_change_start(self,loc):
        self.tmpl = loc
        self.tmpr = loc
        self.propagate_marker()
        self.bound_change = True
    def bound_change_update(self,loc):
        if self.bound_change:
            self.tmpr = loc
            self.propagate_marker()
    def bound_change_end(self,loc):
        if self.bound_change:
            self.tmpr = loc
            if self.tmpl < self.tmpr:
                self.bounds = (self.tmpl,self.tmpr)
            elif self.tmpl > self.tmpr:
                self.bounds = (self.tmpr,self.tmpl)
            else:
                self.bounds = None
            self.propagate_marker()
            self.bound_change = False
    def select(self,loc,time,display):
        if self.bounds != None:
            if loc >= self.bounds[0] and loc <= self.bounds[1]:
                self.selection = True
                self.par.notify_select(time,display)
                return
        self.selection = self.par.find_annotation(loc)
        self.par.notify_select(time,display)

class CtxAnnotator(gtk.VBox):
    def __init__(self):
        self.policy = ScaleDisplayPolicy(10000,150)
        self.displays = []
        self.contexts = dict()
        self.context_colors = ['red','green','yellow','orange']
        
        self.display_box = gtk.VBox()
        self.context_box = gtk.HBox()
        self.input_state = InputState(self)
        add_button = gtk.Button(stock='gtk-add')
        add_button.connect('clicked',lambda but: self.create_context())
        self.context_box.pack_start(add_button,expand=False,fill=True)

        scr_win = gtk.ScrolledWindow()
        scr_win.add_with_viewport(self.display_box)
        scr_win.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

        gtk.VBox.__init__(self)
        self.pack_start(scr_win,expand=True,fill=True)
        self.pack_end(self.context_box,expand=False,fill=True)
    def find_annotation(self,x):
        for (ctx,but) in self.contexts.values():
            ind = 0
            for ind in range(len(ctx.entries)):
                if ctx.entries[ind][0] <= x and ctx.entries[ind][1] >= x:
                    return (ctx.name,ind)
        return None
    def bigger(self):
        self.policy.biggerx()
        self.update_zoom()
    def smaller(self):
        self.policy.smallerx()
        self.update_zoom()
    def update_zoom(self):
        if self.displays != []:
            utc = UTC()
            (w,h) = self.policy.display_sizes(num2date(self.xmax,tz=utc)-num2date(self.xmin,tz=utc))
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
        for (ctx,but) in self.contexts.values():
            for (start,end) in ctx.entries:
                if xmin is None or start < xmin:
                    xmin = start
                if xmax is None or end > xmax:
                    xmax = end
        self.xmin = xmin
        self.xmax = xmax
        if not xmin is None:
            for d in self.displays:
                d.update_range(xmin,xmax)
            self.input_state.propagate_marker()

    def add_source(self,src):
        disp = Display(self.input_state,src)
        for ctx in self.contexts:
            disp.notice_context(ctx)
        self.displays.append(disp)
        frame = gtk.Table(3,2)
        cont = gtk.Frame()
        cont.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        cont.add(disp)
        frame.attach(cont,0,1,1,3,gtk.EXPAND|gtk.FILL,gtk.EXPAND|gtk.FILL)
        lbl = gtk.Label()
        lbl.set_markup("<b>"+src.getName()+"</b>")
        lbl.set_alignment(0.0,0.5)
        frame.attach(lbl,0,1,0,1,gtk.EXPAND|gtk.FILL,gtk.SHRINK|gtk.FILL)
        rem_but = gtk.Button()
        rem_but.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE,gtk.ICON_SIZE_MENU))
        rem_but.connect('clicked',self.remove_source_handler,frame,disp)
        frame.attach(rem_but,1,2,1,2,gtk.SHRINK|gtk.FILL,gtk.SHRINK|gtk.FILL)
        frame.attach(gtk.VBox(),1,2,2,3,gtk.SHRINK,gtk.EXPAND)
        frame.show_all()
        self.display_box.pack_start(frame,expand=True,fill=True)
        self.recalculate()
    def remove_source_handler(self,but,frame,display):
        self.display_box.remove(frame)
        self.displays.remove(display)
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
            return None
        descr = ContextDescription(name,found_color)
        but = ContextButton(descr,self)
        but.show_all()
        self.context_box.pack_start(but,expand=False,fill=True)
        self.contexts[descr.name]=(descr,but)
        for d in self.displays:
            d.notice_context(descr)
        return descr
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
        dialog.set_markup(_("Please enter the <b>name</b> of the context"))
        entry = gtk.Entry()
        entry.connect("activate", lambda wid: dialog.response(gtk.RESPONSE_OK))
        dialog.vbox.pack_end(entry,expand=True,fill=True)
        dialog.show_all()
        dialog.run()
        self.add_context(entry.get_text())
        dialog.destroy()
    def add_annotation(self,name,start,end):
        if not name in self.contexts:
            descr = self.add_context(name)
            for d in self.displays:
                d.notice_context(descr)
        (descr,but) = self.contexts[name]
        descr.entries.append((start,end))
        for d in self.displays:
            d.notice_annotation(name,descr.color,start,end)
    def create_annotation(self,name):
        if self.input_state.bounds != None:
            (start,end) = self.input_state.bounds
            self.add_annotation(name,start,end)
    def notify_select(self,time,display):
        if self.input_state.selection == None:
            pass
        elif self.input_state.selection == True:
            menu = SelectionMenu(self,display)
            menu.show_all()
            menu.popup(None,None,None,3,time)
        else:
            menu = AnnotationMenu(self)
            menu.show_all()
            menu.popup(None,None,None,3,time)
    def remove_annotation(self,name,pos):
        del self.contexts[name][0].entries[pos]
        for d in self.displays:
            d.notice_annotation_removal(name,pos)
    def write_out(self,fn):
        annotations = []
        for (ctx,but) in self.contexts.values():
            for (begin,end) in ctx.entries:
                annotations.append((ctx.name,begin,end))
        annotations.sort(key=lambda obj: obj[1])
        with open(fn,'w') as h:
            utc = UTC()
            for (name,begin,end) in annotations:
                print num2date(begin,utc)
                h.write(name+" "+str(calendar.timegm(num2date(begin,utc).utctimetuple()))+" "
                        +str(calendar.timegm(num2date(end,utc).utctimetuple()))+"\n")
    def read_in(self,fn):
        for ctx in self.contexts.keys():
            self.remove_context(ctx)
        with open(fn,'r') as h:
            for ln in h:
                (name,start,end) = ln.split()
                self.add_annotation(name,
                                    date2num(datetime.datetime.utcfromtimestamp(float(start))),
                                    date2num(datetime.datetime.utcfromtimestamp(float(end))))
            self.recalculate()
        
class ScaleDisplayPolicy:
    def __init__(self,pixel_per_hour,base_height=100):
        self.pixel_per_hour = pixel_per_hour
        self.base_height = base_height
        self.scales = [0.1,0.25,0.5,1.0,1.5,2.0,2.5,3.0,4.0]
        self.curx = 3
        self.cury = 3
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

class SelectionMenu(gtk.Menu):
    def __init__(self,par,display):
        gtk.Menu.__init__(self)
        ann = gtk.MenuItem(label=_("Annotate"))
        sub_ann = gtk.Menu()
        ann.set_submenu(sub_ann)
        for (ctx,but) in par.contexts.values():
            it = gtk.ImageMenuItem("")
            img = gtk.Image()
            img.set_from_stock(gtk.STOCK_BOLD,gtk.ICON_SIZE_MENU)
            it.set_image(img)
            it.get_child().set_markup("<span bgcolor=\""+ctx.color+"\">"+ctx.name+"</span>")
            it.connect('activate',lambda w,str: par.create_annotation(str),ctx.name)
            sub_ann.append(it)
        sub_ann.append(gtk.SeparatorMenuItem())
        new_it = gtk.ImageMenuItem(_("New context..."))
        new_img = gtk.Image()
        new_img.set_from_stock(gtk.STOCK_ADD,gtk.ICON_SIZE_MENU)
        new_it.set_image(new_img)
        new_it.connect('activate',lambda w: par.create_context())
        sub_ann.append(new_it)
        self.append(ann)
        if display.src.hasCapability("play"):
            play_it = gtk.ImageMenuItem(stock_id=gtk.STOCK_MEDIA_PLAY)
            (start,end) = par.input_state.bounds
            play_it.connect('activate',self.play_annotation,
                            display,
                            num2date(start,UTC()),
                            num2date(end,UTC()))
            self.append(play_it)
    def play_annotation(self,menu,display,start,end):
        data = display.src.getPlayData(start,end)
        scikits.audiolab.play(data[0],data[1])

class AnnotationMenu(gtk.Menu):
    def __init__(self,par):
        gtk.Menu.__init__(self)
        it = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        sel = par.input_state.selection
        it.connect('activate',lambda w,name,pos: par.remove_annotation(name,pos),sel[0],sel[1])
        self.append(it)

class Application(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        accel = gtk.AccelGroup()
        self.add_accel_group(accel)
        self.connect("destroy", lambda x: gtk.main_quit())

        self.set_default_size(400,300)
        self.set_title(_("Context Annotator"))
    
        bar = gtk.MenuBar()
        file_item = gtk.MenuItem(label=_('_Annotations'))
        bar.append(file_item)
        file_menu = gtk.Menu()
        file_item.set_submenu(file_menu)
        open_item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
        open_item.connect('activate',lambda x: self.load())
        open_item.add_accelerator('activate',accel,111,gtk.gdk.CONTROL_MASK,gtk.ACCEL_VISIBLE)
        save_item = gtk.ImageMenuItem(gtk.STOCK_SAVE)
        save_item.connect('activate',lambda x: self.save())
        save_item.add_accelerator('activate',accel,115,gtk.gdk.CONTROL_MASK,gtk.ACCEL_VISIBLE)
        file_menu.append(open_item)
        file_menu.append(save_item)
        
        source_item = gtk.MenuItem(label=_('_Sources'))
        bar.append(source_item)
        source_menu = gtk.Menu()
        source_item.set_submenu(source_menu)
        open_source_item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
        open_source_item.connect('activate',lambda x: self.load_source())
        source_menu.append(open_source_item)

        view_item = gtk.MenuItem(label=_('_View'))
        bar.append(view_item)
        view_menu = gtk.Menu()
        view_item.set_submenu(view_menu)
        zoom_in_item = gtk.ImageMenuItem(gtk.STOCK_ZOOM_IN, accel)
        zoom_in_item.connect('activate',lambda x: self.annotator.bigger())
        zoom_in_item.add_accelerator("activate",accel,43,gtk.gdk.CONTROL_MASK,gtk.ACCEL_VISIBLE)
        zoom_out_item = gtk.ImageMenuItem(gtk.STOCK_ZOOM_OUT)
        zoom_out_item.connect('activate',lambda x: self.annotator.smaller())
        zoom_out_item.add_accelerator("activate",accel,45,gtk.gdk.CONTROL_MASK,gtk.ACCEL_VISIBLE)
        view_menu.append(zoom_in_item)
        view_menu.append(zoom_out_item)
    
        layout = gtk.VBox()
        layout.pack_start(bar,expand=False,fill=True)

        self.add(layout)
        
        self.annotator = CtxAnnotator()
        layout.pack_start(self.annotator,expand=True,fill=True)
        #self.annotator.add_source(MovementSource("examples/movement.log"))
        cur = datetime.datetime(2009,6,3,9,48,0,0,UTC())

        self.annotator.add_source(SoundSource("examples/01 - Elvenpath.wav",cur))
    def save(self):
        dialog = gtk.FileChooserDialog(title=_("Save annotation"),
                                       action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                       buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.annotator.write_out(dialog.get_filename())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
    def load(self):
        dialog = gtk.FileChooserDialog(title=_("Load annotation"),
                                       action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                       buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.annotator.read_in(dialog.get_filename())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
    def load_source(self):
        dialog = LoadSourceDialog()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            src = dialog.get_source()
            self.annotator.add_source(src)
        dialog.destroy()
    def run(self):
        self.show_all()
        gtk.main()

class LoadSourceDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self,title=_("Load source"))
        table = gtk.Table(5,2)
        lbl_file = gtk.Label()
        lbl_file.set_markup("<b>"+_("File")+":</b>")
        lbl_file.set_alignment(0.0,0.5)
        self.openw = gtk.FileChooserButton(title=_("Load source"))
        
        lbl_filetype = gtk.Label()
        lbl_filetype.set_markup("<b>"+_("File type")+":</b>")
        lbl_filetype.set_alignment(0.0,0.5)
        
        self.opt_movement = gtk.RadioButton(label=_("Movement data"))
        self.opt_movement.connect('toggled',lambda s: self.update_hide_show())
        self.opt_audio = gtk.RadioButton(group=self.opt_movement,label=_("Audio data"))
        self.opt_audio.connect('toggled',lambda s: self.update_hide_show())
        
        self.box_audio = gtk.Table(3,2)
        lbl_channel = gtk.Label()
        lbl_channel.set_markup(_("Channel")+":")
        lbl_channel.set_alignment(0.0,0.5)
        opt_chan1 = gtk.RadioButton(label=_("Channel")+" 1")
        opt_chan2 = gtk.RadioButton(group=opt_chan1,label=_("Channel")+" 2")
        lbl_offset = gtk.Label()
        lbl_offset.set_markup(_("Offset")+":")
        lbl_offset.set_alignment(0.0,0.5)
        self.date_entry = DateEdit(show_time=True,use_24_format=True)

        self.box_audio.attach(lbl_channel,0,1,0,1,gtk.SHRINK|gtk.FILL)
        self.box_audio.attach(opt_chan1,1,2,0,1)
        self.box_audio.attach(opt_chan2,1,2,1,2)
        self.box_audio.attach(lbl_offset,0,1,2,3,gtk.SHRINK|gtk.FILL)
        self.box_audio.attach(self.date_entry,1,2,2,3)

        self.box_movement = gtk.Table(1,3)
        lbl_axis = gtk.Label()
        lbl_axis.set_markup(_("Axis")+":")
        lbl_axis.set_alignment(0.0,0.5)
        opt_axis_x = gtk.RadioButton(label=_("X-Axis"))
        opt_axis_y = gtk.RadioButton(group=opt_axis_x,label=_("Y-Axis"))
        opt_axis_z = gtk.RadioButton(group=opt_axis_y,label=_("Z-Axis"))
        self.box_movement.attach(lbl_axis,0,1,0,1,gtk.SHRINK|gtk.FILL)
        self.box_movement.attach(opt_axis_x,1,2,0,1)
        self.box_movement.attach(opt_axis_y,1,2,1,2)
        self.box_movement.attach(opt_axis_z,1,2,2,3)

        table.attach(lbl_file,0,1,0,1,gtk.SHRINK|gtk.FILL)
        table.attach(self.openw,1,2,0,1)
        table.attach(lbl_filetype,0,1,1,2,gtk.SHRINK|gtk.FILL)
        table.attach(self.opt_movement,1,2,1,2)
        table.attach(self.box_movement,1,2,2,3,xpadding=20)
        table.attach(self.opt_audio,1,2,3,4)
        table.attach(self.box_audio,1,2,4,5,xpadding=20)

        self.get_content_area().add(table)
        self.update_hide_show()

        self.add_buttons(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK)
        self.show_all()

    def update_hide_show(self):
        if self.opt_movement.get_active():
            self.box_movement.set_sensitive(True)
            self.box_audio.set_sensitive(False)
        else:
            self.box_movement.set_sensitive(False)
            self.box_audio.set_sensitive(True)
    def get_source(self):
        fn = self.openw.get_filename()
        if fn is None:
            return None
        if self.opt_movement.get_active():
            return MovementSource(fn)
        else:
            offset = self.date_entry.get_datetime()
            return SoundSource(fn,offset)

# Note to python devs: You suck!
class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


if __name__=="__main__":
    app = Application()
    app.run()
