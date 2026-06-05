# How Python manages memory
a = [1, 2, 3]  # Memory allocated for list + 3 integers
b = a          # b references same memory (no new allocation)

# Memory pools (arenas)
small_int = 100    # Reused from small integer cache (-5 to 256)
large_int = 10000  # New object created

x = 100
y = 100
print(x is y)  # True (same object - cached)

x = 1000
y = 1000
print(x is y)  # False (different objects)

# String interning
s1 = "hello"
s2 = "hello"
print(s1 is s2)  # True (interned for efficiency)