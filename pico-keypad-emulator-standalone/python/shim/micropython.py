"""Emulated `micropython` module (const and friends)."""


def const(value):
    return value


def native(fn):
    return fn


viper = native


def alloc_emergency_exception_buf(size):
    pass


def schedule(fn, arg):
    fn(arg)


def mem_info(*args):
    print("mem: (emulated) total: 264192, current: 8192")


def opt_level(*args):
    return 0
