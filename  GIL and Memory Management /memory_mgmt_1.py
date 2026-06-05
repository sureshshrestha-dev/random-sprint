# Everything is an Object
# Every value in Python is an object stored in memory
x = 42          # Integer object (28 bytes in memory)
y = "hello"     # String object (49+ bytes)
z = [1, 2, 3]   # List object (72+ bytes)

import sys
print(sys.getsizeof(x))  # 28 bytes
print(sys.getsizeof(y))  # 50 bytes
print(sys.getsizeof(z))  # 72 bytes + items