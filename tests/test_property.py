import threading
import unittest
from unittest.mock import Mock, patch

from launchpy.property import Property


class PublishedFilteringTests(unittest.TestCase):
    def setUp(self):
        self.connector = Mock(header={})
        self.property = Property(
            {
                "id": "PRexample",
                "attributes": {
                    "name": "Example",
                    "platform": "web",
                    "development": False,
                    "domains": [],
                },
                "links": {
                    name: f"https://example.invalid/{name}"
                    for name in ("data_elements", "extensions", "rules", "environments")
                },
                "relationships": {
                    "libraries": {"links": {"related": "https://example.invalid/libraries"}}
                },
            },
            _connector=self.connector,
        )
        self.components = [
            {
                "id": f"component-{index}",
                "attributes": {"name": f"Component {index}", "published": False},
                "links": {
                    "rule_components": f"https://example.invalid/component-{index}/parts"
                },
            }
            for index in range(10)
        ]
        self.response = {
            "data": self.components,
            "meta": {"pagination": {"current_page": 1, "total_pages": 1}},
        }
        self.connector.getData.return_value = self.response
        self.methods = (self.property.getRules, self.property.getDataElements)

    def test_published_checks_run_concurrently_with_five_worker_limit(self):
        for method in self.methods:
            with self.subTest(method=method.__name__):
                barrier = threading.Barrier(5)
                lock = threading.Lock()
                active = 0
                peak = 0
                main_thread = threading.get_ident()

                def find_published_version(component):
                    nonlocal active, peak
                    self.assertNotEqual(threading.get_ident(), main_thread)
                    with lock:
                        active += 1
                        peak = max(peak, active)
                    try:
                        barrier.wait(timeout=5)
                        return component
                    finally:
                        with lock:
                            active -= 1

                with patch.object(
                    self.property, "getLatestPublishedVersion",
                    side_effect=find_published_version,
                ) as find:
                    self.assertEqual(method(published=True), self.components)

                self.assertEqual(find.call_count, len(self.components))
                self.assertEqual(peak, 5)
                self.assertEqual(active, 0)

    def test_filters_by_publication_history_in_input_order(self):
        def get_revisions(element):
            index = int(element["id"].split("-")[1])
            return [
                {"attributes": {"revision_number": 1, "published": index % 2 == 0}},
                {"attributes": {"revision_number": 2, "published": False}},
            ]

        for method in self.methods:
            for published in (True, False):
                with self.subTest(method=method.__name__, published=published):
                    with patch.object(
                        self.property, "getRevisions", side_effect=get_revisions,
                    ) as get:
                        result = method(published=published)

                    expected = [
                        component
                        for index, component in enumerate(self.components)
                        if (index % 2 == 0) == published
                    ]
                    self.assertEqual(result, expected)
                    self.assertEqual(get.call_count, len(self.components))

        self.assertEqual(
            self.property.ruleComponents,
            {
                component["id"]: {
                    "name": component["attributes"]["name"],
                    "url": component["links"]["rule_components"],
                }
                for component in self.components
            },
        )

    def test_none_skips_revision_checks(self):
        for method in self.methods:
            with self.subTest(method=method.__name__):
                with patch.object(self.property, "getLatestPublishedVersion") as find:
                    self.assertEqual(method(published=None), self.components)
                find.assert_not_called()

    def test_empty_results_skip_revision_checks(self):
        self.response["data"] = []
        for method in self.methods:
            for published in (None, True, False):
                with self.subTest(method=method.__name__, published=published):
                    with patch.object(self.property, "getLatestPublishedVersion") as find:
                        self.assertEqual(method(published=published), [])
                    find.assert_not_called()

    def test_unexpected_worker_errors_propagate(self):
        for method in self.methods:
            with self.subTest(method=method.__name__):
                with patch.object(
                    self.property, "getLatestPublishedVersion",
                    side_effect=RuntimeError("revision lookup failed"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "revision lookup failed"):
                        method(published=True)


if __name__ == "__main__":
    unittest.main()
