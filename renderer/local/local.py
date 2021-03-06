# Copyright 2020 LINE Corporation
#
# LINE Corporation licenses this file to you under the Apache License,
# version 2.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at:
#
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from common.renderer import Renderer
from common.const import const
from os.path import join, getmtime, getsize, exists
from os import scandir
import typing
from datetime import datetime
import hashlib
from lib.config import config
from lib.utils import format_date, format_size
from flask import request
from flask_api import status
import os
import calendar


class LocalRenderer(Renderer):
    def __read_file(self, file):
        with open(file, "rb") as targetfile:
            while 1:
                data = targetfile.read(8192)
                if not data:
                    break
                yield data

    def __read_file_data(self, file):
        reader = open(file, "rb")
        data = reader.read()
        reader.close()
        return data

    def __directory(self, id):
        directories = config["storage"]["directories"]
        if isinstance(directories, typing.List):
            return directories[int(id)]
        elif isinstance(directories, typing.Dict):
            return directories.get(id)
        else:
            return directories

    def __base(self, id):
        dir = os.environ.get("JNOTEBOOK_READER_DIR")
        if not dir:
            return self.__directory(id)
        else:
            return dir.split(",")[int(id)]

    def __list(self, path):
        result = []
        for entry in scandir(path):
            if entry.name.startswith('.'):
                continue
            if entry.is_dir():
                result.append(
                    {
                        "name": entry.name,
                        "size": 0,
                        "rawSize": 0,
                        "lastModified": "-",
                        "type": "Folder",
                    }
                )
            else:
                if entry.name.endswith(('.ipynb','.py','.md','.jpeg','.jpg','.png','.gif','.html')):
                    result.append(
                        {
                            "name": entry.name,
                            "size": format_size(getsize(entry.path)),
                            "rawSize": getsize(entry.path),
                            "lastModified": format_date(self.__last_modified(entry.path)),
                            "type": "File",
                        }
                    )
        result.sort(key=lambda item: item['name'])
        return result

    def __last_modified(self, file):
        return datetime.fromtimestamp(getmtime(file))

    def __etag(self, file):
        hash_md5 = hashlib.md5()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def __check_modified(self, file):
        if_modified_since = request.headers.get("If-Modified-Since", "")
        last_modified = self.__last_modified(file).strftime("%a, %d %b %Y %H:%M:%S %Z")
        if last_modified.strip() == if_modified_since.strip():
            return False, last_modified
        return True, last_modified

    def render_directory(self, id, prefix):
        return self.__list(join(self.__base(id), prefix))

    def render_file(self, id, prefix, type):
        file = join(self.__base(id), prefix)
        if not exists(file):
            return {"status": status.HTTP_404_NOT_FOUND}
        modified, last_modified = self.__check_modified(file)

        if not modified:
            return {"status": status.HTTP_304_NOT_MODIFIED}
        content = self.__read_file_data(file)
        if type == const.NOTEBOOK_TYPE:
            (content, resources) = self.render_notebook(content)
        if type == const.MARKDOWN_TYPE:
            content = self.render_markdown(content)
        return {
            "content": content,
            "etag": self.__etag(file),
            "lastModified": last_modified,
        }

    def render_year(self, id, year):
        months = dict([(m,[]) for m in range(1,13)])
        for entry in scandir(join(self.__base(id), year)):
            if not entry.name.startswith('.') and entry.is_dir() and entry.name.count('_')==2:
                month = int(entry.name.split('_')[1])
                month_files = months[month]
                for file in scandir(entry.path):
                    if file.is_file() and file.name.endswith('.ipynb'):
                        month_files.append({'date':entry.name.replace('_','-'),
                        'date_path': join(year, entry.name),
                        'name':file.name, 
                        'path': join(year, entry.name, file.name) })
        content = [ {'number':m, 'name':calendar.month_name[m], 'files':files } for m,files in months.items() if files]
        for c in content:
            c['files'].sort(key=lambda item: (item['date'],item['name']))
        content.sort(key=lambda item : item['number'])
        return content
        

    def render_download(self, id, prefix):
        file = join(self.__base(id), prefix)
        if not exists(file):
            return {"status": status.HTTP_404_NOT_FOUND}
        return {"stream": self.__read_file(join(self.__base(id), prefix))}
