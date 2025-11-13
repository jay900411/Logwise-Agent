# runtime_error.py
print("Script is starting...")
a = 10
b = 0

print("About to perform division...")
# This will raise a ZeroDivisionError
result = a / b

print(f"Result: {result}") # This line will not be reached