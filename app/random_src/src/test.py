# -1-
def square(x):    return x**2
lambda x:x**2

# -2-
def add(a,b):    return a+b
lambda a,b:a+b 


# -3-
people = [('Alice', 25), ('Bob', 20), ('Charlie', 30)]

for i in range(len(people)):
    for j in range(len(people) - 1 - i):
        if people[j][1] > people[j + 1][1]:
            people[j], people[j + 1] = people[j + 1], people[j]

# print("normal:", people)
sorted_people = sorted(people, key=lambda x: x[1])
# print(sorted_people)
# -4-
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
data=list(filter(lambda x: x % 2 == 0, numbers))
# print(data)

# -5-
data=lambda x: "Even" if x % 2 == 0 else "Odd"
# print(data(4))
# print(data(5))

# -6- to calculate (x^2 + 2x + 1) for each number:

data= list(map(lambda x: x**2 + 2*x + 1, numbers))
# Or simpler: list(map(lambda x: (x+1)**2, numbers))
# print(data)

# -7- 
#  Sort with Complex Key , Sort this list of dictionaries by the length of the name:
users = [
    {'name': 'Bob', 'age': 25},
    {'name': 'Alexander', 'age': 30},
    {'name': 'Eve', 'age': 20}
]
# Expected: Eve (3 chars), Bob (3 chars), Alexander (9 chars)
sorted_users = sorted(users, key=lambda x: len(x['name']))
# print(sorted_users)

# -8- Nested Lambda
# Create a lambda that returns another lambda (function factory):
create_multiplier = lambda x: lambda y: x * y
multiplier = create_multiplier(3)
print(multiplier(5))  # 15

# -9-  Sort with Multiple Conditions Sort this list of tuples by first by name length, then alphabetically:
words = ['cat', 'banana', 'apple', 'dog', 'elephant']
sorted_words = sorted(words, key=lambda x: (len(x), x))
# print(sorted_words)

# -10- 
from functools import reduce
numbers = [42, 17, 89, 3, 56]
# Expected: 89
print(reduce(lambda a, b: a if a > b else b, numbers))

# -x-
data = [
    {'role': 'sys', 'content': [{'content': 'Some system message', 'datetime': '2024-03-15 14:19:00'}]},
    {'role': 'sys', 'content': [{'content': 'Some system message', 'datetime': '2024-03-15 14:30:00'}]},
    {'role': 'user', 'content': [{'content': 'Some user message', 'datetime': '2024-03-15 14:20:00'}]},
    {'role': 'sys', 'content': [{'content': 'Some system message 2', 'datetime': '2024-03-15 14:31:00'}]}
]


# def sortdate(item):
#     dt = item['content'][0]['datetime']
#     return (dt is None, dt)

# sorted_data = sorted(data, key=sortdate)
# print(sorted_data)


result = list(map(
    lambda x: x['content'][0]['content'],
    sorted(
        data,
        key=lambda x: (
            x['content'][0]['datetime'] is None,
            x['content'][0]['datetime']
        )
    )
))

print(result)
# Result: ['How are you?', 'Hi', 'Hello!']

