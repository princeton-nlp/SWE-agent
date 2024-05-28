from __future__ import annotations

import ctypes
import inspect
import re
import threading


def _async_raise(tid, exctype):
    """Raises an exception in the threads with id tid

    This code is modified from the following SO answer:
    Author: Philippe F
    Posted: Nov 28, 2008
    URL: https://stackoverflow.com/a/325528/
    """
    if not inspect.isclass(exctype):
        msg = "Only types can be raised (not instances)"
        raise TypeError(msg)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    if res == 0:
        msg = "invalid thread id"
        raise ValueError(msg)
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        msg = "PyThreadState_SetAsyncExc failed"
        raise SystemError(msg)


class ThreadWithExc(threading.Thread):
    """A thread class that supports raising an exception in the thread from
    another thread.

    This code is modified from the following SO answer:
    Author: Philippe F
    Posted: Nov 28, 2008
    URL: https://stackoverflow.com/a/325528/
    """

    def _get_my_tid(self):
        """determines this (self's) thread id

        CAREFUL: this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.is_alive():
            msg = "the thread is not active"
            raise threading.ThreadError(msg)

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        msg = "could not determine the thread's id"
        raise RuntimeError(msg)

    def raise_exc(self, exctype):
        """Raises the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithExc( ... )
            ...
            t.raise_exc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raise_exc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL: this function is executed in the context of the
        caller thread, to raise an exception in the context of the
        thread represented by this instance.
        """
        _async_raise(self._get_my_tid(), exctype)


# From Martijn Pieters at https://stackoverflow.com/a/14693789
# 7-bit C1 ANSI sequences
_ANSI_ESCAPE = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
    re.VERBOSE,
)


def strip_ansi_sequences(string: str) -> str:
    return _ANSI_ESCAPE.sub("", string)


class AttrDict(dict):
    """Dictionary subclass whose entries can be accessed by attributes (as well
        as normally).

    Author: https://stackoverflow.com/users/355230/martineau
    Posted June 26, 2016
    Post: https://stackoverflow.com/questions/38034377/

    >>> obj = AttrDict()
    >>> obj['test'] = 'hi'
    >>> print obj.test
    hi
    >>> del obj.test
    >>> obj.test = 'bye'
    >>> print obj['test']
    bye
    >>> print len(obj)
    1
    >>> obj.clear()
    >>> print len(obj)
    0
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def from_nested_dicts(cls, data):
        """Construct nested AttrDicts from nested dictionaries."""
        if not isinstance(data, dict):
            return data
        else:
            return cls({key: cls.from_nested_dicts(data[key]) for key in data})
