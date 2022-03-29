#!/home/ns2-manip/miniconda3/envs/jnotebook-reader/bin/python
# -*- coding: utf-8 -*-

import ijson
import json
import os
import typing
import time

from lib.config import config

def __directory(id):
    directories = config["storage"]["directories"]
    if isinstance(directories, typing.List):
        return directories[int(id)]
    elif isinstance(directories, typing.Dict):
        return directories.get(id)
    else:
        return directories

def __base(id):
    dir = os.environ.get("JNOTEBOOK_READER_DIR") 
    if not dir:
        return __directory(id)
    else:
        return dir.split(",")[int(id)]

def get_tags(fname):
    with open(fname,'r') as f:
        tags = ijson.items(f, 'cells.item.metadata.tags')
        return [x for x in tags if x]

try:
    with open('tag_parser_db.json','r') as f:
        dbmain = json.load(f)
except:
    dbmain = dict()

id = 0
tstart = time.time()
files_total = 0
files_modified = 0
for year in os.scandir(__base(id)):
    if year.is_dir() and year.name.isdecimal():
        if year.name in dbmain:
            db = dbmain[year.name]
        else:
            db = dict()
            dbmain[year.name] = db
        for entry in os.scandir(year.path):
            if not entry.name.startswith('.') and entry.is_dir() and entry.name.count('_')==2:
                for file in os.scandir(entry.path):
                    if file.is_file() and file.name.endswith('.ipynb'):
                        files_total += 1
                        if file.path in db:
                            entry = db[file.path]
                            mtime = entry['mtime']
                        else:
                            entry = dict()
                            db[file.path] = entry
                            mtime = 0
                        if file.stat().st_mtime > mtime+1:
                            files_modified += 1
                            entry['tags'] =  get_tags(file.path)
                            entry['mtime']= int(file.stat().st_mtime)

with open('tag_parser_db.json','w') as f:
    json.dump(dbmain,f)

print(files_total,'files parsed in',int(time.time()-tstart),'s.')
print('Found',files_modified,'modified files.')
