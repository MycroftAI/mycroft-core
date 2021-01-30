import urllib.request
import tempfile
import shutil
import os
import requests

downloaded = 0
last_printed = 0

def report(block_number, block_size, total_size):
    global downloaded, last_printed
    downloaded += block_size
    percentage = 100 * downloaded / total_size
    if percentage - last_printed >= 1:
        last_printed = percentage
        print('{}%'.format(percentage))

url = 'https://github.com/MycroftAI/mimic1/releases/latest/download/mimic_windows_amd64.zip'

print("Downloading")
r = requests.get(url)
with tempfile.NamedTemporaryFile(suffix='.zip', mode='wb', delete=False) as tempzip:
    tempzip.write(r.content)
    
    print("Unpacking")
    shutil.unpack_archive(tempzip.name, 'mimic\\bin')