#!/usr/bin/python
# -*- coding: utf-8

"""
Main Application
================
"""

import numpy as np
#import matplotlib.pyplot as plt
import gtk
import datetime
import time
import calendar
import scikits.audiolab
from matplotlib.dates import date2num,num2date,MinuteLocator,SecondLocator,seconds,minutes,hours,weeks
import gettext
from dateentry import DateEdit
from timezone import UTC
from annotation import Annotations
from display import Display
from inputstate import InputState
gettext.install('context-annotator','po')

from sources import *

class CtxAnnotator(gtk.VBox):
    def __init__(self):
        self.policy = ScalePolicy()
        self.displays = []
        self.xmax = None
        self.xmin = None
        self.annotations = Annotations()
        self.annotations.connect('context-added',self.add_context_button)
        self.annotations.connect('context-removed',self.remove_context_button)
        self.buttons = dict()

        self.display_box = gtk.VBox()
        self.context_box = gtk.HBox()
        self.input_state = InputState(self.annotations)
        self.input_state.connect('select-selection',self.show_selection_menu)
        self.input_state.connect('select-annotation',self.show_annotation_menu)
        add_button = gtk.Button(stock='gtk-add')
        add_button.connect('clicked',lambda but: self.create_context())
        self.context_box.pack_start(add_button,expand=False,fill=True)

        scr_win = gtk.ScrolledWindow()
        scr_win.add_with_viewport(self.display_box)
        scr_win.set_policy(gtk.POLICY_NEVER,gtk.POLICY_AUTOMATIC)

        self.adjustment = gtk.Adjustment()
        self.adjustment.connect('value-changed',self.update_pos)
        self.scroller = gtk.HScrollbar(self.adjustment)
        self.scroller.hide()
        gtk.VBox.__init__(self)
        self.pack_start(scr_win,expand=True,fill=True)
        self.pack_start(self.scroller,expand=False,fill=True)
        self.pack_end(self.context_box,expand=False,fill=True)
    def update_pos(self,adj):
        self.policy.update_pos(adj.value)
        for d in self.displays:
            d.update_zoom(self.policy)
    def find_annotation(self,x):
        hits = self.annotations.find_annotation(x)
        if len(hits) is 0:
            return None
        else:
            return hits[0]
    def bigger(self):
        self.policy.biggerx()
        self.update_zoom()
    def smaller(self):
        self.policy.smallerx()
        self.update_zoom()
    def update_zoom(self):
        if self.xmax is None:
            self.scroller.hide()
            return
        max = self.xmax - self.policy.get_window()
        if self.xmin < max:
            self.adjustment.lower = self.xmin
            self.adjustment.upper = max
            self.scroller.show()
        else:
            self.scroller.hide()
        self.adjustment.step_increment = self.policy.get_steps()
        self.adjustment.changed()
        for d in self.displays:
            d.update_zoom(self.policy)
            
    def recalculate(self):
        xmin = None
        xmax = None
        for d in self.displays:
            min,max = d.src.xBounds()
            if xmin is None or min < xmin:
                xmin = min
            if xmax is None or max > xmax:
                xmax = max
        ann_l,ann_r = self.annotations.bounds()
        if ann_l is not None and ann_l < xmin:
            xmin = ann_l
        if ann_r is not None and ann_r > xmax:
            xmax = ann_r
        self.xmin = xmin
        self.xmax = xmax
        if xmin is not None:
            self.policy.update_min(xmin)
        self.update_zoom()

    def add_source(self,src):
        disp = Display(src,self.annotations,self.input_state)
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
        frame.destroy()
        self.recalculate()
    def add_context(self,name):
        self.annotations.add_context(name)
    def add_context_button(self,model,name,color):
        but = ContextButton(name,color,self)
        but.show_all()
        self.context_box.pack_start(but,expand=False,fill=True)
        self.buttons[name] = but
    def remove_context_button(self,model,name):
        but = self.buttons[name]
        self.context_box.remove(but)
        del self.buttons[name]
    def remove_context(self,name):
        self.annotations.remove_context(name)
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
        self.annotations.add_annotation(name,start,end)
    def create_annotation(self,name):
        if self.input_state.selection is not None:
            (start,end) = self.input_state.selection
            self.add_annotation(name,start,end)
    def show_selection_menu(self,state,display,boundl,boundr,time):
        menu = SelectionMenu(self,display)
        menu.show_all()
        menu.popup(None,None,None,3,time)
    def show_annotation_menu(self,state,display,id,time):
        menu = AnnotationMenu(self,id)
        menu.show_all()
        menu.popup(None,None,None,3,time)
    def remove_annotation(self,id):
        self.annotations.remove_annotation(id)
    def write_out(self,fn):
        self.annotations.write(fn)
    def read_in(self,fn):
        try:
            self.annotations.read(fn)
        except Exception as e:
            warning = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                        buttons=gtk.BUTTONS_OK,
                                        message_format=str(e))
            warning.run()
            warning.destroy()

