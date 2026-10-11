from gescrtl.core.one_euro import OneEuro


def test_constant_input_is_constant():
    f = OneEuro(1.0, 0.007, 1.0)
    outs = [f(0.4, i / 30) for i in range(60)]
    assert all(abs(o - 0.4) < 1e-9 for o in outs)


def test_step_converges():
    f = OneEuro(1.0, 0.007, 1.0)
    f(0.0, 0.0)
    out = 0.0
    for i in range(1, 300):
        out = f(1.0, i / 30)
    assert abs(out - 1.0) < 0.01


def test_deterministic_and_reset():
    seq = [(0.1 * i % 1.0, i / 30) for i in range(50)]
    a, b = OneEuro(1.0, 0.007, 1.0), OneEuro(1.0, 0.007, 1.0)
    assert [a(x, t) for x, t in seq] == [b(x, t) for x, t in seq]
    a.reset()
    assert a(0.77, 5.0) == 0.77
