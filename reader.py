#!/usr/bin/python

import os
import wx
import wx.html2
import sys
from wx.lib.agw.customtreectrl import CustomTreeCtrl
import wx.lib.agw.customtreectrl as CTC
from wx.lib.agw.ultimatelistctrl import UltimateListCtrl
import wx.lib.agw.ultimatelistctrl as ULC
import feedparser
import re
import jinja2
from time import mktime
from datetime import datetime

import database

ID_NEWFOLDER  = 1001
ID_NEWFEED    = 1002

ID_FULLSCREEN = 1501
ID_QUIT       = 1999

ID_FI_PROPERTIES = 2001
ID_FI_DELETE     = 2500

app = wx.App(False)

WIDTH = 800
HEIGHT = 600

templateLoader = jinja2.FileSystemLoader( searchpath="templates" )
templateEnv = jinja2.Environment( loader=templateLoader )
templates = { }
for f in os.listdir("templates"):
    mime = "/".join(f.split("_"))
    templates[mime] = templateEnv.get_template(f)

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,
                          parent=None,
                          title="RSS Reader",
                          size=(800, 600))
        self.menu_bar = wx.MenuBar()
        main = wx.Menu()

        newfolder = wx.MenuItem(main, ID_NEWFOLDER, 'New Folder')
        self.Bind(wx.EVT_MENU, self.NewFolder, id=ID_NEWFOLDER)
        main.AppendItem(newfolder)
        
        newfeed = wx.MenuItem(main, ID_NEWFEED, '&New Feed')
        self.Bind(wx.EVT_MENU, self.NewFeed, id=ID_NEWFEED)
        main.AppendItem(newfeed)
        
        self.is_fullscreen = False
        fullscreen = wx.MenuItem(main, ID_FULLSCREEN, 'Full Screen...\tF11')
        self.Bind(wx.EVT_MENU, self.FullScreen, id=ID_FULLSCREEN)
        main.AppendItem(fullscreen)
        
        quit = wx.MenuItem(main, ID_QUIT, '&Quit\tCtrl+Q')
        self.Bind(wx.EVT_MENU, self.Quit, id=ID_QUIT)
        main.AppendItem(quit)
        
        self.menu_bar.Append(main, '&Main')

        self.SetMenuBar(self.menu_bar)
        
        top_sizer = wx.BoxSizer()
        top_splitter = wx.SplitterWindow(parent=self,
                                         style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        top_sizer.Add(top_splitter, proportion=1, flag=wx.EXPAND)

        feed_list_panel = wx.Panel(top_splitter)
        feed_list_sizer = wx.BoxSizer()
        self.feed_list_ctrl = CustomTreeCtrl(feed_list_panel,
                                             agwStyle=CTC.TR_HIDE_ROOT|CTC.TR_HAS_BUTTONS)
        feed_list_sizer.Add(self.feed_list_ctrl, 1, flag=wx.EXPAND)
        feed_list_panel.SetSizer(feed_list_sizer)
        
        self.feed_list_ctrl.SetBackgroundColour('white')
        self.feed_root = self.feed_list_ctrl.AddRoot("Everything")
        self.feed_list_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.FeedSelectionChanged)
        self.feed_list_ctrl.Bind(CTC.EVT_TREE_ITEM_MENU, self.FeedItemMenu)

        self.feed_list_ctrl.ExpandAllChildren(self.feed_root)

        right_panel = wx.Panel(top_splitter)
        right_sizer = wx.BoxSizer()
        right_splitter = wx.SplitterWindow(parent=right_panel,
                                           style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        right_sizer.Add(right_splitter, proportion=1, flag=wx.EXPAND)
        right_panel.SetSizer(right_sizer)

        web_panel = wx.Panel(right_splitter)
        web_sizer = wx.BoxSizer(wx.VERTICAL)
        self.web_toolbar = web_toolbar = wx.ToolBar(web_panel)
        web_toolbar.AddTool(1, bitmap=wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))
        web_toolbar.AddTool(2, bitmap=wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        web_toolbar.AddTool(3, bitmap=wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
        web_toolbar.AddTool(4, bitmap=wx.ArtProvider.GetBitmap(wx.ART_COPY))
        web_toolbar.AddTool(5, bitmap=wx.ArtProvider.GetBitmap(wx.ART_PASTE))

        self.ignore_url_change = False
        self.url_ctrl = wx.TextCtrl(web_toolbar, style=wx.TE_PROCESS_ENTER)
        web_toolbar.AddControl(self.url_ctrl)
        web_toolbar.Realize()
        web_toolbar.Bind(wx.EVT_TOOL, self.ToolbarHandler)
        self.url_ctrl.Bind(wx.EVT_TEXT_ENTER, self.ToolbarURLSet)
            
        feed_items_panel = wx.Panel(right_splitter)
        feed_items_sizer = wx.BoxSizer()
        self.feed_items_ctrl = UltimateListCtrl(feed_items_panel, agwStyle=wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.unseen_feed_item_font = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False)
        self.seen_feed_item_font = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False)
        
        feed_items_sizer.Add(self.feed_items_ctrl, 1, flag=wx.EXPAND)
        feed_items_panel.SetSizer(feed_items_sizer)
        self.feed_items_ctrl.InsertColumn(0, "Date")
        self.feed_items_ctrl.InsertColumn(1, "Title")
        def adjust_title_width(evt):
            x, y = self.feed_items_ctrl.GetSize()
            self.feed_items_ctrl.SetColumnWidth(1, x - self.feed_items_ctrl.GetColumnWidth(0) - wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X) )
            evt.Skip()
        self.feed_items_ctrl.Bind(wx.EVT_SIZE, adjust_title_width)
        self.feed_items_ctrl.Bind(wx.EVT_LIST_COL_END_DRAG, adjust_title_width)
        self.feed_items_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.FeedItemSelected)
        
        web_sizer.Add(web_toolbar, proportion=0, flag=wx.EXPAND)
        self.web_ctrl = wx.html2.WebView.New(web_panel)
        web_sizer.Add(self.web_ctrl, proportion=1, flag=wx.EXPAND)
        web_panel.SetSizer(web_sizer)
        self.web_ctrl.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self.Navigating)
        self.web_ctrl.Bind(wx.html2.EVT_WEBVIEW_NAVIGATED, self.Navigated)
        self.web_ctrl.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.Loaded)
        self.web_ctrl.Bind(wx.html2.EVT_WEBVIEW_TITLE_CHANGED, self.BrowserTitleChanged)
        
        right_splitter.SplitHorizontally(feed_items_panel,
                                         web_panel)
        
        top_splitter.SplitVertically(feed_list_panel, right_panel)
        top_splitter.SetSashPosition(WIDTH / 4)
        right_splitter.SetSashPosition(HEIGHT / 4)
        self.SetSizer(top_sizer)

        self.LoadFoldersAndFeeds()

        self.web_ctrl.LoadURL("about:blank")

    def NewFolder(self, evt):
        dialog = wx.TextEntryDialog(self, "Name of folder...", "New Folder")
        res = dialog.ShowModal()
        if res == wx.CANCEL:
            return
        name = dialog.GetValue().strip()
        if len(name)>0:
            id = database.insert("insert into folders (name, parent, ordering) values (?, ?, (select 1+max(ordering) from folders where parent=?))", (name, 1, 1))
            self.AddFolderToTree(id, 1, name)

    def NewFeed(self, evt):
        dialog = wx.TextEntryDialog(self, "Feed URL...", "New Feed")
        res = dialog.ShowModal()
        if res == wx.CANCEL:
            return
        url = dialog.GetValue().strip()

        selected_item = self.feed_list_ctrl.GetSelection()
        if selected_item.is_folder:
            dest_folder = selected_item.db_id
        else:
            dest_folder = selected_item.in_folder
            
        if len(url)>0:
            id = database.insert("insert into feeds (name, folder, ordering, url) values (?, ?, (select 1+max(ordering) from feeds where folder=?), ?)", ("feed", dest_folder, dest_folder, url))
            self.AddFeedToTree(id, dest_folder, "feed", url)

    def AddFeedToTree(self, id, folder, name, url):
        item = self.feed_list_ctrl.AppendItem(self.folder_mapping[folder], name)
        item.url = url
        item.db_id = id
        item.name = name
        item.is_folder = False
        item.in_folder = folder

    def AddFolderToTree(self, id, parent, name):
        mapping = self.folder_mapping
        item = self.feed_list_ctrl.AppendItem(mapping[parent], name)
        mapping[id] = item
        item.name = name
        item.is_folder = True
        item.in_folder = parent
        item.db_id = id

    def LoadFoldersAndFeeds(self):
        try:
            database.lock()

            folders = database.query("select id, parent, name from folders order by ordering")
            self.folder_mapping = mapping = { }
            noparent = [ ]
            for folder in folders:
                if folder[2] == None:
                    mapping[folder[0]] = self.feed_root
                else:
                    noparent.append(folder)
            while len(noparent) > 0:
                stillnoparent = [ ]
                for folder in noparent:
                    if mapping.has_key(folder[1]):
                        self.AddFolderToTree(*folder)
                    else:
                        stillnoparent.append(folder)
                noparent = stillnoparent

            feeds = database.query("select id, folder, name, url from feeds order by ordering")
            for feedinfo in feeds:
                self.AddFeedToTree(*feedinfo)
        finally:
            database.unlock()

    def FeedItemSelected(self, evt):
        index = evt.GetIndex()
        self.feed_items_ctrl.SetItemFont(index, self.seen_feed_item_font)
        item = self.feed_items_ctrl.GetItem(index)
        data = item.GetData()

        content = data['content'][0]
        template = templates.get(content['type'], None)

        if template == None:
            self.web_ctrl.SetPage("unrenderable content type %s" % (content['type'],))
        else:
            kwargs = data.copy()
            kwargs['value'] = content['value']
            html = template.render(**kwargs)
            #open("dump.html","w").write(html.encode("UTF-8"))
            self.web_ctrl.SetPage(html, '')

    def FeedItemMenu(self, evt):
        item = evt.GetItem()
        popup = wx.Menu()
        popup.Append(ID_FI_PROPERTIES, 'Properties')
        popup.Append(ID_FI_DELETE, 'Delete')
        self.feed_list_ctrl.Bind(wx.EVT_MENU, self.FeedItemProperties(item), id=ID_FI_PROPERTIES)
        self.feed_list_ctrl.Bind(wx.EVT_MENU, self.FeedItemDelete(item), id=ID_FI_DELETE)
        self.feed_list_ctrl.PopupMenu(popup)

    def FeedItemProperties(self, item):
        def handler(evt):
            print "properties", item.name
        return handler

    def FeedItemDelete(self, item):
        def handler(evt):
            print "delete", item.name
        return handler

    def FeedSelectionChanged(self, evt):
        selected_item = evt.GetItem()
        if selected_item.is_folder:
            # TODO
            # needs some generalization with below, but show the items
            # from all the folder's feeds
            pass
        else:
            feed_url = selected_item.url
            feed = feedparser.parse(feed_url)
            entries = feed.entries
            entries.sort(key=lambda e: e.published_parsed)
            feed_items = self.feed_items_ctrl
            feed_items.DeleteAllItems()
            for e, i in zip(entries, range(0, len(entries))):
                index = feed_items.InsertStringItem(sys.maxint, datetime.fromtimestamp(mktime(e.published_parsed)).isoformat())
                title = re.sub("\s+", " ", e['title'])
                feed_items.SetStringItem(index, 1, title)
                feed_items.SetItemData(index, e)
                feed_items.SetItemFont(index, self.unseen_feed_item_font)
        
    def BrowserTitleChanged(self, evt):
        evt.GetString()
        
    def Navigating(self, evt):
        evt.Skip()
        
    def Navigated(self, evt):
        self.web_toolbar.EnableTool(1, self.web_ctrl.CanGoBack())
        self.web_toolbar.EnableTool(2, self.web_ctrl.CanGoForward())

    def Loaded(self, evt):
        url = evt.GetURL()
        if type(url) in (str, unicode) and len(url)>=4:
            try:
                self.ignore_url_change = True
                self.url_ctrl.SetValue(url)
            except e:
                print e
            finally:
                self.ignore_url_change = False
        
    def ToolbarHandler(self, evt):
        if evt.GetId() == 1:
            # back
            self.web_ctrl.GoBack()
        elif evt.GetId() == 2:
            # forward
            self.web_ctrl.GoForward()
        elif evt.GetId() == 3:
            # stop
            self.web_ctrl.Stop()
        elif evt.GetId() == 4:
            # copy
            url = wx.URLDataObject()
            url.SetURL(self.web_ctrl.GetCurrentURL())
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(url)
            wx.TheClipboard.Close()
        elif evt.GetId() == 5:
            # paste
            url = wx.URLDataObject()
            wx.TheClipboard.Open()
            wx.TheClipboard.GetData(url)
            wx.TheClipboard.Close()
            self.web_ctrl.LoadURL(url.GetURL())

    def ToolbarURLSet(self, evt):
        if not self.ignore_url_change:
            url = self.url_ctrl.GetValue()
            if not re.match("^([a-z]+):", url):
                url = "http://" + url
            self.web_ctrl.LoadURL(url)
            
    def Quit(self, evt):
        self.Close(True)
        self.Destroy()
        sys.exit(0)

    def FullScreen(self, evt):
        self.is_fullscreen = not self.is_fullscreen
        self.ShowFullScreen(self.is_fullscreen)
        
frame = MainFrame()
frame.Show()
app.SetTopWindow(frame)
app.MainLoop()
