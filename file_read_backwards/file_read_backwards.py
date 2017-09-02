#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""FileReadBackwards module."""

import io
import weakref

from .buffer_work_space import BufferWorkSpace

supported_encodings = ["utf-8", "ascii", "latin-1"]  # any encodings that are backward compatible with ascii should work


class FileReadBackwards:

    """Class definition for `FileReadBackwards`.

    A `FileReadBackwards` can spawn several iterators, if need be and each of these `FileReadBackwardsIterator` keep an
    opened file handler.

    It can be used as a Context Manager. If done so, when exited, it will close all file handlers that are still opened
    in iterators it has spawned.

    In any mode, `close()` can be called to close them all.
    """

    def __init__(self, path, encoding="utf-8", chunk_size=io.DEFAULT_BUFFER_SIZE):
        """Constructor for FileReadBackwards.

        Args:
            path: Path to the file to be read
            encoding (str): Encoding
            chunk_size (int): How many bytes to read at a time
        """
        if encoding.lower() not in supported_encodings:
            error_message = "{0} encoding was not supported/tested.".format(encoding)
            error_message += "Supported encodings are '{0}'".format(",".join(supported_encodings))
            raise NotImplementedError(error_message)

        self.path = path
        self.encoding = encoding.lower()
        self.chunk_size = chunk_size
        self.__fp_refs = []

    def __iter__(self):
        """Opens a file and returns a reversed iterator on it."""
        fp = io.open(self.path, mode="rb")
        self.__fp_refs.append(weakref.ref(fp))
        return FileReadBackwardsIterator(fp, self.encoding, self.chunk_size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes all opened file handlers and propagates all exceptions on exit."""
        self.close()
        return False

    def close(self):
        """Closes all opened file handlers.

        Moreover, it only keeps internally weakrefs of non-collected items.
        """
        new_fp_refs = []
        for fp_ref in self.__fp_refs:
            fp = fp_ref()
            if fp is not None:
                fp.close()
                new_fp_refs.append(fp_ref)
        self.__fp_refs = new_fp_refs


class FileReadBackwardsIterator:
    """Iterator for `FileReadBackwards`.

    This will read backwards line by line a file. It holds an opened file handler.
    """
    def __init__(self, fp, encoding, chunk_size):
        """Constructor for FileReadBackwardsIterator

        :param fp: A file
        :param str encoding: Encoding
        :param int chunk_size: How many bytes to read at a time
        """
        self.path = fp.name
        self.encoding = encoding
        self.chunk_size = chunk_size
        self.__fp = fp
        self.__buf = BufferWorkSpace(self.__fp, self.chunk_size)

    def __iter__(self):
        return self

    def next(self):
        """Returns unicode string from the last line until the beginning of file.

        Gets exhausted if::

            * already reached the beginning of the file on previous iteration
            * the file got closed

        When it gets exhausted, it closes the file handler.
        """
        # Using binary mode, because some encodings such as "utf-8" use variable number of
        # bytes to encode different Unicode points.
        # Without using binary mode, we would probably need to understand each encoding more
        # and do the seek operations to find the proper boundary before issuing read
        if self.closed:
            raise StopIteration
        if self.__buf.has_returned_every_line():
            self.close()
            raise StopIteration
        self.__buf.read_until_yieldable()
        r = self.__buf.return_line()
        return r.decode(self.encoding)

    __next__ = next

    @property
    def closed(self):
        """The status of the file handler.

        :return: True if the file handler is still opened. False otherwise.
        """
        return self.__fp.closed

    def close(self):
        """Closes the file handler."""
        self.__fp.close()


