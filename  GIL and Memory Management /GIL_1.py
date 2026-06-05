import threading
import time

# CPU-intensive task (bad with GIL)
def count_numbers():
    count = 0
    for i in range(50_000_000):
        count += 1
    return count

# Without threading
start = time.time()
count_numbers()
print(f"Single thread: {time.time() - start:.2f} seconds")

# With 2 threads (GIL hurts CPU work)
start = time.time()
t1 = threading.Thread(target=count_numbers)
t2 = threading.Thread(target=count_numbers)
t1.start()
t2.start()
t1.join()
t2.join()
print(f"2 threads: {time.time() - start:.2f} seconds")
# Actually SLOWER than single thread! 😱