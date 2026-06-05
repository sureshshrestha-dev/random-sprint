import sys


class Person:

    def __del__(self):
        print("\n [__del__] Person object destroyed!")


print("--- 1. Creating References ---")
p1 = Person()  # Count = 1
print(f"p1 created. Expected count: 1 - Actual sys.getrefcount: {sys.getrefcount(p1) - 1} (+1 temp = {sys.getrefcount(p1)})")

p2 = p1  # Count = 2
print(f"p2 linked.  Expected count: 2 - Actual sys.getrefcount: {sys.getrefcount(p1) - 1} (+1 temp = {sys.getrefcount(p1)})")

p3 = p1  # Count = 3
print(f"p3 linked.  Expected count: 3 - Actual sys.getrefcount: {sys.getrefcount(p1) - 1} (+1 temp = {sys.getrefcount(p1)})")


print("\n--- 2. Removing References ---")

p2 = None  # Count = 2
print(f"p2 removed. Expected count: 2 - Actual sys.getrefcount: {sys.getrefcount(p1) - 1} (+1 temp = {sys.getrefcount(p1)})")

p3 = None  # Count = 1
print(f"p3 removed. Expected count: 1 - Actual sys.getrefcount: {sys.getrefcount(p1) - 1} (+1 temp = {sys.getrefcount(p1)})")


print("\n--- 3. Removing Final Reference ---")
print("Setting p1 = None now...")
p1 = None  # Count = 0 -> Triggers __del__ instantly!

print("\n--- 4. End of Script ---")