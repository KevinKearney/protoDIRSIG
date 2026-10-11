"""`dirhash/1`: the content digest of a directory, the hash a directory-valued library reference (a `.scene`) carries.

The digest of a directory is the sha256 of a manifest. The manifest lists every regular file under the directory,
recursively, one line per file, `<64 lowercase hex sha256 of the file's bytes>` + two spaces + `<path relative to the
directory, POSIX separators>` + newline, sorted by the UTF-8 bytes of the path. Symbolic links, any other non-regular
file, and file names containing a backslash or a newline are an error (the library holds real files only). Empty
directories are not listed, and a directory with no regular file under it has the empty manifest (its digest is the
sha256 of zero bytes). A directory-valued ref is a `{name, content_hash}` whose `name` ends in `.scene`, the
directory is the parent directory of that file (the layout `scenes/<scene>/<scene>.scene`), and `content_hash` is
`sha256:` + the manifest digest. An independent check is the shell pipeline

    (cd DIR && LC_ALL=C find . -type f -printf '%P\\0' | LC_ALL=C sort -z | xargs -0 -r sha256sum) | sha256sum

Conformance vector: manifold_contracts/vectors/identity/dirhash/.

Imports: the standard library only (`scripts/stamp_hashes.py` loads this file by path).
"""
import hashlib
import os
import stat
from pathlib import Path

PREFIX = "sha256:"
DIRECTORY_SUFFIX = (".scene",)                     # a ref whose name ends so names a directory: its parent
_CHUNK = 1 << 20


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _walk(root, rel):
    """(relative path as UTF-8 bytes, absolute path) for every regular file under `root / rel`, unsorted."""
    with os.scandir(root / rel if rel else root) as it:
        for entry in it:
            sub = f"{rel}/{entry.name}" if rel else entry.name
            where = root / sub
            if "\\" in entry.name or "\n" in entry.name:
                raise ValueError(f"{where}: a file name with a backslash or a newline is not allowed (dirhash/1)")
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f"{where}: a symbolic link is not allowed in a hashed directory (dirhash/1)")
            if stat.S_ISDIR(mode):
                yield from _walk(root, sub)
            elif stat.S_ISREG(mode):
                try:
                    key = sub.encode("utf-8")
                except UnicodeEncodeError as e:
                    raise ValueError(f"{where}: the file name is not valid UTF-8 (dirhash/1)") from e
                yield key, where
            else:
                raise ValueError(f"{where}: not a regular file or directory; a hashed directory holds real files "
                                 "only (dirhash/1)")


def directory_manifest(path):
    """The `dirhash/1` manifest of the directory `path`, as bytes (see the module docstring)."""
    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"{root}: not a directory")
    lines = [f"{_file_sha256(where)}  ".encode("ascii") + key + b"\n" for key, where in sorted(_walk(root, ""))]
    return b"".join(lines)


def directory_digest(path):
    """`sha256:` + the sha256 of the `dirhash/1` manifest of the directory `path`."""
    return PREFIX + hashlib.sha256(directory_manifest(path)).hexdigest()


def is_directory_ref(name):
    """A ref name that names a directory (`scenes/<scene>/<scene>.scene` names `scenes/<scene>/`)."""
    return isinstance(name, str) and name.strip().endswith(DIRECTORY_SUFFIX)
