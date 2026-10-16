import os
"""Small temporary-fixture tests; not a proof for every CSV or filesystem."""
import contextlib
import csv
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import bigcsv

HERE = Path(__file__).resolve().parent


class Checks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'data.csv'
        self.output = self.root / 'parts'

    def call(self, raw, maximum=None):
        self.path.write_bytes(raw if isinstance(raw, bytes) else raw.encode())
        out, err = io.StringIO(), io.StringIO()
        args = ['bigcsv.py', str(self.path)]
        if maximum is not None:
            args += ['--split', str(maximum), str(self.output)]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = bigcsv.main(args)
        return rc, out.getvalue(), err.getvalue()

    def split_rows(self):
        rows = []
        for p in sorted(self.output.glob('part*.csv')):
            records = list(bigcsv.read_records(p))
            self.assertEqual(records[0], ['A', 'B'])
            rows.extend(records[1:])
        return rows

    def test_record_count_not_physical_lines(self):
        rc, out, _ = self.call('A,B\n1,"two\nlines"\n2,end\n')
        self.assertEqual(rc, 0)
        self.assertIn('Data records: 2', out)

    def test_multiline_quotes_commas_and_order_preserved(self):
        raw='A,B\n1,"two\nlines"\n2,"a,b"\n3,"say ""yes"""\n'
        self.assertEqual(self.call(raw, 2)[0], 0)
        self.assertEqual(self.split_rows(), [['1','two\nlines'],['2','a,b'],['3','say "yes"']])

    def test_bare_carriage_return_field_preserved(self):
        self.assertEqual(self.call('A,B\r\n1,"x\ry"\r\n',1)[0],0)
        self.assertEqual(self.split_rows(),[['1','x\ry']])

    def test_header_only_creates_no_parts(self):
        self.assertEqual(self.call('A,B\n', 2)[0], 0)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_empty_file_rejected_without_output(self):
        self.assertEqual(self.call('',2)[0],1)
        self.assertFalse(self.output.exists())

    def test_blank_header_rejected(self):
        self.assertEqual(self.call('A, \n1,x\n')[0],1)

    def test_duplicate_header_rejected(self):
        self.assertEqual(self.call('A,A\n1,x\n')[0],1)

    def test_extra_field_rejected(self):
        self.assertEqual(self.call('A,B\n1,x,z\n',2)[0],1)
        self.assertFalse(self.output.exists())

    def test_missing_field_rejected(self):
        self.assertEqual(self.call('A,B\n1\n')[0],1)

    def test_blank_record_rejected(self):
        self.assertEqual(self.call('A,B\n\n')[0],1)

    def test_unclosed_quote_rejected(self):
        self.assertEqual(self.call('A,B\n1,"x\n',2)[0],1)

    def test_invalid_utf8_rejected(self):
        self.assertEqual(self.call(b'A,B\n1,\xff\n',2)[0],1)

    def test_bom_supported(self):
        self.assertEqual(self.call(b'\xef\xbb\xbfA,B\n1,x\n',2)[0],0)
        self.assertEqual(self.split_rows(),[['1','x']])

    def test_last_record_without_newline(self):
        self.assertEqual(self.call('A,B\n1,x',2)[0],0)
        self.assertEqual(self.split_rows(),[['1','x']])

    def test_header_in_every_part_and_sizes(self):
        self.assertEqual(self.call('A,B\n'+'1,x\n'*5,2)[0],0)
        self.assertEqual([bigcsv.scan(p)[1] for p in sorted(self.output.iterdir())],[2,2,1])

    def test_existing_output_folder_and_nested_bytes_preserved(self):
        (self.output/'nested').mkdir(parents=True)
        p=self.output/'nested/keep';p.write_bytes(b'KEEP');before=p.stat().st_mtime_ns
        self.assertEqual(self.call('A,B\n1,x\n',2)[0],1)
        self.assertEqual(p.read_bytes(),b'KEEP');self.assertEqual(p.stat().st_mtime_ns,before)
        self.assertEqual(sorted(p.relative_to(self.output).as_posix() for p in self.output.rglob('*')),['nested','nested/keep'])

    def test_existing_output_file_preserved(self):
        self.output.write_bytes(b'KEEP')
        self.assertEqual(self.call('A,B\n1,x\n',2)[0],1)
        self.assertEqual(self.output.read_bytes(),b'KEEP')

    def test_repeat_split_does_not_replace_parts(self):
        self.assertEqual(self.call('A,B\n1,x\n',2)[0],0)
        p=self.output/'part0001.csv';before=(p.read_bytes(),p.stat().st_mtime_ns)
        self.assertEqual(self.call('A,B\n2,y\n',2)[0],1)
        self.assertEqual(before,(p.read_bytes(),p.stat().st_mtime_ns))

    def test_source_bytes_and_mtime_preserved(self):
        self.path.write_bytes(b'A,B\r\n1,x\r\n');before=(self.path.read_bytes(),self.path.stat().st_mtime_ns)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bigcsv.main(['bigcsv.py',str(self.path),'--split','1',str(self.output)]),0)
        self.assertEqual(before,(self.path.read_bytes(),self.path.stat().st_mtime_ns))

    def test_bad_split_sizes(self):
        for value in ['x',0,-1,bigcsv.EXCEL_GRID]:
            self.assertEqual(self.call('A,B\n1,x\n',value)[0],2)
            self.assertFalse(self.output.exists())

    def test_header_uses_one_grid_row(self):
        with mock.patch.object(bigcsv,'MAX_DATA',2):
            self.assertIn('Within row-count limit only.',self.call('A,B\n1,x\n2,y\n')[1])
            self.assertIn('Exceeds row-count limit',self.call('A,B\n1,x\n2,y\n3,z\n')[1])
        self.assertEqual(bigcsv.MAX_DATA,1_048_575)

    def test_count_success_is_not_excel_safety_claim(self):
        out=self.call('A,B\n=1+1,001\n')[1]
        self.assertIn('formulas, type conversions',out)
        self.assertNotIn('should open fully',out)

    def test_changed_source_digest_is_not_verified(self):
        self.path.write_text('A,B\n1,x\n')
        expected=bigcsv.scan(self.path)
        self.path.write_text('A,B\n2,y\n')
        with self.assertRaisesRegex(ValueError,'digest/count differs'):
            bigcsv.split(self.path,2,self.output,expected)
        self.assertTrue(self.path.exists())

    def test_usage_errors(self):
        for args in [[],['bigcsv.py'],['bigcsv.py','a','--split'],['bigcsv.py','a','--bad','2','out']]:
            with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(bigcsv.main(args),2)

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(bigcsv.main(['bigcsv.py',str(self.path)]),1)

    def test_setup_refusal_preserves_nested_data(self):
        p=self.root/'make_sample.py';shutil.copyfile(HERE/'make_sample.py',p)
        (self.root/'sample/nested').mkdir(parents=True);keep=self.root/'sample/nested/keep';keep.write_bytes(b'KEEP')
        result=subprocess.run([sys.executable,str(p)],capture_output=True,text=True)
        self.assertEqual(result.returncode,1);self.assertEqual(keep.read_bytes(),b'KEEP')
        self.assertEqual(sorted(x.name for x in (self.root/'sample').iterdir()),['nested'])


class PathSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'tree';self.root.mkdir()
        self.file=self.root/'zero';self.file.write_bytes(b'')
    def link(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError:self.skipTest('Symlinks unavailable')
    def code(self,path):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            return bigcsv.main(['p',str(path)])
    def test_root_alias_refuses(self):
        p=self.base/'alias';self.link(p,self.root,True);self.assertEqual(self.code(p),1)
    def test_ancestor_alias_refuses(self):
        p=self.base/'alias';self.link(p,self.base,True);self.assertEqual(self.code(p/'tree'),1)
    def test_file_alias_refuses(self):
        p=self.base/'linked';self.link(p,self.file);self.assertEqual(self.code(p),1)
    def test_file_hardlink_refuses(self):
        p=self.base/'hard';os.link(self.file,p);self.assertEqual(self.code(p),1)
    def test_file_pipe_refuses(self):
        if not hasattr(os,'mkfifo'):self.skipTest('Unix pipe unavailable')
        p=self.base/'pipe';os.mkfifo(p);self.assertEqual(self.code(p),1)
    def test_file_self_loop_refuses(self):
        p=self.base/'loop';self.link(p,p);self.assertEqual(self.code(p),1)
    def test_file_dangling_refuses(self):
        p=self.base/'alias';self.link(p,self.base/'missing');self.assertEqual(self.code(p),1)
    def test_file_traversal_refuses(self):self.assertEqual(self.code(self.root/'..'/'tree'/'zero'),1)
    def test_file_ancestor_refuses(self):
        p=self.base/'alias';self.link(p,self.root,True);self.assertEqual(self.code(p/'zero'),1)
    def test_metadata_error_refuses(self):
        with mock.patch.object(Path,'lstat',side_effect=OSError('forced')):self.assertEqual(self.code(self.file),1)
    def test_reparse_attribute_refuses(self):
        real=Path.lstat
        def fake(p,*a,**kw):
            value=real(p,*a,**kw)
            if p==self.file:return type('Reparse',(),{'st_mode':value.st_mode,'st_file_attributes':0x400})()
            return value
        with mock.patch.object(Path,'lstat',fake):self.assertEqual(self.code(self.file),1)


    def test_read_error_stops(self):
        with mock.patch.object(Path,'open',side_effect=OSError('forced')):
            self.assertEqual(self.code(self.file),1)
    def test_setup_alias_parent_refuses(self):
        import make_sample
        p=self.base/'alias';self.link(p,self.root,True)
        with mock.patch.object(make_sample,'__file__',str(p/'make_sample.py')):
            with self.assertRaises(OSError):make_sample.main()
        self.assertFalse((self.root/'sample').exists())
    def test_setup_traversal_refuses(self):
        import make_sample
        with mock.patch.object(make_sample,'__file__',str(self.root/'..'/'make_sample.py')):
            with self.assertRaises(OSError):make_sample.main()

    def test_output_linked_parent_refuses(self):
        p=self.base/'alias';self.link(p,self.root,True)
        with self.assertRaises(OSError):bigcsv.safe_output(p/'new')
        self.assertFalse((self.root/'new').exists())
    def test_output_traversal_refuses(self):
        with self.assertRaises(OSError):bigcsv.safe_output(self.root/'..'/'new')
    def test_output_metadata_error_refuses(self):
        with mock.patch.object(Path,'lstat',side_effect=OSError('forced')):
            with self.assertRaises(OSError):bigcsv.safe_output(self.root/'new')


if __name__ == '__main__':
    unittest.main()
