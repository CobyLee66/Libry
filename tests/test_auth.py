"""RateLimiter 单元测试：滑动窗口限速与 429 Retry-After 计算。"""
from libry.server.auth import RateLimiter


def test_rate_limiter_retry_after():
    """未限速为 0；被拒后返回窗口内的正等待秒数，不影响其他 key。"""
    limiter = RateLimiter(max_hits=2, window_sec=60)
    assert limiter.retry_after("ip") == 0
    assert limiter.allow("ip") is True
    assert limiter.retry_after("ip") == 0
    assert limiter.allow("ip") is True
    assert limiter.allow("ip") is False
    wait = limiter.retry_after("ip")
    assert 1 <= wait <= 60
    assert limiter.retry_after("other-ip") == 0
