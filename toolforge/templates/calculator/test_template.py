from tool import calculate


def test_calculate_sum():
    result = calculate(operation="sum", numbers="1,2,3,4,5")
    assert result["result"] == 15
    assert result["count"] == 5


def test_calculate_mean():
    result = calculate(operation="mean", numbers="2,4,6")
    assert result["result"] == 4.0


def test_calculate_median():
    result = calculate(operation="median", numbers="1,3,3,6,7,8,9")
    assert result["result"] == 6
