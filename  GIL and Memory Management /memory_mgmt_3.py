# Garbage Collection (For Circular References)

import gc
import sys


class Node:

    def __init__(self, value):
        self.value = value
        self.next = None

    def __del__(self):
        print(f"♻️  [__del__] Node {self.value} destroyed!")


print("--- 1. Creating Nodes and Circular Reference ---")
node1 = Node(1)
node2 = Node(2)

# Create the cycle
node1.next = node2
node2.next = node1  # Loop complete!

# sys.getrefcount adds +1 temporary reference. 
# Expected base count here is 2: one from the variable name, one from the .next pointer.
print(f"node1 ref count: {sys.getrefcount(node1) - 1}")
print(f"node2 ref count: {sys.getrefcount(node2) - 1}")


print("\n--- 2. Severing Global Variables ---")
print("Setting node1 and node2 to None...")
node1 = None
node2 = None

print("Variables cleared. Notice that __del__ has NOT fired yet!")


print("\n--- 3. Forcing Garbage Collection ---")
print("Calling gc.collect()...")



# gc.collect() returns the number of unreachable objects found/cleared
unreachable_count = gc.collect()

print(f"GC complete. Unreachable objects found and cleared: {unreachable_count}")
print("\n--- 4. End of Script ---")