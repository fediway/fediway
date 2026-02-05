from config.redis import RedisConfig


def test_redis_config_has_timeout_defaults():
    cfg = RedisConfig()

    assert cfg.redis_socket_timeout == 5.0
    assert cfg.redis_socket_connect_timeout == 5.0


def test_redis_config_timeout_can_be_customized(monkeypatch):
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "10.0")
    monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", "3.0")

    cfg = RedisConfig()

    assert cfg.redis_socket_timeout == 10.0
    assert cfg.redis_socket_connect_timeout == 3.0


def test_redis_config_defaults():
    cfg = RedisConfig()

    assert cfg.redis_host == "localhost"
    assert cfg.redis_port == 6379
    assert cfg.redis_name == 0
    assert cfg.redis_pass is None
