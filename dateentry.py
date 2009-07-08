# Python GTK+ date and time entry widget.
# Copyright (C) 2005  Fabian Sturm
#
# ported from the libgnomeui/gnome-dateedit.c
# Modified by Henning Guenther <h.guenther@tu-bs.de>
#
# This widget is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this widget; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA


import pygtk

pygtk.require('2.0')

import gobject
import gtk
from gtk import gdk
import time
import datetime


 # gnome_date_edit_new:
 # @the_time: date and time to be displayed on the widget
 # @show_time: whether time should be displayed
 # @use_24_format: whether 24-hour format is desired for the time display.
 #
 # Description: Creates a new #GnomeDateEdit widget which can be used
 # to provide an easy to use way for entering dates and times.
 # If @the_time is 0 then current time is used.
 #
 # Returns: a new #GnomeDateEdit widget.
 # Todo: missing the version with the flags in the constructor
class DateEdit(gtk.HBox):
    __gtype_name__ = 'DateEdit'

    def __init__(self, the_time = None, show_time = True, use_24_format = True):
        gtk.HBox.__init__(self)

        # register custom signals, help can anyone explain this call parameters?
        # (I mean better than in the api docs)
        gobject.signal_new('time_changed', DateEdit,
                       gobject.SIGNAL_RUN_FIRST,
                       gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,))
        gobject.signal_new('date_changed', DateEdit,
                       gobject.SIGNAL_RUN_FIRST,
                       gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,))                       
        
        # preset values
        self.__lower_hour = 7;
        self.__upper_hour = 19;

        self.__flag_show_time = show_time
        self.__flag_use_24_format = use_24_format
        self.__flag_week_starts_monday = False

        # the date entry
        self.__date_entry = gtk.Entry()
        self.__date_entry.set_size_request(90, -1)
        self.pack_start(self.__date_entry, True, True, 0)
        self.__date_entry.show()
        
        # the date button
        self.__date_button = gtk.Button()
        self.__date_button.connect('clicked', self.select_clicked)
        self.pack_start(self.__date_button, False, False, 0)
        hbox = gtk.HBox(False, 3)
        self.__date_button.add(hbox)
        hbox.show()
        # calendar label, only show if the date editor has a time field
        self.__cal_label = gtk.Label('Calendar')
        self.__cal_label.set_alignment(0.0, 0.5)
        hbox.pack_start(self.__cal_label, True, True, 0)
        self.__cal_label.show()
        # the down arrow
        arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_OUT)
        hbox.pack_start(arrow, True, False, 0)
        arrow.show()
        # finally show the button
        self.__date_button.show()
        
        # the time entry
        self.__time_entry = gtk.Entry()
        self.__time_entry.set_max_length(12)
        self.__time_entry.set_size_request(88, -1)
        self.pack_start(self.__time_entry, True, True, 0)
            
        # the time popup menu
        self.__time_popup = gtk.ComboBox(TimeTree(7,19))
        self.__time_popup.connect('changed',self.time_selected)
        cell = gtk.CellRendererText()
        self.__time_popup.pack_start(cell,True)
        self.__time_popup.add_attribute(cell,'text',0)
        self.pack_start(self.__time_popup, False, False, 0)
        
        if show_time == True:
            self.__time_entry.show()
            self.__time_popup.show()
        
        # the calendar popup
        self.__cal_popup = gtk.Window(gtk.WINDOW_POPUP)
        self.__cal_popup.set_events(self.__cal_popup.get_events() | gdk.KEY_PRESS_MASK)
        self.__cal_popup.connect('delete_event', self.delete_popup)
        self.__cal_popup.connect('key_press_event', self.key_press_popup)
        self.__cal_popup.connect('button_press_event', self.button_press_popup)
        self.__cal_popup.set_resizable(False) # Todo: Needed?
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_OUT)
        self.__cal_popup.add(frame)
        frame.show()
        # the calendar
        self.__calendar = gtk.Calendar()
        self.__calendar.display_options(gtk.CALENDAR_SHOW_DAY_NAMES 
                                        | gtk.CALENDAR_SHOW_HEADING)
        self.__calendar.connect('day-selected', self.day_selected)
        self.__calendar.connect('day-selected-double-click', self.day_selected_double_click)
        frame.add(self.__calendar)
        self.__calendar.show()

        # set provided date and time
        self.set_date_time(the_time)
        
    def set_show_time(self,show_time):
        if show_time != self.__flag_show_time:
            self.__flag_show_time = show_time
            if show_time:
                self.__cal_label.show() 
                self.__time_entry.show()
                self.__time_popup.show()
            else:
                self.__cal_label.hide()
                self.__time_entry.hide()
                self.__time_popup.hide()

    def set_use_24_format(self,use24):
        if use24 != self.__flag_use_24_format:
            self.__flag_use_24_format = use24
            self.__time_popup.set_model(TimeTree(self.__lower_hour,set.__upper_hour,use24))

    def set_week_starts_on_monday(self,starts_mon):
        if starts_mon != self.__flag_week_starts_monday:
            self.__flag_week_starts_monday = starts_mon
            if starts_mon:
                self.__calendar.set_display_options(self.__calendar.get_display_options() | gtk.CALENDAR_WEEK_START_MONDAY)
            else:
                self.__calendar.set_display_options(self.__calendar.get_display_options() & ~gtk.CALENDAR_WEEK_START_MONDAY)
    def set_date_time(self, the_time):      
        if the_time is None:
            the_time = datetime.datetime.today()
        assert isinstance(the_time, (datetime.datetime, datetime.date))
        # set the date
        self.__initial_time = the_time
        self.__date_entry.set_text(the_time.strftime('%x'))
        # set the time
        if self.__flag_use_24_format:
            self.__time_entry.set_text(the_time.strftime('%H:%M'))
        else:
            self.__time_entry.set_text(the_time.strftime('%I:%M %p'))


    def popup_grab_on_window(self, window, activate_time):
        if gdk.pointer_grab(window, True, gdk.BUTTON_PRESS_MASK 
                                          | gdk.BUTTON_RELEASE_MASK
                                          | gdk.POINTER_MOTION_MASK, 
                            None, None, activate_time) == 0:
                if gdk.keyboard_grab (window, True, activate_time) == 0:
                    return True
                else:
                    gdk.pointer_ungrab(activate_time)
                    return False
        return False


    def select_clicked(self, widget, data=None):
        # Temporarily grab pointer and keyboard on a window we know exists        
        if not self.popup_grab_on_window(widget.window, gtk.get_current_event_time()):
            print 'error during grab'
            return
        
        # set calendar date
        str = self.__date_entry.get_text()
        mtime = time.strptime(str, '%x')
        self.__calendar.select_month(mtime.tm_mon - 1, mtime.tm_year)
        self.__calendar.select_day(mtime.tm_mday)        
        
        # position and show popup window
        self.position_popup()
        self.__cal_popup.grab_add()
        self.__cal_popup.show()
        self.__calendar.grab_focus()
        
        # Now transfer our grabs to the popup window, this should always succed
        self.popup_grab_on_window(self.__cal_popup.window, gtk.get_current_event_time())


    def position_popup(self):
        req = self.__cal_popup.size_request()
        (x,y) = gdk.Window.get_origin(self.__date_button.window)

        x += self.__date_button.allocation.x
        y += self.__date_button.allocation.y
        bwidth = self.__date_button.allocation.width
        bheight = self.__date_button.allocation.height

        x += bwidth - req[0]
        y += bheight

        if x < 0: x = 0
        if y < 0: y = 0
        
        self.__cal_popup.move(x,y)


    def day_selected(self, widget, data=None):
        (year, month, day) = self.__calendar.get_date()
        month += 1        
        the_time = datetime.date(year, month, day)
        self.__date_entry.set_text(the_time.strftime('%x'))
        self.emit('date_changed', None)
        
        
    def day_selected_double_click(self, widget, data=None):
        self.hide_popup()


    def hide_popup(self):
        self.__cal_popup.hide()
        self.__cal_popup.grab_remove()


    def key_press_popup(self, widget, data=None):        
        # Todo, Fixme: what is the name of gdk.Escape? missing?
        if data == None or data.keyval != 65307:
            return False

        # Todo: does not work and what does it do anyway?
        # widget.stop_emission_by_name('key_press_event')
        self.hide_popup()
        return True


    # Todo: is this correct?
    def button_press_popup(self, widget, data=None):
        # We don't ask for button press events on the grab widget, so
        # if an event is reported directly to the grab widget, it must
        # be on a window outside the application (and thus we remove
        # the popup window). Otherwise, we check if the widget is a child
        # of the grab widget, and only remove the popup window if it
        # is not.
        if data == None or data.window == None:
            return False
            
        child = data.window.get_user_data()
        if child != widget:
            while child:
                if child == widget:
                    return False
                child = child.parent
                
        self.hide_popup()
        return True


    def delete_popup(self, widget, data=None):
        # Todo: when is this ever called??
        print 'delete_popup'
        hide_popup (gde);
        return TRUE;

    def time_selected(self, widget, data = None):
        it = self.__time_popup.get_active_iter()
        model = self.__time_popup.get_model()
        str = model.get_value(it,0)
        self.__time_entry.set_text(str)
        self.emit('time_changed', None);
        
        
    # Todo: get_properties
        # PROP_TIME
        # PROP_DATE_EDIT_FLAGS
        # PROP_LOWER_HOUR
        # PROP_UPPER_HOUR
        # PROP_INITIAL_TIME
    # Todo: set_properties
        # PROP_TIME
        # PROP_DATE_EDIT_FLAGS
        # PROP_LOWER_HOUR
        # PROP_UPPER_HOUR

class TimeTree(gtk.TreeStore):
    def __init__(self,lower,upper,use_24_format=True):
        gtk.TreeStore.__init__(self,gobject.TYPE_STRING)
        for h in range(lower,upper+1):
            the_time = datetime.time(h,0)
            if use_24_format:
                label = the_time.strftime('%H:%M')
            else:
                label = the_time.strftime('%I:%M %p')
            iter = self.insert(None,-1,[label])
            for m in range(15,60,15):
                the_time = datetime.time(h,m)
                if use_24_format:
                    label = the_time.strftime('%H:%M')
                else:
                    label = the_time.strftime('%I:%M %p')
                self.insert(iter,-1,[label])

# Test the dateedit widget
gobject.type_register(DateEdit)
