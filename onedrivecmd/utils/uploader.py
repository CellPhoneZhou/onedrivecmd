#!/usr/bin/env python
# coding:utf-8
# Author:  Beining --<i@cnbeining.com>
# Purpose: File uploader for onedrivecmd
# Created: 09/24/2016

import json
from progress.bar import Bar
import requests
from collections import OrderedDict

try:
    from static import *
    from helper_file import *
    from helper_item import *
    from session import *
except ImportError:
    from .static import *
    from .helper_file import *
    from .helper_item import *
    from .session import *


## Upload related
def upload_one_piece(uploadUrl = '', token = '', source_file = '', range_this = [], file_size = 0,
                     requests_session = None):
    """list->int

    Post one piece of file to Onedrive via API.
    """
    if requests_session is None:
        requests_session = requests.Session()
        # this is how everything calculated
    content_length = range_this[1] - range_this[0] + 1

    file_piece = file_read_seek_len(source_file, range_this[0], content_length)

    # Since we are setting up the header by ourselves, we must make sure
    # the DATA TYPE of the headers are correct (i.e., everything in string)
    # or sometimes requests is not able to do
    # auto data type converting.
    # On OS X everything works fine; Ubuntu would throw an
    # Header value 10485760 must be of type str or bytes, not <type 'int'>
    headers = {'Authorization': 'bearer {access_token}'.format(access_token = token),
               'Content-Range': 'bytes {start}-{to}/{total}'.format(start = range_this[0],
                                                                    to = range_this[1],
                                                                    total = str(file_size)),
               'Content-Length': str(content_length), }

    req = requests_session.put(uploadUrl,
                               data = file_piece,
                               headers = headers)

    return req.status_code


def upload_self(client, source_file = '', dest_path = '', chunksize = 10247680):
    """OneDriveClient, str, str, int->Bool

    Upload a file via the API, instead of the SDK.

    Ref: https://dev.onedrive.com/items/upload_post.htm
    """
    ## get upload URL
    if not dest_path.endswith('/'):
        dest_path += '/'

    if source_file.endswith('/'):
        source_file=source_file[:-1]

    # check if it's a file
    if os.path.isfile(source_file):
        # Prepare API call
        # token expires in 3600s, just refresh it if TTL<50min.
        if token_time_to_live(client) < 50*60:
            refresh_token(client)

        dest_path = path_to_remote_path(dest_path) + '/' + path_to_name(source_file)
        # Stamps
        print(" ")
        os.system("echo [\"$(date +%F\\ %T)\"]")
        print("\033[36m"+source_file+"\033[0m ==> \033[36mod:"+dest_path+"\033[0m")

        info_json = json.dumps({'item': OrderedDict([('@name.conflictBehavior', 'rename'), ('name', path_to_name(source_file))])})
    
        api_url = client.base_url + 'drive/root:{dest_path}:/upload.createSession'.format(dest_path = dest_path)
    
        req = requests.post(api_url,
                            data = info_json,
                            headers = {'Authorization': 'bearer {access_token}'.format(access_token = get_access_token(client)),
                                       'content-type': 'application/json'})
    
        if req.status_code > 201:
            print("\033[31mRequest error:\033[0m "+req.json()['error']['message'])
            return False
    
        req = convert_utf8_dict_to_dict(req.json())
    
        uploadUrl = req['uploadUrl']
    
        # filesize cannot > 10GiB
        file_size = os.path.getsize(source_file)
    
        # print(file_size)
    
        range_list = [[i, i + chunksize - 1] for i in range(0, file_size, chunksize)]
        range_list[-1][-1] = file_size - 1
    
        # Upload with a progress bar
        bar = Bar('Uploading', max = len(range_list), suffix = '%(percent).1f%% - %(eta)ds')
        bar.next()  # nessesery to init the Bar
    
        # Session reuse when uploading, hopefully will kill some overhead
        requests_session = requests.Session()
    
        for i in range_list:
            upload_one_piece(uploadUrl = uploadUrl, token = get_access_token(client), source_file = source_file,
                             range_this = i, file_size = file_size, requests_session = requests_session)
            bar.next()
    
        bar.finish()
    # So it's a dir, upload it recursively.
    else:
        new_dest_path=dest_path+path_to_name(source_file)+"/"
        for new_source_file in os.listdir(source_file):
            upload_self(client, source_file+"/"+new_source_file, new_dest_path, chunksize)
    return True


if __name__ == '__main__':
    pass
