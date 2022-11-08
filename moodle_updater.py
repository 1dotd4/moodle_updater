#!/usr/bin/env python3

# moodle_updater.py - Send diff of moodle update on telegram channel.
# Copyright (c) 2022, 1dotd4 <https://github.com/1dotd4/moodle_updater>.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import tomli
import argparse
import requests
from bs4 import BeautifulSoup

def die(*a):
    print(*a, file=sys.stderr)
    exit(1)

# load config, halt otherwise
config_file = None
parser = argparse.ArgumentParser(prog = 'moodle_updater',
                                 description = 'I watch moodle and report on telegram')
parser.add_argument('-c', dest='config_file', help="")
parsed = parser.parse_args()
if parsed.config_file == None:
    parser.print_help()
    exit(1)
with open(parsed.config_file, mode="rb") as fp:
    config = tomli.load(fp)
course_id = config['course_id']
guest_pass = config['guest_pass']
root_url = config['root_url']
telegram_token = config['telegram_token']
telegram_channel = config['telegram_channel']
save_file = config['save_file']
if course_id == None:
    die("Required course_id config variable")
elif guest_pass == None:
    die("Required guest_pass config variable")
elif root_url == None:
    die("Required root_url config variable")
elif telegram_token == None:
    die("Required telegram_token config variable")
elif save_file == None:
    die("Required save_file config variable")

# begin of funny functions

def fetch_new_list():
    s = requests.Session()
    r = s.get(root_url + '/course/view.php?id=' + course_id)
    parsed_html = BeautifulSoup(r.text, 'html.parser')
    form = parsed_html.body.find('form', attrs={'class': 'mform', 'method': 'post'})
    url = form['action']
    payload = {}
    for i in form.find_all('input'):
        payload[i['name']] = i['value']
    payload['guestpassword'] = guest_pass
    # performs login and it will be redirected to the course we want to monitor
    r = s.post(url, data=payload)
    parsed_html = BeautifulSoup(r.text, 'html.parser')
    # extract only the activity button and then the name of the activity we want
    activities = []
    for a in parsed_html.find_all('li', attrs={'class': ['activity', 'activity-wrapper', 'resource', 'modtype_resource']}):
        instanceTag = a.find('span', attrs={'class', 'instancename'})
        if instanceTag != None:
            activities.append(list(instanceTag.stripped_strings)[0])
    return activities

def load_list():
    if os.path.exists(save_file) and os.path.isfile(save_file):
        with open(save_file, "r") as f:
            lines = f.read().splitlines()
            return lines
    else:
        return []

def save_list(l):
    with open(save_file, "w") as f:
        f.write('\n'.join(l))

# Begin of diff stuff

# Adapted from https://rosettacode.org/wiki/Longest_common_subsequence#Dynamic_Programming_7
def lcs(a, b):
    lengths = [[0] * (len(b)+1) for _ in range(len(a)+1)]
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            if x == y:
                lengths[i+1][j+1] = lengths[i][j] + 1
            else:
                lengths[i+1][j+1] = max(lengths[i+1][j], lengths[i][j+1])
    # read a substring from the matrix
    result = []
    j = len(b)
    for i in range(1, len(a)+1):
        if lengths[i][j] != lengths[i-1][j]:
            result += [a[i-1]]
    return result

# Followed the guideline https://en.wikipedia.org/wiki/Diff#Algorithm
def diff(a, b):
    """
    Returns a list of tuples where
    - the first element is False if deleted, and True if added
    - the second element is the element modified
    """
    d = []
    c = lcs(a, b)
    i, j = 0, 0
    for m in range(len(c)):
        while i < len(a) and a[i] != c[m]:
            d.append((False, a[i]))
            i += 1
        while j < len(b) and b[j] != c[m]:
            d.append((True, b[j]))
            j += 1
        i += 1
        j += 1
    while i < len(a):
        d.append((False, a[i]))
        i += 1
    while j < len(b):
        d.append((True, b[j]))
        j += 1
    return d

# Pretty print for screen
def pretty_print_diff(d):
    return '\n'.join([('+' if l[0] else '-') + ' ' + l[1] for l in d])

# Send to telegram channel
def send_message(text):
    payload = {'chat_id': telegram_channel, 'text': text}
    r = requests.post('https://api.telegram.org/bot' + telegram_token + '/sendMessage', data=payload)
    # print(r.text)

# Old test for diff algo
# new = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'i', 'j', 'k', 'r', 'x', 'y', 'z', 'u']
# old = ['a', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'q', 'z']
# print(pretty_print_diff(diff(old, new)))

# Should I wrap this into a main function?
new = fetch_new_list()
old = load_list()
d = diff(old, new)
if len(d) > 0:
    # only if we have a difference we will send the message
    send_message(pretty_print_diff(d))
    save_list(new)

