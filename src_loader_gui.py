import gtk
from dateentry import DateEdit

class LoadSourceDialog(gtk.Dialog):
    def __init__(self,sources):
        gtk.Dialog.__init__(self,title=_("Load source"))
        table = gtk.Table(5,2)
        lbl_file = gtk.Label()
        lbl_file.set_markup("<b>"+_("File")+":</b>")
        lbl_file.set_alignment(0.0,0.5)
        self.openw = gtk.FileChooserButton(title=_("Load source"))
        
        lbl_name = gtk.Label()
        lbl_name.set_markup("<b>"+_("Name")+":</b>")
        lbl_name.set_alignment(0.0,0.5)

        self.fn_entry = gtk.Entry()

        lbl_filetype = gtk.Label()
        lbl_filetype.set_markup("<b>"+_("File type")+":</b>")
        lbl_filetype.set_alignment(0.0,0.5)
        
        table.attach(lbl_file,0,1,0,1,gtk.SHRINK|gtk.FILL)
        table.attach(self.openw,1,2,0,1)
        table.attach(lbl_name,0,1,1,2,gtk.SHRINK|gtk.FILL)
        table.attach(self.fn_entry,1,2,1,2)
        table.attach(lbl_filetype,0,1,2,3,gtk.SHRINK|gtk.FILL)

        self.file_type_option = []
        line = 2
        group = None
        for src in sources:
            opt = gtk.RadioButton(group=group,label=src.description())
            opt.connect('toggled',lambda s: self.update_hide_show())
            table.attach(opt,1,2,line,line+1)
            opt_box,wids = self.construct_opts(src)
            table.attach(opt_box,1,2,line+1,line+2,xpadding=20)
            self.file_type_option.append((src,opt,opt_box,wids))
            if group is None:
                group = opt
            line+=2
        self.child.add(table)
        self.add_buttons(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK)
        self.update_hide_show()
        self.show_all()
    def update_hide_show(self):
        for src,wid,box,opts in self.file_type_option:
            box.set_sensitive(wid.get_active())
    def construct_opts(self,src):
        box = gtk.Table(columns=2)
        line = 0
        widgets = {}
        for name,tp,args,descr in src.arg_description():
            lbl_descr = gtk.Label()
            lbl_descr.set_markup(descr+":")
            lbl_descr.set_alignment(0.0,0.5)
        
            box.attach(lbl_descr,0,1,line,line+1,gtk.SHRINK|gtk.FILL)
            
            if tp == 'time':
                widget = DateEdit(show_time=True,use_24_format=True)
                box.attach(widget,1,2,line,line+1)
                line += 1
            elif tp == 'choice':
                group = None
                choices = []
                for descr,val in args:
                    but = gtk.CheckButton(label=descr)
                    box.attach(but,1,2,line,line+1)
                    choices.append((but,val))
                    line+=1
                widget = choices
            else:
                widget = None
                line += 1
            widgets[name] = widget
        return (box,widgets)
    def get_source(self):
        fn = self.openw.get_filename()
        dname = self.fn_entry.get_text()
        for src,wid,box,opts in self.file_type_option:
            if wid.get_active():
                res = {}
                for name,tp,args,descr in src.arg_description():
                    if tp == 'time':
                        res[name] = opts[name].get_datetime()
                    elif tp == 'choice':
                        res_set = set()
                        for (wid,val) in opts[name]:
                            if wid.get_active():
                                res_set.add(val)
                        res[name] = res_set
                return src.from_file(fn,dname,**res)