class ScalePolicy:
    def __init__(self):
        self.scales = [(_("Hour"),hours(1),MinuteLocator(interval=10)),
                       (_("Half-hour"),minutes(30),MinuteLocator(interval=5)),
                       (_("10-Minute"),minutes(10),MinuteLocator(interval=2)),
                       (_("Minute"),minutes(1),SecondLocator(interval=10))
                       ]
        self.cur = 0
        self.pos = None
    def get_window(self):
        return self.scales[self.cur][1]
    def get_locator(self):
        return self.scales[self.cur][2]
    def get_steps(self):
        return self.get_window()/100
    def get_bounds(self):
        if self.pos is None:
            raise ValueError()
        win = self.get_window()
        return (self.pos,self.pos+win)
    def update_min(self,npos):
        if self.pos is None:
            self.pos = npos
    def update_pos(self,pos):
        self.pos = pos
    def biggerx(self):
        if self.cur+1 < len(self.scales):
            self.cur+=1
    def smallerx(self):
        if self.cur > 0:
            self.cur-=1

class ContextButton(gtk.HBox):
    def __init__(self,name,color,par):
        gtk.HBox.__init__(self)
        add_button = gtk.Button("")
        add_button.get_child().set_markup("<span bgcolor=\""+color+"\">"+name+"</span>")
        rem_button = gtk.Button(stock='gtk-delete')
        self.pack_start(add_button,expand=True,fill=True)
        self.pack_start(rem_button,expand=False,fill=True)
        rem_button.connect('clicked',lambda but: par.remove_context(name))
        add_button.connect('clicked',lambda but: par.create_annotation(name))

class SelectionMenu(gtk.Menu):
    def __init__(self,par,display):
        gtk.Menu.__init__(self)
        ann = gtk.MenuItem(label=_("Annotate"))
        sub_ann = gtk.Menu()
        ann.set_submenu(sub_ann)
        for (ctx,color) in par.annotations.contexts():
            it = gtk.ImageMenuItem("")
            img = gtk.Image()
            img.set_from_stock(gtk.STOCK_BOLD,gtk.ICON_SIZE_MENU)
            it.set_image(img)
            it.get_child().set_markup("<span bgcolor=\""+color+"\">"+ctx+"</span>")
            it.connect('activate',lambda w,str: par.create_annotation(str),ctx)
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
    def __init__(self,par,sel):
        gtk.Menu.__init__(self)
        it = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        it.connect('activate',lambda w,id: par.remove_annotation(id),sel)
        self.append(it)

class Application(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        accel = gtk.AccelGroup()
        self.add_accel_group(accel)
        self.connect("destroy", lambda x: gtk.main_quit())

        self.set_default_size(800,600)
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

        help_item = gtk.MenuItem(label=_('_Help'))
        bar.append(help_item)
        help_menu = gtk.Menu()
        help_item.set_submenu(help_menu)
        about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        about_item.connect('activate',lambda x: self.show_about())
        help_menu.append(about_item)
    
        self.status = gtk.Statusbar()
        
        layout = gtk.VBox()
        layout.pack_start(bar,expand=False,fill=True)

        self.add(layout)
        
        self.annotator = CtxAnnotator()
        self.annotator.input_state.connect('message-changed',self.set_message)
        layout.pack_start(self.annotator,expand=True,fill=True)
        layout.pack_start(self.status,expand=False,fill=True)
    def set_message(self,state,str):
        ctx = self.status.get_context_id("coords")
        self.status.push(ctx,str)
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
            try:
                src = dialog.get_source()
                self.annotator.add_source(src)
            except Exception as e:
                warning = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                            buttons=gtk.BUTTONS_OK,
                                            message_format=str(e))
                warning.run()
                warning.destroy()
        dialog.destroy()
    def run(self):
        self.show_all()
        self.annotator.update_zoom()
        gtk.main()
    def show_about(self):
        dialog = gtk.AboutDialog()
        dialog.set_name(_("Context Annotator"))
        dialog.set_copyright("© 2009 Henning Günther")
        dialog.set_license(_("\
This program is free software; you can redistribute\n\
it and/or modify it under the terms of the GNU General\n\
Public License as published by the Free Software\n\
Foundation; either version 3 of the License, or (at your\n\
option) any later version.\n\n\
This program is distributed in the hope that it will be\n\
useful, but WITHOUT ANY WARRANTY; without even the\n\
implied warranty of MERCHANTABILITY or FITNESS FOR A\n\
PARTICULAR PURPOSE. See the GNU General Public License\n\
for more details.\n\n\
You should have received a copy of the GNU General\n\
Public License along with this program; if not, see\n\
<http://www.gnu.org/licenses/>."))
        dialog.set_version("0.1")
        dialog.set_authors(["Henning Günther <h.guenther@tu-bs.de>"])
        dialog.run()
        dialog.destroy()

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
        self.opt_axis_x = gtk.RadioButton(label=_("X-Axis"))
        self.opt_axis_y = gtk.RadioButton(group=self.opt_axis_x,label=_("Y-Axis"))
        self.opt_axis_z = gtk.RadioButton(group=self.opt_axis_y,label=_("Z-Axis"))
        self.box_movement.attach(lbl_axis,0,1,0,1,gtk.SHRINK|gtk.FILL)
        self.box_movement.attach(self.opt_axis_x,1,2,0,1)
        self.box_movement.attach(self.opt_axis_y,1,2,1,2)
        self.box_movement.attach(self.opt_axis_z,1,2,2,3)

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
            if self.opt_axis_x.get_active():
                axis = 0
            elif self.opt_axis_y.get_active():
                axis = 1
            else:
                axis = 2
            return MovementSource(fn,axis)
        else:
            offset = self.date_entry.get_datetime()
            return SoundSource(fn,offset)

if __name__=="__main__":
    app = Application()
    app.run()
