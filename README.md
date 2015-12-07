I've been using local RSS readers for a lotta years now. I paid money
for one once. They've all been obnoxious in some way or another. Most
recently, Liferea has started crashing whenever I tried to open the
properties on a feed. Ok, maybe I could fix that. But it annoys me in
a dozen other ways, that haven't improved over the years I've been
using it. 

So I'm finally going to work on my own RSS reader.

I'm running with Python for this because:
* Most of the GUI work I've ever done has been using wxPython
* I've got some experience writing Python that handles errors well, and
  fails cleanly. And for something non-critical like an RSS reader, that's
  good enough.
* The wxPython webkit wrapper works for me.
* feedparser, jinja2, etc

Ways in which I plan on making this superior to all other feed readers
I've used:

* The item content pane will be the result of a(n optionally per-feed)
  jinja2 template, so you can customize how the items are rendered by
  adjusting the HTML/CSS of the template, or invoking arbitrary Python.
* Feed will not be just be URL with maybe a filter program associated.
  Feeds will be chunks of code that do whatever you want, and return
  feed-like data. (But if your feed is a bare URL, it'll be run
  through feedparser, so that the common case remains easy.)
* Network IO will not freeze the UI.
* The damnable accelerator keys will work consistently, regardless of
  which stupid subpanel you happen to accidentally give focus to.
* Screen space will not be wasted on unnecessary status bars, tool bars,
  etc.

Suggestions for goals, and a project name are welcome.

-- Jay Kominek
