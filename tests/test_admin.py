import unittest
from unittest.mock import Mock, patch

from launchpy.admin import Admin
from launchpy.property import Property


class AdminSearchTests(unittest.TestCase):
    def setUp(self):
        self.connector = Mock()
        self.connector.header = {}
        self.admin = Admin(_connector=self.connector)
        self.admin.getCompanyId = Mock(return_value="COexample")
        self.properties = [
            {"id": "PRfirst", "attributes": {"name": "First property"}},
            {"id": "PRsecond", "attributes": {"name": "Second property"}},
        ]
        self.admin.getProperties = Mock(return_value=self.properties)

    @staticmethod
    def property_api(name: str) -> Mock:
        api = Mock(spec=Property)
        api.name = name
        api.getRules.return_value = [
            {"id": "RLmatch", "attributes": {"name": "Checkout rule"}},
            {"id": "RLother", "attributes": {"name": "Other rule"}},
        ]
        api.getDataElements.return_value = [
            {"id": "DEmatch", "attributes": {"name": "Checkout data element"}},
        ]
        api.getExtensions.return_value = [
            {"id": "EXmatch", "attributes": {"name": "Checkout extension"}},
        ]
        return api

    def test_search_reuses_cached_matches_and_admin_connector(self):
        self.admin.getProperties.return_value = self.properties[:1]
        api = self.property_api("First property")
        expected = [
            {
                "property": "First property",
                "type": kind,
                "component": component,
            }
            for kind, component in (
                ("rule", api.getRules.return_value[0]),
                ("dataElement", api.getDataElements.return_value[0]),
                ("extension", api.getExtensions.return_value[0]),
            )
        ]

        with (
            patch("launchpy.admin.Property", return_value=api) as constructor,
            patch("builtins.print") as output,
        ):
            self.assertEqual(self.admin.searchComponent("Checkout"), expected)
            self.assertEqual(self.admin.searchComponent("Checkout"), expected)

        constructor.assert_called_once_with(
            self.properties[0], _connector=self.connector
        )
        api.getRules.assert_called_once_with()
        api.getDataElements.assert_called_once_with()
        api.getExtensions.assert_called_once_with()
        output.assert_not_called()

    def test_search_prints_property_errors_and_continues(self):
        for failure_stage in (
            "constructor", "getRules", "getDataElements", "getExtensions",
        ):
            with self.subTest(failure_stage=failure_stage):
                self.admin.cacheProperties.clear()
                failing = self.property_api("First property")
                healthy = self.property_api("Second property")
                error = RuntimeError(f"{failure_stage} failed")
                if failure_stage != "constructor":
                    getattr(failing, failure_stage).side_effect = error

                def construct(prop, **kwargs):
                    if prop["id"] == "PRfirst":
                        if failure_stage == "constructor":
                            raise error
                        return failing
                    return healthy

                with (
                    patch("launchpy.admin.Property", side_effect=construct),
                    patch("builtins.print") as output,
                ):
                    results = self.admin.searchComponent("Checkout")

                self.assertEqual(len(results), 3)
                self.assertTrue(
                    all(result["property"] == "Second property" for result in results)
                )
                output.assert_called_once()
                message = output.call_args.args[0]
                self.assertIn("First property", message)
                self.assertIn(str(error), message)
                self.assertNotIn("First property", self.admin.cacheProperties)

    def test_search_prints_cached_component_errors_and_continues(self):
        self.admin.cacheProperties["First property"] = {
            "rules": [{"id": "RLinvalid"}],
            "dataelements": [],
            "extensions": [],
        }
        healthy = self.property_api("Second property")

        with (
            patch("launchpy.admin.Property", return_value=healthy) as constructor,
            patch("builtins.print") as output,
        ):
            results = self.admin.searchComponent("Checkout")

        self.assertEqual(len(results), 3)
        self.assertTrue(
            all(result["property"] == "Second property" for result in results)
        )
        constructor.assert_called_once_with(
            self.properties[1], _connector=self.connector
        )
        output.assert_called_once()
        self.assertIn("First property", output.call_args.args[0])
        self.assertIn("attributes", output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
