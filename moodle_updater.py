#!/usr/bin/env python3

# moodle_updater.py - Send notification update of changes of moodle content on a telegram channel.
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

## begin of funny functions
def fetch_new_list(root_url, course_id, guest_pass):
    s = requests.Session()
    r = s.get(root_url + '/course/view.php?id=' + course_id)
    parsed_html = BeautifulSoup(r.text, 'html.parser')
    form = parsed_html.body.find('form', attrs={'class': 'mform', 'method': 'post'})
    url = form['action']
    payload = {}
    for input_tag in form.find_all('input'):
        payload[input_tag['name']] = input_tag['value']
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

def load_list(filename):
    try:
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            return lines
    except Exception as e:
        print('Was not able to read ' + filename + ', will try to create one.')
        return []

def save_list(filename, new_list):
    try:
        with open(filename, "w") as f:
            f.write('\n'.join(new_list))
    except Exception:
        die('Was not able to write ' + filename + ' file.')

## Begin of diff stuff
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
def pretty_print_diff(deltas):
    return '\n'.join([('+' if line[0] else '-') + ' ' + line[1] for line in deltas])

# Send to telegram channel
def send_message(telegram_token, telegram_channel, text):
    payload = {'chat_id': telegram_channel, 'text': text}
    r = requests.post('https://api.telegram.org/bot' + telegram_token + '/sendMessage', data=payload)
    # print(r.text)

# Test for diff algo
def test_diff():
    new = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'i', 'j', 'k', 'r', 'x', 'y', 'z', 'u']
    old = ['z', 'a', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'q', 'z']
    print(pretty_print_diff(diff(old, new)))

if __name__ == "__main__":
    # load config, halt otherwise
    parser = argparse.ArgumentParser(prog = 'moodle_updater',
                                    description = 'I watch moodle and report on telegram')
    parser.add_argument('-c', dest='config_file', help="")
    parsed = parser.parse_args()
    if parsed.config_file == None:
        parser.print_help()
        exit(1)
    try:
        with open(parsed.config_file, mode="rb") as fp:
            toml_config = tomli.load(fp)
    except:
        die('Could not open ' + parsed.config_file)
    course_id        = toml_config['course_id']
    guest_pass       = toml_config['guest_pass']
    root_url         = toml_config['root_url']
    telegram_token   = toml_config['telegram_token']
    telegram_channel = toml_config['telegram_channel']
    save_file        = toml_config['save_file']
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
    new = fetch_new_list(root_url, course_id, guest_pass)
    old = load_list(save_file)
    d = diff(old, new)
    if len(d) > 0:
        # only if we have a difference we will send the message
        send_message(telegram_token, telegram_channel, pretty_print_diff(d))
        if os.getenv('DEBUG') != None:
            print(pretty_print_diff(d))
        save_list(save_file, new)

