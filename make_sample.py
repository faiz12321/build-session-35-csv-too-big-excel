"""Create a fictional CSV only in a new sample folder. About 37 MB on disk."""
from pathlib import Path
import stat

ROWS = 1_100_003


def main():
    folder = Path(__file__).absolute().parent / 'sample'
    if '..' in folder.parts:
        raise OSError('Parent-traversal paths are unsupported.')
    for parent in reversed(folder.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError('Linked/reparse-point parents are unsupported.')
    try:
        folder.mkdir()
    except FileExistsError:
        raise SystemExit('Stopped: sample already exists. Nothing was replaced or deleted.')
    with (folder / 'sales.csv').open('x', encoding='utf-8', newline='') as handle:
        handle.write('Order ID,Item,Region,Total\n')
        for i in range(1, ROWS + 1):
            handle.write('%07d,Item %d,Region %d,%d.%02d\n' % (
                i, (i * 37) % 9000 + 1000, (i * 11) % 8 + 1,
                (i * 13) % 900 + 20, (i * 7) % 100))
    print('Created sample/sales.csv with 1,100,003 fictional data records plus header.')
    print('Setup refuses existing sample paths; use a new empty lesson folder.')


if __name__ == '__main__':
    main()
