import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, rate: int, per: int):
        self.rate = rate
        self.per = per
        self.allowance = defaultdict(lambda: rate)
        self.last_check = defaultdict(time.time)

    def is_allowed(self, identifier: str) -> bool:
        current_time = time.time()
        time_passed = current_time - self.last_check[identifier]
        self.last_check[identifier] = current_time
        self.allowance[identifier] += time_passed * (self.rate / self.per)

        if self.allowance[identifier] > self.rate:
            self.allowance[identifier] = self.rate

        if self.allowance[identifier] < 1.0:
            return False
        else:
            self.allowance[identifier] -= 1.0
            return True
