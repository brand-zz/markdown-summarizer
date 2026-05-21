import unittest
import tempfile
import os
from unittest.mock import patch
from docusaurus_frontmatter import process_file

class TestDocusaurusFrontmatter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.test1_path = os.path.join(self.test_dir.name, "test1.md")
        self.test2_path = os.path.join(self.test_dir.name, "test2.md")

        with open(self.test1_path, "w", encoding="utf-8") as f:
            f.write("# Hello World\nThis is a test document about Python programming.\nIt talks about functions, variables, and classes.\n")

        with open(self.test2_path, "w", encoding="utf-8") as f:
            f.write("---\nid: test2\ntitle: Existing Front Matter\n---\n# Test 2\nThis file has existing front matter.\n")

    def tearDown(self):
        self.test_dir.cleanup()

    @patch('docusaurus_frontmatter.generate_front_matter')
    def test_process_file_no_frontmatter(self, mock_gen):
        mock_gen.return_value = "description: This is a test description.\nkeywords: [test, mock, file]"

        process_file(self.test1_path, "gemini-2.5-flash-lite", False)

        with open(self.test1_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("description: This is a test description.", content)
        self.assertIn("- test\n- mock\n- file", content)
        self.assertIn("# Hello World", content)

    @patch('docusaurus_frontmatter.generate_front_matter')
    def test_process_file_existing_frontmatter(self, mock_gen):
        mock_gen.return_value = "description: This is a test description.\nkeywords: [test, mock, file]"

        process_file(self.test2_path, "gemini-2.5-flash-lite", False)

        with open(self.test2_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("description: This is a test description.", content)
        self.assertIn("- test\n- mock\n- file", content)
        self.assertIn("id: test2", content)
        self.assertIn("title: Existing Front Matter", content)
        self.assertIn("# Test 2", content)

if __name__ == '__main__':
    unittest.main()
