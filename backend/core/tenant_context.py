from contextvars import ContextVar


_current_empresa = ContextVar("current_empresa", default=None)


def get_current_empresa():
    return _current_empresa.get()


def set_current_empresa(empresa):
    return _current_empresa.set(empresa)


def reset_current_empresa(token):
    _current_empresa.reset(token)
