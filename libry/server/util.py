"""服务端共享小工具。"""
from datetime import datetime, timezone


def coerce_updated_at(value) -> str:
    """可选的客户端动作时间戳 → 参与 LWW 的 ISO UTC 时间串。

    客户端（离线 outbox 回放）携带动作发生的原始时刻，服务端用它做 per-file LWW
    比较，保证「动作发生晚者胜」与在线多端语义一致。规则：
    - 缺省/空/非法格式 → 服务器当前时间（旧客户端不带该字段时行为不变）
    - 无时区的时间按 UTC 解析
    - 超前的未来值钳制为服务器当前时间（防客户端时钟漂移污染 LWW）
    """
    now = datetime.now(timezone.utc)
    if not value:
        return now.isoformat()
    try:
        ts = datetime.fromisoformat(str(value))
    except ValueError:
        return now.isoformat()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if ts > now:
        ts = now
    return ts.astimezone(timezone.utc).isoformat()
