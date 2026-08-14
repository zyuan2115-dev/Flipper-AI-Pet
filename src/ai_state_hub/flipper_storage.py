"""Small Flipper CLI storage client used by the packaged desktop app.

The protocol is compatible with uFBT's ``flipper.storage`` module, but is
kept here so end-user installers do not need a developer uFBT installation.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
import time

import serial


class FlipperStorageError(RuntimeError):
    pass


class _BufferedRead:
    def __init__(self, stream) -> None:
        self.buffer = bytearray()
        self.stream = stream

    def until(self, marker: str) -> bytes:
        expected = marker.encode("ascii")
        while True:
            position = self.buffer.find(expected)
            if position >= 0:
                result = self.buffer[:position]
                self.buffer = self.buffer[position + len(expected):]
                return bytes(result)
            data = self.stream.read(max(1, self.stream.in_waiting))
            if not data:
                raise FlipperStorageError("Flipper USB CLI did not respond")
            self.buffer.extend(data)


class FlipperStorage:
    PROMPT = ">: "
    EOL = "\r\n"

    def __init__(self, port_name: str, chunk_size: int = 8192) -> None:
        self.port = serial.Serial(port=port_name, baudrate=115200, timeout=2)
        self.read = _BufferedRead(self.port)
        self.chunk_size = chunk_size

    def __enter__(self):
        self.port.open()
        time.sleep(0.5)
        self.read.until(self.PROMPT)
        self.port.reset_input_buffer()
        self.send("device_info\r")
        self.read.until("hardware_model")
        self.read.until(self.PROMPT)
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.port.close()

    def send(self, command: str) -> None:
        self.port.write(command.encode("ascii"))

    def _command(self, command: str) -> bytes:
        self.send(command)
        return self.read.until(self.PROMPT)

    @staticmethod
    def _check(response: bytes, path: str) -> None:
        if b"Storage error:" in response:
            text = response.decode("ascii", "replace").strip()
            raise FlipperStorageError(f"{path}: {text}")

    def exist_file(self, path: str) -> bool:
        response = self._command(f'storage stat "{path}"\r')
        return b"File, size:" in response

    def exist_dir(self, path: str) -> bool:
        response = self._command(f'storage stat "{path}"\r')
        if b"Storage error:" in response:
            return False
        return b"Directory" in response or b"Storage" in response

    def size(self, path: str) -> int:
        response = self._command(f'storage stat "{path}"\r')
        self._check(response, path)
        if b"File, size:" not in response:
            raise FlipperStorageError(f"{path}: not a file")
        value = response.split(b"File, size:", 1)[1].decode("ascii", "replace")
        digits = "".join(character for character in value if character.isdigit())
        return int(digits)

    def mkdir(self, path: str) -> None:
        response = self._command(f'storage mkdir "{path}"\r')
        self._check(response, path)

    def remove(self, path: str) -> None:
        response = self._command(f'storage remove "{path}"\r')
        self._check(response, path)

    def hash_flipper(self, path: str) -> str:
        response = self._command(f'storage md5 "{path}"\r')
        self._check(response, path)
        return response.decode("ascii", "replace").strip().splitlines()[-1]

    def send_file(self, source: str, destination: str) -> None:
        if self.exist_file(destination):
            self.remove(destination)
        with open(source, "rb") as file:
            while chunk := file.read(self.chunk_size):
                self.send(f'storage write_chunk "{destination}" {len(chunk)}\r')
                response = self.read.until(self.EOL)
                self._check(response, destination)
                self.port.write(chunk)
                self.read.until(self.PROMPT)


class FlipperStorageOperations:
    def __init__(self, storage: FlipperStorage) -> None:
        self.storage = storage

    def _mkpath(self, path: str) -> None:
        components = path.split("/")
        missing = []
        while components and not self.storage.exist_dir("/".join(components)):
            missing.append(components.pop())
        for component in reversed(missing):
            components.append(component)
            self.storage.mkdir("/".join(components))

    def recursive_send(self, destination: str, source: str, force: bool = False) -> None:
        if not os.path.isfile(source):
            raise FlipperStorageError(f"{source}: expected a file")
        self._mkpath(posixpath.dirname(destination))
        if not force and self.storage.exist_file(destination):
            with open(source, "rb") as file:
                local_hash = hashlib.md5(file.read()).hexdigest()
            if local_hash == self.storage.hash_flipper(destination):
                return
        self.storage.send_file(source, destination)
