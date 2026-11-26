import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, call, patch

import launchpy


class ExtractPropertiesTests(unittest.TestCase):
    def setUp(self):
        admin_patch = patch("launchpy.Admin", autospec=True)
        self.admin = admin_patch.start().return_value
        self.addCleanup(admin_patch.stop)
        self.admin.getCompanyId.return_value = "COexample"
        self.properties = [
            {
                "id": f"PR{index}",
                "attributes": {"name": f"Export {index}"},
                "relationships": {},
            }
            for index in range(4)
        ]
        self.admin.getProperties.return_value = self.properties

    def test_extracts_filtered_properties_concurrently_with_worker_limit(self):
        self.admin.getProperties.return_value = self.properties + [
            {"id": "PRskip", "attributes": {"name": "Skip"}},
        ]
        barrier = threading.Barrier(2)
        lock = threading.Lock()
        active = 0
        peak = 0
        main_thread = threading.get_ident()

        def extract(prop, publishedVersion=False):
            nonlocal active, peak
            self.assertNotEqual(threading.get_ident(), main_thread)
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                barrier.wait(timeout=5)
            finally:
                with lock:
                    active -= 1

        with patch("launchpy.extractProperty", side_effect=extract) as extract_property:
            result = launchpy.extractProperties(
                filter=r"^Export \d$", publishedVersion=True, max_workers=2
            )

        self.assertIsNone(result)
        self.assertEqual(active, 0)
        self.assertEqual(peak, 2)
        self.admin.getCompanyId.assert_called_once_with()
        self.admin.getProperties.assert_called_once_with("COexample")
        self.assertCountEqual(
            extract_property.call_args_list,
            [call(prop, publishedVersion=True) for prop in self.properties],
        )

    def test_propagates_worker_errors(self):
        self.admin.getProperties.return_value = self.properties[:1]
        with patch("launchpy.extractProperty", side_effect=RuntimeError("export failed")):
            with self.assertRaisesRegex(RuntimeError, "export failed"):
                launchpy.extractProperties()

    def test_empty_or_unmatched_properties_are_not_extracted(self):
        for properties in ([], self.properties):
            with self.subTest(properties=properties):
                self.admin.getProperties.return_value = properties
                with patch("launchpy.extractProperty") as extract_property:
                    self.assertIsNone(launchpy.extractProperties(filter="No match"))
                extract_property.assert_not_called()

    def test_nested_threads_and_async_exports_finish_before_returning(self):
        self.admin.getProperties.return_value = self.properties[:2]
        barrier = threading.Barrier(2)
        loops = []
        apis = {}
        rule = {"id": "RLexample"}
        data_element = {"attributes": {"name": "Data element"}}
        extension = {"attributes": {"name": "Extension"}}

        def fetch_rules():
            barrier.wait(timeout=5)
            return [rule]

        def get_rules():
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(fetch_rules).result()

        for prop in self.properties[:2]:
            api = Mock(spec=launchpy.Property)
            api.name = prop["attributes"]["name"]
            api.header = {}
            api.connector = Mock(proxy=None)
            api.getRules.side_effect = get_rules
            api.getDataElements.return_value = [data_element]
            api.getExtensions.return_value = [extension]
            apis[prop["id"]] = api

        async def extract_components(rule, client, folder, header):
            loops.append(asyncio.get_running_loop())
            await asyncio.sleep(0)

        extract_property = launchpy.extractProperty
        with tempfile.TemporaryDirectory() as folder:
            def export(prop, publishedVersion=False):
                extract_property(
                    prop,
                    publishedVersion=publishedVersion,
                    folder=str(Path(folder) / prop["id"]),
                )

            with (
                patch("launchpy.Property", side_effect=lambda prop: apis[prop["id"]]),
                patch("launchpy.extractProperty", side_effect=export),
                patch("launchpy.httpx.AsyncClient"),
                patch("launchpy.__extractRuleComponents__", side_effect=extract_components),
            ):
                launchpy.extractProperties(max_workers=2)

            for prop in self.properties[:2]:
                root = Path(folder) / prop["id"]
                for subfolder, name, expected in (
                    ("data_elements", "data_element.json", data_element),
                    ("extensions", "extension.json", extension),
                ):
                    with (root / subfolder / name).open() as exported:
                        self.assertEqual(json.load(exported), expected)

        self.assertEqual(len(loops), 2)
        self.assertIsNot(loops[0], loops[1])
        self.assertTrue(all(loop.is_closed() for loop in loops))


if __name__ == "__main__":
    unittest.main()
