# GIL + Memory Management: The Connection
import threading

shared_list = []

def add_items():
    for i in range(10000):
        shared_list.append(i)  # Multiple threads appending

# GIL prevents memory corruption here
threads = [threading.Thread(target=add_items) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Final list length: {len(shared_list)}")  # 100000 exactly!
# Without GIL, this could corrupt memory or give wrong count