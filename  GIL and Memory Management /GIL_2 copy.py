# When GIL is NOT a Problem (I/O Operations)

import threading
import time
import requests

# I/O-bound task (waiting for network, disk, user input)
def download_file(url):
    print(f"Downloading {url}")
    response = requests.get(url)  # Waits for network (GIL released!)
    print(f"Finished {url}")
    return response

# Multiple threads work WELL with I/O
urls = ['https://example.com'] * 5

start = time.time()
threads = []
for url in urls:
    t = threading.Thread(target=download_file, args=(url,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
print(f"With threading: {time.time() - start:.2f} seconds")

# Why? When thread waits for I/O, it RELEASES the GIL!