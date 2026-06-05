# Memory Optimization Techniques

# 1. Use generators for large data
# BAD: Loads everything into memory
def read_large_file_bad():
    with open('large_file.txt') as f:
        return f.readlines()  # All lines in memory!

# GOOD: Generator yields one line at a time
def read_large_file_good():
    with open('large_file.txt') as f:
        for line in f:  # One line in memory
            yield line

# 2. Use __slots__ to reduce memory
class RegularPerson:
    def __init__(self, name, age):
        self.name = name
        self.age = age

class SlottedPerson:
    __slots__ = ['name', 'age']  # No __dict__ overhead
    def __init__(self, name, age):
        self.name = name
        self.age = age

import sys
regular = RegularPerson("John", 30)
slotted = SlottedPerson("John", 30)

print(f"Regular: {sys.getsizeof(regular)} + dict")
print(f"Slotted: {sys.getsizeof(slotted)}")  # Much smaller!

# 3. Use array module for numbers
from array import array
# List of integers (each int is 28 bytes)
list_ints = [1, 2, 3, 4, 5]  # ~140 bytes

# Array of integers (each int is 4 bytes)
array_ints = array('i', [1, 2, 3, 4, 5])  # ~20 bytes