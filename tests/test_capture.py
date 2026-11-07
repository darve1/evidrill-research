"""Source preservation: helper downloads, extracted text and quote normalization."""
import http.server
import json
import shutil
import threading
import unittest
from pathlib import Path

from support import StudyFixture, cli, ledger

HTML = (b'<!doctype html><html><head><title>Trial</title><style>p{color:red}</style>'
        b'<script>var hidden = "not text";</script></head><body>'
        b'<p>The drug <em>did not</em> reduce mortality in the trial.</p>'
        b'<p>Mean weight change was &minus;1.4&nbsp;kg (95% CI &minus;1.8 to &minus;1.0).</p></body></html>')


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/missing':
            self.send_error(403)
            return
        body, kind = (HTML, 'text/html; charset=utf-8') if self.path == '/page' else (
            'Plain caf\xe9 text in Latin-1 encoding.\n'.encode('latin-1'), 'text/plain; charset=latin-1')
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.s = StudyFixture(self)

    def test_content_addressed_versions_are_preserved(self):
        source = self.s.temp / 'new.txt'
        source.write_text('Old', encoding='utf-8')
        first = ledger.capture(self.s.root, source, 's9', 'text')
        source.write_text('New', encoding='utf-8')
        second = ledger.capture(self.s.root, source, 's9', 'text')
        self.assertNotEqual(first['snapshot_path'], second['snapshot_path'])
        self.assertEqual((self.s.root / first['snapshot_path']).read_text(), 'Old')

    def test_path_traversal_source_id_rejected(self):
        with self.assertRaises(ValueError):
            ledger.capture(self.s.root, self.s.temp / 'release.txt', '../escape', 'text')

    def test_input_capture_kind_is_recorded_and_validated(self):
        snap = ledger.capture(self.s.root, self.s.temp / 'release.txt', 's9', capture_kind='downloaded')
        self.assertEqual((snap['capture'], snap['format'], snap['content_kind']), ('downloaded', 'text', 'text'))
        with self.assertRaises(ValueError):
            ledger.capture(self.s.root, self.s.temp / 'release.txt', 's9', capture_kind='helper_fetched')

    def test_helper_download_extracts_html_text_and_records_fetch(self):
        snap = ledger.capture(self.s.root, source_id='web1', url=self.base + '/page')
        self.assertEqual(snap['capture'], 'helper_fetched')
        self.assertEqual(snap['fetch']['status'], 200)
        self.assertTrue(snap['snapshot_path'].endswith('.html'))
        text = (self.s.root / snap['text_path']).read_text(encoding='utf-8')
        self.assertIn('The drug did not reduce mortality in the trial.', text)
        self.assertNotIn('hidden', text)
        self.assertNotIn('color:red', text)

    def test_quotes_match_rendered_html_text_and_keep_negation(self):
        result = self.register_web('/page')
        self.assertNotIn('error', result)
        self.add_quote('The drug did not reduce mortality in the trial.')
        self.add_quote('Mean weight change was −1.4 kg (95% CI −1.8 to −1.0).', eid='e8')
        with self.assertRaises(ValueError):
            self.add_quote('The drug did reduce mortality in the trial.', eid='e9')

    def test_non_utf8_text_gets_decoded_copy(self):
        snap = ledger.capture(self.s.root, source_id='web2', url=self.base + '/latin')
        self.assertEqual(snap['format'], 'binary')
        self.assertIn('café', (self.s.root / snap['text_path']).read_text(encoding='utf-8'))
        self.assertTrue(snap['text_extraction'].startswith('decode:'))

    def test_http_error_is_reported_without_writing(self):
        code, payload, _ = cli('snapshot', '--root', self.s.root, '--source-id', 'web3', '--url', self.base + '/missing')
        self.assertEqual(code, 1)
        self.assertIn('HTTP 403', payload['error'])
        self.assertFalse((self.s.root / 'snapshots/web3').exists())

    def test_only_http_urls_are_fetched(self):
        with self.assertRaises(ValueError):
            ledger.capture(self.s.root, source_id='bad', url='file:///etc/passwd')

    def test_layout_normalization(self):
        variants = ledger.text_variants('The drug did not\nreduce mor-\ntality. “Quoted” ﬁne.')
        for quote in ('The drug did not reduce mortality.', '"Quoted" fine.'):
            self.assertIsNotNone(ledger.locate(quote, variants), quote)
        self.assertIsNone(ledger.locate('The drug did reduce', variants))
        self.assertIsNone(ledger.locate('x2', ledger.text_variants('x²')), 'superscripts are not folded into digits')

    @unittest.skipUnless(shutil.which('pdftotext'), 'pdftotext not installed')
    def test_pdf_text_is_extracted_when_pdftotext_exists(self):
        pdf = Path(self.s.temp / 'tiny.pdf')
        pdf.write_bytes(TINY_PDF)
        snap = ledger.capture(self.s.root, pdf, 'pdf1', capture_kind='downloaded')
        self.assertEqual((snap['format'], snap['text_extraction']), ('binary', 'pdftotext'))
        self.assertIn('Hello PDF', (self.s.root / snap['text_path']).read_text(encoding='utf-8'))

    # helpers
    def register_web(self, path):
        code, payload, _ = cli('snapshot', '--root', self.s.root, '--source-id', 'web1', '--url', self.base + path,
                               '--title', 'Trial page', '--route', 'literature', '--read-level', 'full_text')
        self.assertEqual(code, 0, payload)
        return payload

    def add_quote(self, quote, eid='e7'):
        return ledger.add_row(self.s.root, 'evidence', dict(evidence_id=eid, source_id='web1', origin_id='unknown',
                                                           kind='text', locator='paragraph 1', quote=quote))


TINY_PDF = (b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
            b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
            b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R'
            b'/Resources<</Font<</F1 5 0 R>>>>>>endobj\n'
            b'4 0 obj<</Length 44>>stream\nBT /F1 18 Tf 20 40 Td (Hello PDF) Tj ET\nendstream endobj\n'
            b'5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n'
            b'trailer<</Root 1 0 R>>\n%%EOF\n')


if __name__ == '__main__':
    unittest.main()
