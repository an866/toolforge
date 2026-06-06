import math


def calculate(operation="{{ operation }}", numbers="{{ numbers }}"):
    if isinstance(numbers, str):
        nums = [float(n.strip()) for n in numbers.split(",") if n.strip()]
    else:
        nums = list(numbers)

    if not nums:
        raise ValueError("No numbers provided")

    if operation == "sum":
        return {"result": sum(nums), "operation": "sum", "count": len(nums)}
    elif operation == "mean":
        return {"result": sum(nums) / len(nums), "operation": "mean", "count": len(nums)}
    elif operation == "median":
        sorted_nums = sorted(nums)
        n = len(sorted_nums)
        if n % 2 == 0:
            median = (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
        else:
            median = sorted_nums[n // 2]
        return {"result": median, "operation": "median", "count": n}
    elif operation == "std":
        mean = sum(nums) / len(nums)
        variance = sum((x - mean) ** 2 for x in nums) / len(nums)
        return {"result": math.sqrt(variance), "operation": "std", "count": len(nums)}
    elif operation == "min":
        return {"result": min(nums), "operation": "min", "count": len(nums)}
    elif operation == "max":
        return {"result": max(nums), "operation": "max", "count": len(nums)}
    else:
        raise ValueError(f"Unsupported operation: {operation}")
