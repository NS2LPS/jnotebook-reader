import ijson
import json
import os
import typing

from lib import config

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
    return tags or []

try:
    with open('tag_parser_db.json','r') as f:
        dbmain = json.load(f)
except:
    dbmain = dict()

id = 0
for year in os.scandir(__base(id)):
    if year.is_dir() and year.name.isdecimal():
        db = dbmain.get(year.name, dict())
        for entry in os.scandir(year.path):
            if not entry.name.startswith('.') and entry.is_dir() and entry.name.count('_')==2:
                for file in os.scandir(entry.path):
                    if file.is_file() and file.name.endswith('.ipynb'):
                        if file.path in db:
                            entry = db[file.path]
                            mtime = entry['mtime']
                        else:
                            entry = dict()
                            db[file.path] = entry
                            mtime = 0.
                        if file.stat.st_mtime != mtime:
                            entry['tags'] =  get_tags(file.name)
                            entry['mtime']= file.stat.st_mtime

with open('tag_parser_db.json','w') as f:
    json.dump(dbmain,f)


