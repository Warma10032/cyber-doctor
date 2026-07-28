import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch


class YoucomSearchTests(unittest.TestCase):
    def setUp(self):
        self.original_env = sys.modules.get("env")
        fake_env = types.ModuleType("env")
        fake_env.get_env_value = lambda _key: "test-api-key"
        sys.modules["env"] = fake_env
        sys.modules.pop("Internet.youcom_search", None)
        self.youcom = importlib.import_module("Internet.youcom_search")

    def tearDown(self):
        sys.modules.pop("Internet.youcom_search", None)
        if self.original_env is None:
            sys.modules.pop("env", None)
        else:
            sys.modules["env"] = self.original_env

    def test_search_formats_web_and_news_results(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "results": {
                "web": [
                    {
                        "title": "Web result",
                        "url": "https://web.example",
                        "snippets": ["Web snippet"],
                    }
                ],
                "news": [
                    {
                        "title": "News result",
                        "url": "https://news.example",
                        "snippets": ["News snippet"],
                    }
                ],
            }
        }

        with patch.object(self.youcom.requests, "post", return_value=response) as post:
            result = self.youcom.search_news("diabetes", count=2)

        self.assertIn("Web result", result)
        self.assertIn("News result", result)
        self.assertEqual(post.call_args.kwargs["json"], {"query": "diabetes", "count": 2})

    def test_research_reads_official_response_shape(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "output": {
                "content": "## Findings\n\nResearch body [[1]]",
                "sources": [
                    {
                        "title": "Primary source",
                        "url": "https://source.example",
                        "snippets": ["Supporting evidence"],
                    }
                ],
            }
        }

        with patch.object(self.youcom.requests, "post", return_value=response) as post:
            result = self.youcom.research_news("diabetes treatment")

        self.assertIn("Research body [[1]]", result)
        self.assertIn("Primary source", result)
        self.assertEqual(post.call_args.args[0], "https://api.you.com/v1/research")


class DeepResearchIntentTests(unittest.TestCase):
    def test_keyword_routes_to_deep_research_without_calling_llm(self):
        fake_clientfactory = types.ModuleType("client.clientfactory")

        class Clientfactory:
            def get_client(self):
                raise AssertionError("DeepResearch keyword should not invoke the LLM classifier")

        fake_clientfactory.Clientfactory = Clientfactory
        previous_module = sys.modules.pop("qa.question_parser", None)
        previous_clientfactory = sys.modules.get("client.clientfactory")
        sys.modules["client.clientfactory"] = fake_clientfactory
        try:
            parser = importlib.import_module("qa.question_parser")
            self.assertEqual(
                parser.parse_question("请深度研究糖尿病治疗的最新进展"),
                parser.purpose_map["深度研究"],
            )
        finally:
            sys.modules.pop("qa.question_parser", None)
            if previous_module is not None:
                sys.modules["qa.question_parser"] = previous_module
            if previous_clientfactory is None:
                sys.modules.pop("client.clientfactory", None)
            else:
                sys.modules["client.clientfactory"] = previous_clientfactory


if __name__ == "__main__":
    unittest.main()
