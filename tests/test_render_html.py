from __future__ import annotations

import unittest

from src.render_html import markdown_to_html


class RenderHtmlTests(unittest.TestCase):
    def test_basic_markdown_rendering(self) -> None:
        html = markdown_to_html("# Title\n\n## Section\n\n- Item\n\n| A | B |\n| --- | --- |\n| 1 | 2 |")

        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<h2>Section</h2>", html)
        self.assertIn("<li>Item</li>", html)
        self.assertIn("<table>", html)
        self.assertIn("<th>A</th>", html)


if __name__ == "__main__":
    unittest.main()
