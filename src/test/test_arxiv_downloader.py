import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.rag_curator.ingestion.arxiv import ArXivDownloader


class TestArXivDownloader(unittest.TestCase):
    def test_init_creates_expected_directories(self):
        with TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "arxiv_data"
            downloader = ArXivDownloader(
                data_dir=str(data_dir),
                metadata_file="papers_metadata.json",
            )

            self.assertTrue(downloader.raw_dir.exists())
            self.assertTrue(downloader.processed_dir.exists())
            self.assertIsInstance(downloader.papers_metadata, dict)

    @patch("src.rag_curator.ingestion.arxiv.urllib.request.urlopen")
    def test_search_papers_parses_response_and_builds_valid_query(self, mock_urlopen):
        mock_urlopen.return_value.read.return_value = b"""
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/2401.00001v1</id>
                <title>Test Paper Title</title>
                <summary>Example abstract.</summary>
                <published>2026-08-01T00:00:00Z</published>
                <updated>2026-08-02T00:00:00Z</updated>
                <author><name>Alice Author</name></author>
                <author><name>Bob Author</name></author>
                <category term="cs.CL" />
                <category term="cs.AI" />
                <link type="application/pdf" href="https://arxiv.org/pdf/2401.00001.pdf" />
            </entry>
        </feed>
        """

        with TemporaryDirectory() as temp_dir:
            downloader = ArXivDownloader(
                data_dir=str(Path(temp_dir) / "arxiv"),
                metadata_file="papers_metadata.json",
            )

            papers = downloader.search_papers(
                query="cat:cs.CL",
                max_results=5,
                start_date="2026-07-17",
                end_date="2026-08-16",
            )

            self.assertEqual(len(papers), 1)
            self.assertEqual(papers[0].arxiv_id, "2401.00001v1")
            self.assertEqual(papers[0].title, "Test Paper Title")
            self.assertIn("cat%3Acs.CL", mock_urlopen.call_args[0][0])
            self.assertIn("submittedDate%3A%5B2026-07-17", mock_urlopen.call_args[0][0])
            self.assertIn("submittedDate%3A%5B%2A+TO+2026-08-16%5D", mock_urlopen.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
