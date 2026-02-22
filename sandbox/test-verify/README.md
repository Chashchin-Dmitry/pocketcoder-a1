# Calculator

A simple Python calculator module providing basic arithmetic operations.

## Functions

### `add(a, b)`

Returns the sum of two numbers.

```python
from calculator import add

add(2, 3)      # 5
add(-1, 3)     # 2
add(1.5, 2.5)  # 4.0
```

### `subtract(a, b)`

Returns the difference of two numbers.

```python
from calculator import subtract

subtract(5, 3)    # 2
subtract(3, 5)    # -2
subtract(5.5, 2.5)  # 3.0
```

### `multiply(a, b)`

Returns the product of two numbers.

```python
from calculator import multiply

multiply(2, 3)    # 6
multiply(-2, 3)   # -6
multiply(2.5, 4)  # 10.0
```

### `divide(a, b)`

Returns the quotient of two numbers. Raises `ValueError` if dividing by zero.

```python
from calculator import divide

divide(6, 3)    # 2.0
divide(7, 2)    # 3.5
divide(0, 5)    # 0.0
divide(1, 0)    # raises ValueError: Cannot divide by zero
```

## Running Tests

```bash
pytest -v
```
