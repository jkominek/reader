#!/usr/bin/python

import sqlite3
import threading

connlock = threading.RLock()
conn = sqlite3.connect("reader.db")
cursor = conn.cursor()

def lock():
    connlock.acquire()
def unlock():
    connlock.release()

cursor.execute("select count(*) from sqlite_master where type='table' and name='configuration'")
conf_exists = bool(cursor.fetchone()[0])

if not conf_exists:
    cursor.execute("""
create table configuration (
  key text primary key,
  value text
)""")
    cursor.execute("insert into configuration values (?, ?)", ('dbversion', 0))

    cursor.execute("""
create table folders (
  id integer primary key,
  name text,
  parent integer,
  ordering integer,
  foreign key(parent) references folders(id)
)
""")
    cursor.execute("insert into folders (name, parent) values (null, null)")

    cursor.execute("""
create table feeds (
  id integer primary key,
  name text,
  folder integer,
  ordering integer,
  url text,
  last_checked datetime,
  foreign key(folder) references folders(id)
)
""")

    cursor.execute("""
create table feeditems (
  feed integer not null,
  retrieved datetime,
  seen boolean default 0,
  item blob,
  foreign key(feed) references feeds(id)
)
""")

    conn.commit()

def conf_get(key):
    row = None
    try:
        connlock.acquire()
        cursor.execute("select value from configuration where key=?", (key,))
        row = cursor.fetchone()
    finally:
        connlock.release()

    if row == None:
        return None
    else:
        return row[0]

def conf_set(key, val):
    try:
        connlock.acquire()
        cursor.execute("insert or replace into configuration (key, value) values (?, ?)", (key, val))
    finally:
        connlock.release()

if int(conf_get('dbversion')) != 0:
    raise StandardError, "Don't know how to use or upgrade this version of the database"

def query(q, args=()):
    try:
        connlock.acquire()
        cursor.execute(q, args)
        data = list(cursor)
        return data
    finally:
        connlock.release()

def insert(q, args=()):
    try:
        connlock.acquire()
        cursor.execute(q, args)
        conn.commit()
        return cursor.lastrowid
    finally:
        connlock.release()
