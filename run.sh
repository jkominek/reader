#!/bin/sh

# This is dumb.
# https://bugs.launchpad.net/ubuntu/+source/wxwidgets3.0/+bug/1388847

export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libwx_gtk2u_webview-3.0.so.0 

./reader.py
