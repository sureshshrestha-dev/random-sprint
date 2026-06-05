# # How to Bypass GIL?

# # 1. Use multiprocessing (separate memory, separate GIL)
# from multiprocessing import Process

# def cpu_intensive_task():
#     count = 0
#     for i in range(50_000_000):
#         count += 1

# # Each process has its OWN Python interpreter and GIL
# p1 = Process(target=cpu_intensive_task)
# p2 = Process(target=cpu_intensive_task)
# # This actually works in parallel on multiple CPU cores!

# # 2. Use C extensions (NumPy, Pandas release GIL)
# import numpy as np
# # NumPy operations run in C, releasing the GIL
# arr = np.array([1, 2, 3]) * 1000000  # Fast, no GIL blocking

# # 3. Use asyncio (single-threaded concurrency)
# import asyncio

# async def fetch_data():
#     await asyncio.sleep(1)  # Non-blocking
#     return "data"

# example 2

# import logging
# import os
# from multiprocessing import Process
# import time

# # Configure logging to show time, process ID, and message
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s [PID %(process)d] %(message)s"
# )


# def cpu_intensive_task(name):
#     logging.info(f"Task {name} started.")
#     start_time = time.time()

#     count = 0
#     for _ in range(50_000_000):
#         count += 1

#     logging.info(
#         f"Task {name} finished in {time.time() - start_time:.2f} seconds."
#     )


# if __name__ == "__main__":
#     logging.info("Main program started.")

#     # Creating two separate processes
#     p1 = Process(target=cpu_intensive_task, args=("A",))
#     p2 = Process(target=cpu_intensive_task, args=("B",))

#     p1.start()
#     p2.start()

#     p1.join()
#     p2.join()

#     logging.info("Main program finished.")

# Example 3
import logging
from threading import Thread
import time
import numpy as np

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s"
)


def numpy_task(name):
    logging.info(f"{name} creating large array...")
    # Generate a massive array to force heavy C-level computation
    data = np.random.rand(1000, 1000)

    logging.info(f"{name} starting heavy matrix math (GIL released)...")
    start = time.time()

    # This heavy dot product happens in C and releases the GIL
    _ = np.dot(data, data)

    logging.info(f"{name} finished math in {time.time() - start:.2f}s")


# If Python threads were stuck on the GIL, these would run strictly sequentially.
t1 = Thread(target=numpy_task, args=("Thread-A",), name="Thread-A")
t2 = Thread(target=numpy_task, args=("Thread-B",), name="Thread-B")

t1.start()
t2.start()

t1.join()
# t2.join()

# example 4
# import asyncio
# import logging
# import time

# logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


# async def fetch_data(task_id, delay):
#     logging.info(f"Task {task_id}: Fetching data... (simulating network wait)")
#     start = time.time()

#     # asyncio.sleep yields control back to the event loop
#     await asyncio.sleep(delay)

#     logging.info(
#         f"Task {task_id}: Data received after {time.time() - start:.2f}s"
#     )
#     return f"data {task_id}"


# async def main():
#     logging.info("Main event loop started.")
#     start_time = time.time()

#     # Schedule both tasks to run concurrently
#     await asyncio.gather(fetch_data(1, 2), fetch_data(2, 3))

#     logging.info(
#         f"All tasks completed in {time.time() - start_time:.2f} seconds total."
#     )


# # Run the event loop
# asyncio.run(main())