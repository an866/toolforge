from tool import transform_data


def test_transform_data_filter():
    data = [{"name": "a", "val": 1}, {"name": "b", "val": 2}, {"name": "c", "val": 1}]
    result = transform_data(data, operation="filter", key="val", value=1)
    assert len(result) == 2
    assert result[0]["name"] == "a"


def test_transform_data_sort():
    data = [3, 1, 4, 1, 5]
    result = transform_data(data, operation="sort")
    assert result == [1, 1, 3, 4, 5]
