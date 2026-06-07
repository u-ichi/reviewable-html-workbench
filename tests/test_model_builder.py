from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.image_assets import attach_image_to_model
from scripts.html_review_workbench.model_builder import build_model, build_model_from_source
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.validate_bundle import validate_bundle


ROOT = Path(__file__).resolve().parents[1]


class ModelBuilderTest(unittest.TestCase):
    def test_build_model_from_text_creates_table_block(self) -> None:
        model = build_model(
            "比較\nOption | Cost | Speed\nA | Low | Fast\nB | High | Slow",
            title="Comparison",
            document_id="comparison",
        )

        self.assertEqual(model["document_id"], "comparison")
        self.assertEqual(model["blocks"][0]["type"], "html")
        self.assertIn("<table>", model["blocks"][0]["content"])

    def test_build_model_creates_ordered_list_block(self) -> None:
        model = build_model("手順\n1. Gather input\n2. Build model\n3. Render HTML", title="Steps")

        self.assertEqual(model["blocks"][0]["type"], "html")
        self.assertIn("<ol>", model["blocks"][0]["content"])

    def test_build_model_creates_diagram_block_for_flow(self) -> None:
        model = build_model("処理フロー\nInput -> Planner -> HTML", title="Flow")

        block = model["blocks"][0]
        self.assertEqual(block["type"], "diagram")
        self.assertIn("flowchart TD", block["diagram_source"])
        self.assertEqual(block["image"]["generation_status"], "requested")
        self.assertIn("Mermaid source", block["image"]["prompt"])
        self.assertIn("white background", block["image"]["prompt"])

    def test_build_model_creates_image_block_requiring_generation(self) -> None:
        model = build_model("画面イメージとしてレビューUIのスクリーンショット風画像を入れる。", title="Screen")

        block = model["blocks"][0]
        self.assertEqual(block["type"], "image")
        self.assertEqual(block["image"]["generation_status"], "requested")
        self.assertIn("prompt", block["image"])
        self.assertIn("business document", block["image"]["prompt"])
        self.assertIn("do not invent", block["image"]["prompt"])

    def test_structured_content_wins_over_image_keyword(self) -> None:
        table_model = build_model("比較\nStep | Tool\nbuild | imagegen", title="Comparison")
        flow_model = build_model("処理フロー\nInput -> imagegen -> HTML", title="Flow")

        self.assertEqual(table_model["blocks"][0]["type"], "html")
        self.assertIn("<table>", table_model["blocks"][0]["content"])
        self.assertEqual(flow_model["blocks"][0]["type"], "diagram")

    def test_callout_priority_wins_over_visual_keywords(self) -> None:
        model = build_model("注意事項\n重要: 入力内容に応じて表現方法を選ぶ。", title="Caution")

        block = model["blocks"][0]
        self.assertEqual(block["type"], "callout")
        self.assertNotIn("image", block)

    def test_generated_html_escapes_unsafe_input(self) -> None:
        model = build_model("<script>alert(1)</script>\n<button onclick='x'>Run</button>", title="Unsafe")

        content = model["blocks"][0]["content"]
        self.assertNotIn("<script>", content)
        self.assertNotIn("<button", content)
        self.assertIn("&lt;script&gt;", content)

    def test_build_model_from_file_writes_document_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            input_path = tmp_dir / "source.txt"
            output_path = tmp_dir / "document-model.json"
            input_path.write_text("決定事項\n重要: previewを既定で起動する", encoding="utf-8")

            result = build_model_from_source(input_path=input_path, output_path=output_path)

            self.assertEqual(result.path, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["blocks"][0]["type"], "callout")

    def test_cli_build_model_accepts_stdin_and_full_pipeline_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            model_path = tmp_dir / "document-model.json"
            bundle_dir = tmp_dir / "bundle"
            build = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.html_review_workbench.cli",
                    "build-model",
                    "--output",
                    str(model_path),
                    "--title",
                    "Pipeline",
                ],
                cwd=ROOT,
                input="構成\nClient -> API -> Database",
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(build.stdout.strip(), str(model_path))
            render_bundle(model_path, bundle_dir)
            result = validate_bundle(bundle_dir)

            self.assertTrue(result.ok, result.errors)
            html = (bundle_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("diagram-preview", html)

    def test_attach_image_enables_rendering_generated_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            model_path = tmp_dir / "document-model.json"
            bundle_dir = tmp_dir / "bundle"
            image_path = tmp_dir / "generated.png"
            image_path.write_bytes(_minimal_png_bytes())
            model = build_model("画面イメージとしてレビューUIのスクリーンショット風画像を生成して配置する。", title="Screen", document_id="screen")
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")

            result = attach_image_to_model(
                model_path=model_path,
                block_id=model["blocks"][0]["id"],
                image_path=image_path,
            )
            render_bundle(result.model_path, bundle_dir)

            html = (bundle_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn('<figure class="block-content generated-image">', html)
            self.assertIn("<img", html)
            self.assertTrue((bundle_dir / result.source_path).is_file())

    def test_attach_image_enables_rendering_generated_diagram_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            model_path = tmp_dir / "document-model.json"
            bundle_dir = tmp_dir / "bundle"
            image_path = tmp_dir / "generated-diagram.png"
            image_path.write_bytes(_minimal_png_bytes())
            model = build_model("処理フロー\nInput -> Planner -> HTML", title="Flow", document_id="flow")
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            block = model["blocks"][0]

            result = attach_image_to_model(
                model_path=model_path,
                block_id=block["id"],
                image_path=image_path,
            )
            render_bundle(result.model_path, bundle_dir)

            html = (bundle_dir / "index.html").read_text(encoding="utf-8")
            manifest = json.loads((bundle_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertIn('<figure class="block-content generated-image">', html)
            self.assertIn("<img", html)
            self.assertNotIn("diagram-preview", html)
            self.assertTrue((bundle_dir / result.source_path).is_file())
            self.assertEqual(manifest["outputs"]["diagrams"], [f"assets/diagrams/{block['id']}.mmd"])
            self.assertEqual(manifest["outputs"]["images"], [result.source_path])
            self.assertTrue(validate_bundle(bundle_dir).ok)

    def test_heading_source_becomes_html_sections_without_literal_markers(self) -> None:
        source = """# actas で tmux からの別 pane 相談を実現できるか

## 結論

actas だけでは、tmux の別 pane に相談する体験は完成しない。

1. 送信側: tmux の pane 指定を agmsg の宛先 agent 名へ変換する。
2. 受信側: actas で、自分がどの agent 名として受信するかを固定する。

## 評価

| 目的 | actas だけで可能か | 理由 |
| --- | --- | --- |
| 受信側が自分の agent 名を固定する | 可能 | identity 固定として使える |
| 1:4 に送る | 不可能 | tmux 状態の解決が必要 |

## 具体例

```text
agmsg-tmux-send --to 1:4 "相談内容"
agmsg-tmux-send --to right "相談内容"
```
"""

        model = build_model(source)
        model_html = "\n".join(block["title"] + "\n" + block["content"] for block in model["blocks"])

        self.assertEqual(model["title"], "actas で tmux からの別 pane 相談を実現できるか")
        self.assertEqual([block["title"] for block in model["blocks"]], ["結論", "評価", "具体例"])
        self.assertNotIn("# actas", model_html)
        self.assertNotIn("## 評価", model_html)
        self.assertNotIn("```", model_html)
        self.assertIn("<ol>", model_html)
        self.assertIn("<table>", model_html)
        self.assertIn("<pre><code>", model_html)


def _minimal_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe"
        b"\xdc\xccY\xe7"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


if __name__ == "__main__":
    unittest.main()
