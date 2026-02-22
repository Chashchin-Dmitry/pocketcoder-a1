"""Tests for calculator module."""

import pytest

from calculator import add, subtract, multiply, divide


class TestAdd:
    def test_positive_numbers(self):
        assert add(2, 3) == 5

    def test_negative_numbers(self):
        assert add(-1, -2) == -3

    def test_mixed_signs(self):
        assert add(-1, 3) == 2

    def test_zeros(self):
        assert add(0, 0) == 0

    def test_floats(self):
        assert add(1.5, 2.5) == 4.0

    def test_large_numbers(self):
        assert add(10**9, 10**9) == 2 * 10**9


class TestSubtract:
    def test_positive_numbers(self):
        assert subtract(5, 3) == 2

    def test_negative_result(self):
        assert subtract(3, 5) == -2

    def test_negative_numbers(self):
        assert subtract(-1, -2) == 1

    def test_zeros(self):
        assert subtract(0, 0) == 0

    def test_floats(self):
        assert subtract(5.5, 2.5) == 3.0


class TestMultiply:
    def test_positive_numbers(self):
        assert multiply(2, 3) == 6

    def test_negative_numbers(self):
        assert multiply(-2, -3) == 6

    def test_mixed_signs(self):
        assert multiply(-2, 3) == -6

    def test_by_zero(self):
        assert multiply(5, 0) == 0

    def test_by_one(self):
        assert multiply(7, 1) == 7

    def test_floats(self):
        assert multiply(2.5, 4) == 10.0


class TestDivide:
    def test_positive_numbers(self):
        assert divide(6, 3) == 2.0

    def test_negative_numbers(self):
        assert divide(-6, -3) == 2.0

    def test_mixed_signs(self):
        assert divide(-6, 3) == -2.0

    def test_floats(self):
        assert divide(7.5, 2.5) == 3.0

    def test_result_is_float(self):
        assert divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(1, 0)

    def test_zero_divided(self):
        assert divide(0, 5) == 0.0
