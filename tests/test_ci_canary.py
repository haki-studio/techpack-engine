def test_ci_canary_must_go_red():
    """prove-the-guard: CI must fail on this. Reverted in the next commit."""
    assert 1 + 1 == 3
