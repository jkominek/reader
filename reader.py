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

        quit = wx.MenuItem(main, 1001, '&Quit\tCtrl+Q')
        self.Bind(wx.EVT_MENU, self.OnQuit)
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
                                             agwStyle=CTC.TR_HIDE_ROOT)
        feed_list_sizer.Add(self.feed_list_ctrl, 1, flag=wx.EXPAND)
        feed_list_panel.SetSizer(feed_list_sizer)
        
        self.feed_list_ctrl.SetBackgroundColour('white')
        self.feed_root = self.feed_list_ctrl.AddRoot("Everything")
        tech = self.feed_list_ctrl.AppendItem(self.feed_root, "Technology")
        ars = self.feed_list_ctrl.AppendItem(tech, "Ars Technica")
        ars.url = "http://feeds.arstechnica.com/arstechnica/index"
        self.feed_list_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.FeedSelectionChanged)

        self.feed_list_ctrl.ExpandAllChildren(self.feed_root)

        right_panel = wx.Panel(top_splitter)
        right_sizer = wx.BoxSizer()
        right_splitter = wx.SplitterWindow(parent=right_panel,
                                           style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        right_sizer.Add(right_splitter, proportion=1, flag=wx.EXPAND)
        right_panel.SetSizer(right_sizer)

        web_panel = wx.Panel(right_splitter)
        web_sizer = wx.BoxSizer(wx.VERTICAL)
        web_toolbar = wx.ToolBar(web_panel)
        web_toolbar.AddTool(1, bitmap=wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))
        web_toolbar.AddTool(2, bitmap=wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        web_toolbar.Realize()
        web_toolbar.Bind(wx.EVT_TOOL, self.ToolbarHandler)
            
        feed_items_panel = wx.Panel(right_splitter)
        feed_items_sizer = wx.BoxSizer()
        self.feed_items_ctrl = UltimateListCtrl(feed_items_panel, agwStyle=wx.LC_REPORT|wx.LC_SINGLE_SEL)
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
        self.web_ctrl.Bind(wx.html2.EVT_WEBVIEW_TITLE_CHANGED, self.BrowserTitleChanged)
        
        right_splitter.SplitHorizontally(feed_items_panel,
                                         web_panel)
        
        top_splitter.SplitVertically(feed_list_panel, right_panel)
        top_splitter.SetSashPosition(WIDTH / 4)
        right_splitter.SetSashPosition(HEIGHT / 4)
        self.SetSizer(top_sizer)

        self.web_ctrl.LoadURL("about:blank")

    def FeedItemSelected(self, evt):
        index = evt.GetIndex()
        item = self.feed_items_ctrl.GetItem(index)
        data = item.GetData()

        print data
        
        content = data['content'][0]
        template = templates.get(content['type'], None)

        if template == None:
            self.web_ctrl.SetPage("unrenderable content type %s" % (content['type'],))
        else:
            kwargs = data.copy()
            kwargs['value'] = content['value']
            html = template.render(**kwargs)
            open("dump.html","w").write(html.encode("UTF-8"))
            self.web_ctrl.SetPage(html, '')
        
    def FeedSelectionChanged(self, evt):
        feed_url = evt.GetItem().url
        feed = feedparser.parse(feed_url)
        entries = feed.entries
        entries.sort(key=lambda e: e.published_parsed)
        self.feed_items_ctrl.DeleteAllItems()
        for e, i in zip(entries, range(0, len(entries))):
            index = self.feed_items_ctrl.InsertStringItem(sys.maxint, '')
            title = re.sub("\s+", " ", e['title'])
            self.feed_items_ctrl.SetStringItem(index, 1, title)
            self.feed_items_ctrl.SetItemData(index, e)
        
    def BrowserTitleChanged(self, evt):
        evt.GetString()
        
    def Navigating(self, evt):
        evt.Skip()
        
    def ToolbarHandler(self, evt):
        if evt.GetId() == 1:
            # back
            self.web_ctrl.GoBack()
        elif evt.GetId() == 2:
            # forward
            self.web_ctrl.GoForward()
        
    def OnQuit(self, evt):
        self.Close(True)
        self.Destroy()
        sys.exit(0)
        
frame = MainFrame()
frame.Show()
app.SetTopWindow(frame)
app.MainLoop()
