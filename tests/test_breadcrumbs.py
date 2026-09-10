import json
from pathlib import Path
import tempfile
import unittest
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.publish import publish_bundle
from scripts.html_review_workbench.model_quality import check_model_quality
ROOT = Path(__file__).resolve().parents[1]

class BreadcrumbTest(unittest.TestCase):
    def test_parent_links_are_in_header_and_survive_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = json.loads((ROOT / 'tests/fixtures/minimal_document_model.json').read_text())
            model['title'] = 'CRC & 医師'
            model['metadata']['breadcrumbs'] = [{'label': '全体像', 'href': '../index.html'}, {'label': 'ペルソナ <一覧>', 'href': '../personas/index.html'}]
            source = root / 'model.json'
            source.write_text(json.dumps(model))
            preview = render_bundle(source, root / 'preview').read_text()
            header = preview.split('id="document-header"', 1)[1].split('</header>', 1)[0]
            self.assertIn('aria-label="パンくずリスト"', header)
            self.assertIn('href="../personas/index.html"', header)
            self.assertIn('ペルソナ &lt;一覧&gt;', header)
            self.assertIn('aria-current="page">CRC &amp; 医師', header)
            publish_bundle(root / 'preview', root / 'published')
            published = (root / 'published/index.html').read_text()
            self.assertIn('href="../personas/index.html"', published)
            self.assertIn('aria-current="page">CRC &amp; 医師', published)

    def test_optional_input_preserves_standalone_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = render_bundle(ROOT / 'tests/fixtures/minimal_document_model.json', Path(tmp)).read_text()
            self.assertNotIn('class="doc-breadcrumb"', html)

    def test_invalid_links_fail_quality_check_and_render(self):
        for href in ['javascript:alert(1)', 'data:text/html,test', '', '//other.example', ' /path']:
            with self.subTest(href=href), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                model = json.loads((ROOT / 'tests/fixtures/minimal_document_model.json').read_text())
                model['metadata']['breadcrumbs'] = [{'label': 'parent', 'href': href}]
                source = root / 'model.json'
                source.write_text(json.dumps(model))
                self.assertTrue(any('breadcrumb' in e for e in check_model_quality(source).errors))
                with self.assertRaises(ValueError):
                    render_bundle(source, root / 'preview')
