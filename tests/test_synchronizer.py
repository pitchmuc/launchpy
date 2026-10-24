from copy import deepcopy
import threading
import unittest
from unittest.mock import Mock, patch

from launchpy.cli.__main__ import SynchronizerCLI
from launchpy.launchpy import Translator
from launchpy.property import Property
from launchpy.synchronizer import Synchronizer


def component(kind: str, identifier: str, enabled: bool) -> dict:
    data = {
        "id": identifier,
        "type": kind,
        "attributes": {
            "name": "Sample component",
            "enabled": enabled,
            "published": False,
            "revision_number": 2,
        },
        "links": {
            "self": "https://example.invalid/" + identifier,
            "origin": "https://example.invalid/" + identifier,
        },
        "relationships": {
            "rule_components": {"links": {"related": "mock:components"}},
        },
    }
    if kind == "data_elements":
        data["attributes"].update(
            settings="{}",
            delegate_descriptor_id="core::dataElements::custom-code",
            storage_duration="pageview",
            force_lower_case=False,
            default_value="",
            clean_text=False,
        )
        data["relationships"]["extension"] = {
            "data": {"id": "EXbase", "type": "extensions"},
        }
    return data


class SynchronizerTests(unittest.TestCase):
    def make_sync(
        self, kind: str, source_enabled: bool = False, target_enabled: bool = True
    ) -> tuple[Synchronizer, dict, dict]:
        prefix = "RL" if kind == "rules" else "DE"
        source = component(kind, prefix + "base", source_enabled)
        target = component(kind, prefix + "target", target_enabled)
        key = "rules" if kind == "rules" else "dataElements"
        source_api = Mock(spec=Property)
        source_api.connector = Mock()
        target_api = Mock(spec=Property)
        source_api.getRessource.return_value = {"data": []}
        target_api.getRessource.return_value = {"data": []}
        source_api.getRevisions.return_value = [source]
        target_api.getRevisions.return_value = [target]
        source_api.getLatestPublishedVersion.return_value = source
        target_api.getLatestPublishedVersion.return_value = target
        target_api.updateDataElement.side_effect = (
            lambda dataElement_id, attr_dict: self.updated(target, attr_dict)
        )
        target_api.updateRule.side_effect = (
            lambda rule_id, attr_dict: self.updated(target, attr_dict)
        )
        sync = Synchronizer.__new__(Synchronizer)
        sync.base = {
            "name": "Base",
            "api": source_api,
            "rules": [],
            "dataElements": [],
            "extensions": [],
        }
        sync.base[key] = [source]
        sync.targets = {
            "Target": {
                "api": target_api,
                "rules": [],
                "dataElements": [],
                "libraryStack": {"rules": [], "dataElements": [], "extensions": []},
            },
        }
        sync.targets["Target"][key] = [target]
        sync.target_configs = {}
        sync._base_lock = threading.Lock()
        sync._target_locks = {"Target": threading.Lock()}
        sync.translator = Translator()
        sync.translator.setBaseExtensions(
            [{"id": "EXbase", "attributes": {"name": "core"}}], "Base"
        )
        sync.translator.extendExtensions(
            [{"id": "EXtarget", "attributes": {"name": "core"}}], "Target"
        )
        sync.translator.setBaseRules(sync.base["rules"], "Base")
        sync.translator.extendRules(sync.targets["Target"]["rules"], "Target")
        return sync, source, target

    @staticmethod
    def updated(target: dict, attributes: dict) -> dict:
        result = deepcopy(target)
        result["attributes"].update(attributes)
        return result

    def test_created_data_element_update_uses_api_attributes_and_tracks_response(self):
        for source_enabled in (False, True):
            with self.subTest(source_enabled=source_enabled):
                sync, source, created = self.make_sync(
                    "data_elements", source_enabled, not source_enabled
                )
                target = sync.targets["Target"]
                target["dataElements"] = []
                api = target["api"]
                api.createDataElement.return_value = created
                attributes = {
                    "name": source["attributes"]["name"],
                    "enabled": source_enabled,
                    "delegate_descriptor_id": source["attributes"]["delegate_descriptor_id"],
                    "storage_duration": source["attributes"]["storage_duration"],
                    "force_lower_case": source["attributes"]["force_lower_case"],
                    "clean_text": source["attributes"]["clean_text"],
                    "settings": source["attributes"]["settings"],
                    "default_value": source["attributes"]["default_value"],
                }
                updated = self.updated(created, attributes)
                updated["attributes"]["revision_number"] += 1
                api.updateDataElement.side_effect = None
                api.updateDataElement.return_value = updated

                result = sync.syncComponent(componentId=source["id"], forceCreation=True)

                api.updateDataElement.assert_called_once_with(
                    dataElement_id=created["id"], attr_dict=attributes
                )
                self.assertEqual(
                    result,
                    {"Target": 'Data element "Sample component" created in "Target".'},
                )
                self.assertEqual(len(target["dataElements"]), 1)
                self.assertEqual(len(target["libraryStack"]["dataElements"]), 1)
                self.assertIs(target["dataElements"][0], updated)
                self.assertIs(target["libraryStack"]["dataElements"][0], updated)
                self.assertIs(created["attributes"]["enabled"], not source_enabled)
                self.assertEqual(
                    sync.checkComponentSync(componentId=source["id"])["Target"], "Similar"
                )

    def test_created_data_element_needs_no_update_when_enabled_state_matches(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                sync, source, created = self.make_sync("data_elements", enabled, enabled)
                target = sync.targets["Target"]
                target["dataElements"] = []
                api = target["api"]
                api.createDataElement.return_value = created

                sync.syncComponent(componentId=source["id"], forceCreation=True)

                api.updateDataElement.assert_not_called()
                self.assertEqual(target["dataElements"], [created])
                self.assertEqual(target["libraryStack"]["dataElements"], [created])

    def test_created_data_element_update_failure_is_not_cached_as_success(self):
        sync, source, created = self.make_sync("data_elements")
        target = sync.targets["Target"]
        target["dataElements"] = []
        api = target["api"]
        api.createDataElement.return_value = created
        api.updateDataElement.side_effect = RuntimeError("Data element update failed")

        with self.assertRaisesRegex(RuntimeError, "Data element update failed"):
            sync.syncComponent(componentId=source["id"], forceCreation=True)

        self.assertEqual(target["dataElements"], [])
        self.assertEqual(target["libraryStack"]["dataElements"], [])

    def test_enabled_mismatches_are_reported_in_all_comparison_modes(self):
        for kind, label in (("rules", "Rule"), ("data_elements", "Data Element")):
            for enabled in (False, True):
                for published in (False, True):
                    for exclude_similar in (False, True):
                        with self.subTest(
                            kind=kind, enabled=enabled, published=published,
                            exclude_similar=exclude_similar,
                        ):
                            sync, source, target = self.make_sync(
                                kind, enabled, not enabled
                            )
                            result = sync.checkComponentSync(
                                componentId=source["id"],
                                publishedVersion=published,
                                excludeSimilar=exclude_similar,
                            )
                            self.assertEqual(
                                result["Target"], f"{label} enabled status is different"
                            )

    def test_matching_components_preserve_similar_and_exclude_similar_results(self):
        for kind in ("rules", "data_elements"):
            for published in (False, True):
                for exclude_similar in (False, True):
                    with self.subTest(
                        kind=kind, published=published, exclude_similar=exclude_similar,
                    ):
                        sync, source, target = self.make_sync(kind, False, False)
                        result = sync.checkComponentSync(
                            componentId=source["id"],
                            publishedVersion=published,
                            excludeSimilar=exclude_similar,
                        )
                        self.assertEqual(result["Target"], "" if exclude_similar else "Similar")

    def test_data_element_comparison_retains_all_differences(self):
        sync, source, target = self.make_sync("data_elements")
        source["attributes"]["published"] = True
        target["attributes"]["settings"] = '{"different": true}'
        result = sync.checkComponentSync(componentId=source["id"], publishedVersion=True)
        self.assertEqual(
            result["Target"],
            "Data Element enabled status is different,"
            "Data Element published status is different,"
            "Data Element settings are different",
        )

    def test_data_element_published_difference_is_not_overwritten_by_similar_settings(self):
        sync, source, target = self.make_sync("data_elements", False, False)
        source["attributes"]["published"] = True
        result = sync.checkComponentSync(componentId=source["id"], publishedVersion=True)
        self.assertEqual(result["Target"], "Data Element published status is different")

    def test_comparison_reports_enabled_difference_when_target_has_no_published_revision(self):
        for kind, label, suffix in (
            ("rules", "Rule", " (not published)"),
            ("data_elements", "Data Element", " (draft)"),
        ):
            with self.subTest(kind=kind):
                sync, source, target = self.make_sync(kind)
                sync.targets["Target"]["api"].getLatestPublishedVersion.side_effect = (
                    IndexError("No published revision")
                )
                result = sync.checkComponentSync(
                    componentId=source["id"], publishedVersion=True
                )
                self.assertEqual(
                    result["Target"], f"{label} enabled status is different{suffix}"
                )

    def test_library_dry_run_reports_enabled_differences(self):
        for kind, label in (("rules", "Rule"), ("data_elements", "Data Element")):
            for published in (False, True):
                with self.subTest(kind=kind, published=published):
                    sync, source, target = self.make_sync(kind)
                    api = sync.base["api"]
                    api.getLibraries.return_value = [
                        {"id": "LBbase", "attributes": {"name": "Base library"}},
                    ]
                    api.getRule.return_value = source
                    api.getDataElement.return_value = source
                    library = Mock()
                    library.getFullLibrary.return_value = {
                        "rules": [source] if kind == "rules" else [],
                        "data_elements": [source] if kind == "data_elements" else [],
                        "extensions": [],
                    }
                    with patch("launchpy.synchronizer.Library", return_value=library):
                        result = sync.syncFromLibrary(
                            library="LBbase", dryRun=True, publishedVersion=published
                        )
                    self.assertEqual(
                        result[source["attributes"]["name"]]["Target"],
                        f"{label} enabled status is different",
                    )
                    sync.targets["Target"]["api"].updateRule.assert_not_called()
                    sync.targets["Target"]["api"].updateDataElement.assert_not_called()

    def test_bulk_sync_defaults_to_including_disabled_components(self):
        for kind in ("rules", "data_elements"):
            for options in ({}, {"ignoreDisabled": False}):
                with self.subTest(kind=kind, options=options):
                    sync, source, target = self.make_sync(kind)
                    method = sync.syncRules if kind == "rules" else sync.syncDataElements
                    result = method(**options)
                    self.assertIn("Target", result[source["attributes"]["name"]])
                    update = (
                        sync.targets["Target"]["api"].updateRule
                        if kind == "rules"
                        else sync.targets["Target"]["api"].updateDataElement
                    )
                    self.assertIs(update.call_args.kwargs["attr_dict"]["enabled"], False)

    def test_bulk_sync_ignores_disabled_components_without_touching_targets(self):
        for kind in ("rules", "data_elements"):
            for force_creation in (False, True):
                for target_exists in (False, True):
                    with self.subTest(
                        kind=kind, force_creation=force_creation,
                        target_exists=target_exists,
                    ):
                        sync, source, target = self.make_sync(kind)
                        if not target_exists:
                            key = "rules" if kind == "rules" else "dataElements"
                            sync.targets["Target"][key] = []
                        method = sync.syncRules if kind == "rules" else sync.syncDataElements
                        result = method(ignoreDisabled=True, forceCreation=force_creation)
                        self.assertEqual(result, {source["attributes"]["name"]: {}})
                        self.assertEqual(sync.targets["Target"]["api"].mock_calls, [])
                        self.assertEqual(sync.base["api"].mock_calls, [])
                        self.assertEqual(
                            sync.targets["Target"]["libraryStack"],
                            {"rules": [], "dataElements": [], "extensions": []},
                        )

    def test_bulk_sync_only_updates_enabled_components_in_a_mixed_batch(self):
        for kind in ("rules", "data_elements"):
            with self.subTest(kind=kind):
                sync, source, target = self.make_sync(kind)
                key = "rules" if kind == "rules" else "dataElements"
                enabled_source = deepcopy(source)
                enabled_source["id"] += "enabled"
                enabled_source["attributes"].update(name="Enabled component", enabled=True)
                enabled_target = deepcopy(target)
                enabled_target["id"] += "enabled"
                enabled_target["attributes"].update(name="Enabled component", enabled=False)
                sync.base[key].append(enabled_source)
                sync.targets["Target"][key].append(enabled_target)
                api = sync.targets["Target"]["api"]
                update = api.updateRule if kind == "rules" else api.updateDataElement
                update.side_effect = lambda **kwargs: self.updated(
                    enabled_target, kwargs["attr_dict"]
                )
                method = sync.syncRules if kind == "rules" else sync.syncDataElements
                result = method(ignoreDisabled=True)
                self.assertEqual(result[source["attributes"]["name"]], {})
                self.assertIn("Target", result["Enabled component"])
                update.assert_called_once()
                self.assertIs(update.call_args.kwargs["attr_dict"]["enabled"], True)

    def test_bulk_sync_still_syncs_enabled_components_to_disabled_targets(self):
        for kind in ("rules", "data_elements"):
            with self.subTest(kind=kind):
                sync, source, target = self.make_sync(kind, True, False)
                method = sync.syncRules if kind == "rules" else sync.syncDataElements
                result = method(ignoreDisabled=True)
                self.assertIn("Target", result[source["attributes"]["name"]])
                key = "rules" if kind == "rules" else "dataElements"
                self.assertIs(
                    sync.targets["Target"][key][0]["attributes"]["enabled"], True
                )

    def test_bulk_sync_filters_the_selected_published_revision(self):
        for kind in ("rules", "data_elements"):
            for published_enabled in (False, True):
                with self.subTest(kind=kind, published_enabled=published_enabled):
                    sync, source, target = self.make_sync(
                        kind, not published_enabled, not published_enabled
                    )
                    revision = deepcopy(source)
                    revision["id"] += "revision"
                    revision["attributes"]["enabled"] = published_enabled
                    revision["attributes"]["published"] = True
                    sync.base["api"].getLatestPublishedVersion.return_value = revision
                    method = sync.syncRules if kind == "rules" else sync.syncDataElements
                    result = method(ignoreDisabled=True, publishedVersion=True)
                    sync.base["api"].getRevisions.assert_called_once_with(source)
                    if published_enabled:
                        self.assertIn("Target", result[source["attributes"]["name"]])
                    else:
                        self.assertEqual(result[source["attributes"]["name"]], {})
                        self.assertEqual(sync.targets["Target"]["api"].mock_calls, [])

    def test_bulk_sync_keeps_regex_filtering(self):
        for kind in ("rules", "data_elements"):
            with self.subTest(kind=kind):
                sync, source, target = self.make_sync(kind, True, False)
                method = sync.syncRules if kind == "rules" else sync.syncDataElements
                self.assertEqual(method(regex="Does not match", ignoreDisabled=True), {})
                self.assertEqual(sync.targets["Target"]["api"].mock_calls, [])


class SynchronizerCLITests(unittest.TestCase):
    def test_ignore_disabled_accepts_optional_boolean_and_bare_flags(self):
        options = (
            ("", False),
            ("-i", True),
            ("--ignore_disabled", True),
            ("-i True", True),
            ("--ignore_disabled true", True),
            ("-i False", False),
            ("--ignore_disabled false", False),
            ("--ignore_disabled=False", False),
        )
        for command, method_name in (
            ("do_sync_rules", "syncRules"),
            ("do_sync_data_elements", "syncDataElements"),
        ):
            for arguments, expected in options:
                with self.subTest(command=command, arguments=arguments):
                    sync = Mock(spec=Synchronizer)
                    sync.base = {"name": "Base"}
                    method = getattr(sync, method_name)
                    method.return_value = {}
                    shell = SynchronizerCLI(sync)
                    with patch("launchpy.cli.__main__.console") as console:
                        getattr(shell, command)(arguments + " -r Sample -c -p")
                    method.assert_called_once_with(
                        regex="Sample", forceCreation=True, publishedVersion=True,
                        ignoreDisabled=expected,
                    )
                    console.print.assert_not_called()

    def test_ignore_disabled_rejects_invalid_boolean_without_syncing(self):
        for command, method_name in (
            ("do_sync_rules", "syncRules"),
            ("do_sync_data_elements", "syncDataElements"),
        ):
            with self.subTest(command=command):
                sync = Mock(spec=Synchronizer)
                sync.base = {"name": "Base"}
                shell = SynchronizerCLI(sync)
                with patch("sys.stderr") as stderr:
                    getattr(shell, command)("--ignore_disabled invalid")
                getattr(sync, method_name).assert_not_called()
                self.assertTrue(stderr.write.called)


if __name__ == "__main__":
    unittest.main()
