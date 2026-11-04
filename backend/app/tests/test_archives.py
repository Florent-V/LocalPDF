import zipfile

from app.core.archives import build_zip


def test_build_zip_writes_files_with_basename_only(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("hello")
    sub = tmp_path / "sub"
    sub.mkdir()
    b = sub / "b.txt"
    b.write_text("world")

    output = tmp_path / "out.zip"
    build_zip(output, [a, b])

    with zipfile.ZipFile(output) as zf:
        names = sorted(zf.namelist())
        assert names == ["a.txt", "b.txt"]
        assert zf.read("a.txt") == b"hello"
        assert zf.read("b.txt") == b"world"
