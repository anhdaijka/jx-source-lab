from pathlib import Path
import json
import importlib.util
import struct
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

def load_jxlab():
    spec=importlib.util.spec_from_file_location('jxlab',ROOT/'scripts'/'jxlab.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_jxcorpus():
    scripts=ROOT/'scripts'
    if str(scripts) not in sys.path:sys.path.insert(0,str(scripts))
    spec=importlib.util.spec_from_file_location('jxcorpus',scripts/'jxcorpus.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
class TestJxlabParser(unittest.TestCase):
    def test_required_files_exist(self):
        for path in ['AGENTS.md','README.md','lab.toml','scripts/jxlab.py','database/schema.sql','docs/reconstruction-protocol.md','docs/pak-forensics-protocol.md','prompts/00-first-codex-session.md']:
            self.assertTrue((ROOT/path).exists(),path)

    def test_json_schemas_parse(self):
        for path in (ROOT/'schemas').glob('*.json'):
            json.loads(path.read_text(encoding='utf-8'))

    def test_parse_tsv_table_preserves_headers_and_line_numbers(self):
        jxlab=load_jxlab()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.txt'
            path.write_text('TaskId\tTaskName\nMã\tTên\n100\tSample task\n',encoding='utf-8')
            parsed=jxlab.parse_tsv_table(path)
        self.assertEqual(parsed['header'],['TaskId','TaskName'])
        self.assertEqual(parsed['localized_header'],['Mã','Tên'])
        self.assertEqual(parsed['records'],[(3,{'TaskId':'100','TaskName':'Sample task'})])
        self.assertEqual(parsed['malformed_rows'],[])

    def test_parse_pak_listing_preserves_entry_metadata(self):
        jxlab=load_jxlab()
        content=(
            'TotalFile:1\tPakTime:2010-01-01 00:00:00\tPakTimeSave:abc\tCRC:def\n'
            'Index\tID\tTime\tFileName\tSize\tInPakSize\tComprFlag\tCRC\n'
            '0\t1\t2010-01-01 00:00:00\t\\task_publish\\task\\0000000000000001.xml\t10\t5\t4\tdeadbeef\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'listing.txt'
            path.write_text(content,encoding='utf-8')
            parsed=jxlab.parse_pak_listing(path)
        self.assertEqual(parsed['metadata']['TotalFile'],'1')
        self.assertEqual(parsed['entries'][0][0],3)
        self.assertEqual(parsed['entries'][0][1]['ComprFlag'],'4')
        self.assertEqual(jxlab.task_publish_entry_kind(parsed['entries'][0][1]['FileName']),('task_xml_candidate','0000000000000001'))

    def test_inspect_pack_layout_accepts_bounded_standard_index(self):
        jxlab=load_jxlab()
        header=struct.pack('<4sIII',b'PACK',1,36,32)+(b'\0'*16)
        index=struct.pack('<IIII',1,32,4,4)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.pak'
            path.write_bytes(header+b'test'+index)
            layout=jxlab.inspect_pack_layout(path)
        self.assertEqual(layout['status'],'standard_index_layout')
        self.assertTrue(layout['payload_ranges_in_bounds'])
        self.assertTrue(layout['payload_contiguous'])
        self.assertEqual(layout['method_nibble_counts'],{'0x00000000':1})
        self.assertEqual(layout['fragment_flag_counts'],{'false':1})

    def test_inspect_pack_layout_uses_27_bit_size_and_method_nibble(self):
        jxlab=load_jxlab()
        header=struct.pack('<4sIII',b'PACK',1,36,32)+(b'\0'*16)
        index=struct.pack('<IIII',1,32,8,0x20000004)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.pak'
            path.write_bytes(header+b'test'+index)
            layout=jxlab.inspect_pack_layout(path)
        sample=layout['index_record_samples'][0]
        self.assertEqual(sample['stored_size_27'],4)
        self.assertEqual(sample['method_nibble_hex'],'0x20000000')
        self.assertFalse(sample['fragment_flag'])

    def test_nrv2b_safe_8_decodes_copied_pack_sample_when_available(self):
        jxlab=load_jxlab()
        archive=ROOT/'client'/'pak'/'aspaksc.pak'
        if not archive.exists():
            self.skipTest('Local read-only client sample is not available.')
        with tempfile.TemporaryDirectory() as directory:
            copied=Path(directory)/archive.name
            copied.write_bytes(archive.read_bytes())
            data=copied.read_bytes()
        _,count,index_offset,_=struct.unpack_from('<4sIII',data,0)
        self.assertEqual(count,2)
        elem_id,offset,expanded,packed=struct.unpack_from('<IIII',data,index_offset)
        stored=packed&jxlab.PACK_STORED_SIZE_MASK
        decoded=jxlab.nrv2b_decompress_safe_8(data[offset:offset+stored],expanded)
        self.assertEqual(elem_id,0x80e93cfb)
        self.assertEqual(len(decoded),49528)
        self.assertEqual(__import__('hashlib').sha256(decoded).hexdigest(),'599d514db95b8ca62f2364324b27f08a695fbb5a2859803077fdeecfa923099f')

    def test_safe_internal_path_rejects_parent_traversal(self):
        jxlab=load_jxlab()
        with self.assertRaises(ValueError):jxlab.safe_internal_path('\\safe\\..\\escape.txt')
        self.assertEqual(jxlab.safe_internal_path('\\safe\\file.txt'),Path('safe')/'file.txt')

    def test_corpus_tsv_parser_preserves_variable_width_rows(self):
        corpus=load_jxcorpus()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'legacy.txt'
            path.write_text('A\tB\tC\n1\t2\n3\t4\t5\textra\n',encoding='utf-8')
            parsed=corpus.parse_tsv(path)
        self.assertEqual(len(parsed['records']),2)
        self.assertEqual(parsed['records'][0][1],{'A':'1','B':'2','C':''})
        self.assertEqual(parsed['records'][1][1]['__extra_1'],'extra')
        self.assertEqual([row['handling'] for row in parsed['malformed']],['padded_trailing_empty','preserved_extra_columns'])
