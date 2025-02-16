"""HDF5 files."""

from pathlib import Path
from typing import Union

import h5py


class HDF5File:
    def __init__(self, filename: Union[str, Path]):
        if isinstance(filename, str):
            path = Path(filename)
        else:
            path = filename

        self.file_path = path.expanduser().resolve()
        self.file_name = path.name
        self.file_extension = path.suffix[1:]
        self.file_type = 'HDF5'
        self.file_handle = self.open_file()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.file_handle)

    def open_file(self):
        if not self.file_path.is_file():
            raise FileNotFoundError('Cannot find snapshot file')
        return h5py.File(self.file_path, mode='r')

    def close_file(self):
        self.file_handle.close()
