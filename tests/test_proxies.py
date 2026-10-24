import asyncio
import json
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import AsyncMock, Mock, patch

import launchpy
from launchpy.cli.__main__ import MainShell, main
from launchpy.config import config_objects, headers
from launchpy.connector import AdobeRequest


class ProxyTestCase(unittest.TestCase):
    credentials = {
        "org_id": "test@AdobeOrg",
        "client_id": "client",
        "secret": "secret",
        "scopes": "scope",
    }
    proxy = "http://proxy.example:8080"

    def setUp(self):
        for target in (config_objects, headers):
            patcher = patch.dict(target, {}, clear=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def config_file(self, data):
        path = Path(self.directory.name) / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)


class ProxyConfigTests(ProxyTestCase):
    def test_configure_stores_proxy_and_resets_it_on_reconfiguration(self):
        launchpy.configure(**self.credentials, proxy=self.proxy)
        self.assertEqual(config_objects["default"]["proxy"], self.proxy)
        launchpy.configure(**self.credentials)
        self.assertIsNone(config_objects["default"]["proxy"])

    def test_invalid_proxy_configurations_are_rejected(self):
        for proxy in ([], {}, {"https": self.proxy}, 1, True, "", " "):
            with self.subTest(proxy=proxy):
                with self.assertRaises(ValueError):
                    launchpy.configure(**self.credentials, proxy=proxy)
        self.assertEqual(config_objects, {})

    def test_import_single_config_with_legacy_api_key(self):
        config = dict(self.credentials, proxy=self.proxy)
        config["api_key"] = config.pop("client_id")
        launchpy.importConfigFile(self.config_file(config))
        self.assertEqual(config_objects["default"]["proxy"], self.proxy)
        self.assertEqual(config_objects["default"]["client_id"], "client")

    def test_import_multi_org_keeps_proxy_independent(self):
        configs = [
            dict(self.credentials, org_name="first", proxy=self.proxy),
            dict(self.credentials, org_name="second", proxy="http://other:8080"),
            dict(self.credentials, org_name="third"),
        ]
        launchpy.importConfigFile(self.config_file(configs))
        self.assertEqual(config_objects["first"]["proxy"], self.proxy)
        self.assertEqual(config_objects["second"]["proxy"], configs[1]["proxy"])
        self.assertIsNone(config_objects["third"]["proxy"])

    def test_import_proxy_override_applies_to_single_and_multi_org(self):
        override = "http://override:8080"
        for multi in (False, True):
            with self.subTest(multi=multi):
                config = dict(self.credentials, org_name="first", proxy=self.proxy)
                data = [config] if multi else config
                launchpy.importConfigFile(self.config_file(data), proxy=override)
                self.assertEqual(config_objects["first" if multi else "default"]["proxy"],
                                 override)

    def test_import_without_proxy_preserves_old_configuration_format(self):
        launchpy.importConfigFile(self.config_file(self.credentials))
        self.assertIsNone(config_objects["default"]["proxy"])


class ConnectorProxyTests(ProxyTestCase):
    def make_connector(self, proxy=None):
        launchpy.configure(**self.credentials, proxy=proxy)
        return AdobeRequest()

    @patch("launchpy.connector.requests.post")
    def test_oauth_initial_request_and_refresh_use_proxy(self, post):
        post.return_value.json.return_value = {"access_token": "token", "expires_in": 3600}
        connector = self.make_connector(self.proxy)
        connector.config["default"]["date_limit"] = 0
        connector._checkingDate()
        self.assertEqual(post.call_count, 2)
        for call in post.call_args_list:
            self.assertEqual(call.kwargs["proxies"], {"http": self.proxy, "https": self.proxy})
        config_objects["default"]["proxy"] = "http://changed:8080"
        self.assertEqual(connector.proxy, self.proxy)

    @patch("launchpy.connector.requests.post")
    def test_legacy_oauth_configuration_does_not_add_proxy_kwargs(self, post):
        post.return_value.json.return_value = {"access_token": "token", "expires_in": 3600}
        connector = self.make_connector()
        connector.config["default"]["date_limit"] = 0
        connector._checkingDate()
        for call in post.call_args_list:
            self.assertNotIn("proxies", call.kwargs)

    def test_all_api_methods_preserve_proxy_when_retrying(self):
        with patch("launchpy.connector.requests.post") as post:
            post.return_value.json.return_value = {"access_token": "token", "expires_in": 3600}
            connector = self.make_connector(self.proxy)
        for method in ("get", "post", "put", "patch", "delete"):
            with self.subTest(method=method):
                limited = Mock(status_code=429, headers={"Retry-After": "0"})
                success = Mock(status_code=200)
                success.json.return_value = {"data": []}
                with patch(f"launchpy.connector.requests.{method}",
                           side_effect=[limited, success]) as request:
                    with patch("launchpy.connector.time.sleep"):
                        getattr(connector, method + "Data")("https://example.invalid")
                self.assertEqual(request.call_count, 2)
                for call in request.call_args_list:
                    self.assertEqual(call.kwargs["proxies"],
                                     {"http": self.proxy, "https": self.proxy})

    def test_organizations_use_their_own_proxy_for_authentication(self):
        launchpy.configure(**self.credentials, org_name="first", proxy=self.proxy)
        launchpy.configure(**self.credentials, org_name="second",
                           proxy="http://other:8080")
        with patch("launchpy.connector.requests.post") as post:
            post.return_value.json.return_value = {"access_token": "token", "expires_in": 3600}
            first = AdobeRequest(org_name="first")
            second = AdobeRequest(org_name="second")
        self.assertEqual(post.call_args_list[0].kwargs["proxies"],
                         {"http": first.proxy, "https": first.proxy})
        self.assertEqual(post.call_args_list[1].kwargs["proxies"],
                         {"http": second.proxy, "https": second.proxy})
        self.assertNotEqual(first.proxy, second.proxy)


class CLIProxyTests(ProxyTestCase):
    def setUp(self):
        super().setUp()
        for target in ("launchpy.cli.__main__.console", "launchpy.Admin"):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_startup_direct_credentials_and_proxy(self):
        shell = MainShell(**self.credentials, proxy=self.proxy)
        self.assertEqual(config_objects["default"]["proxy"], self.proxy)
        self.assertEqual(shell.org_name, "default")

    def test_interactive_direct_credentials_and_proxy(self):
        shell = MainShell()
        shell.do_config("--client_id client --secret secret --org_id org --scopes scope "
                        f"--proxy {self.proxy}")
        self.assertEqual(config_objects["default"]["proxy"], self.proxy)
        self.assertIsNotNone(shell.cid)

    def test_single_file_proxy_and_cli_override_at_startup_and_interactively(self):
        path = self.config_file(dict(self.credentials, proxy=self.proxy))
        for interactive in (False, True):
            for override in (False, True):
                with self.subTest(interactive=interactive, override=override):
                    expected = "http://override:8080" if override else self.proxy
                    if interactive:
                        shell = MainShell()
                        extra = " --proxy http://override:8080" if override else ""
                        shell.do_config(f'--config_file "{path}"{extra}')
                    else:
                        options = {"proxy": "http://override:8080"} if override else {}
                        shell = MainShell(config_file=path, **options)
                    self.assertEqual(config_objects["default"]["proxy"], expected)
                    self.assertIsNotNone(shell.cid)

    def test_multi_org_proxy_survives_switching_and_reconfiguration(self):
        configs = [
            dict(self.credentials, org_name="first", proxy=self.proxy),
            dict(self.credentials, org_name="second", proxy="http://other:8080"),
        ]
        path = self.config_file(configs)
        for interactive in (False, True):
            with self.subTest(interactive=interactive):
                shell = MainShell() if interactive else MainShell(config_file=path)
                if interactive:
                    shell.do_config(f'--config_file "{path}"')
                for org in ("second", "first", "second"):
                    shell.do_change_org(org)
                    expected = configs[0 if org == "first" else 1]["proxy"]
                    self.assertEqual(config_objects[org]["proxy"], expected)
                    self.assertEqual(shell.org_name, org)
                shell.do_config("--client_id client --secret secret --org_id org "
                                "--scopes scope --proxy http://new:8080")
                self.assertEqual(config_objects["default"]["proxy"], "http://new:8080")

    def test_startup_parser_and_default_org_with_proxy(self):
        with patch("sys.argv", ["launchpy", "--client_id", "client", "--secret", "secret",
                                "--org_id", "org", "--scopes", "scope",
                                "--proxy", "http://proxy:8080"]):
            with patch.object(MainShell, "cmdloop"):
                main()
        self.assertEqual(config_objects["default"]["proxy"], "http://proxy:8080")

    def test_multi_org_overrides_apply_to_every_org_at_startup_and_interactively(self):
        configs = [
            dict(self.credentials, org_name="first", proxy=self.proxy),
            dict(self.credentials, org_name="second"),
        ]
        path = self.config_file(configs)
        for interactive in (False, True):
            with self.subTest(interactive=interactive):
                if interactive:
                    shell = MainShell()
                    shell.do_config(f'--config_file "{path}" --org_name second '
                                    '--proxy http://common:8080')
                else:
                    shell = MainShell(config_file=path, org_name="second",
                                      proxy="http://common:8080")
                for org in ("first", "second"):
                    self.assertEqual(config_objects[org]["proxy"], "http://common:8080")
                self.assertEqual(shell.org_name, "second")

    def test_invalid_file_proxy_is_reported_before_connecting(self):
        path = self.config_file(dict(self.credentials, proxy={"https": self.proxy}))
        shell = MainShell()
        with patch("launchpy.Admin") as admin:
            with patch("launchpy.cli.__main__.console") as console:
                shell.do_config(f'--config_file "{path}"')
        admin.assert_not_called()
        self.assertIn("`proxy` must be", console.print.call_args.args[0])

    def test_empty_proxy_url_is_reported_before_connecting(self):
        shell = MainShell()
        with patch("launchpy.Admin") as admin:
            with patch("launchpy.cli.__main__.console") as console:
                shell.do_config('--client_id client --secret secret --org_id org '
                                '--scopes scope --proxy ""')
        admin.assert_not_called()
        self.assertIn("`proxy` must be", console.print.call_args.args[0])


class LocalProxyTests(ProxyTestCase):
    def test_requests_and_httpx_route_through_configured_proxy(self):
        received = []

        class ProxyHandler(BaseHTTPRequestHandler):
            def respond(self):
                received.append((self.command, self.path))
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                payload = (
                    {"access_token": "test-token", "expires_in": 3600}
                    if self.path.endswith("/token") else {"data": []}
                )
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = respond

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), ProxyHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        proxy = f"http://127.0.0.1:{server.server_port}"
        launchpy.configure(**self.credentials, proxy=proxy)
        config_objects["default"]["oauthTokenEndpointV2"] = "http://example.invalid/token"
        connector = AdobeRequest()
        for method in ("get", "post", "put", "patch", "delete"):
            result = getattr(connector, method + "Data")("http://example.invalid/api")
            self.assertEqual(result, 200 if method == "delete" else {"data": []})
        connector.config["default"]["date_limit"] = 0
        connector._checkingDate()
        rule = {
            "attributes": {"name": "test-rule"},
            "relationships": {
                "rule_components": {"links": {"related": "http://example.invalid/components"}},
            },
        }
        asyncio.run(launchpy.process_all_rules(
            [rule], self.directory.name, {}, connector.proxy))
        self.assertEqual(received, [
            ("POST", "http://example.invalid/token"),
            ("GET", "http://example.invalid/api"),
            ("POST", "http://example.invalid/api"),
            ("PUT", "http://example.invalid/api"),
            ("PATCH", "http://example.invalid/api"),
            ("DELETE", "http://example.invalid/api"),
            ("POST", "http://example.invalid/token"),
            ("GET", "http://example.invalid/components"),
        ])


class AsyncProxyTests(unittest.TestCase):
    def test_async_rule_downloads_use_single_proxy(self):
        proxy = "http://proxy.example:8080"
        with patch("launchpy.httpx.AsyncClient") as client_class:
            with patch("launchpy.__extractRuleComponents__", new_callable=AsyncMock) as extract:
                rules = [{"id": "rule1"}, {"id": "rule2"}]
                asyncio.run(launchpy.process_all_rules(rules, "folder", {}, proxy))
        self.assertEqual(client_class.call_args.kwargs["proxy"], proxy)
        self.assertNotIn("mounts", client_class.call_args.kwargs)
        self.assertEqual(extract.await_count, 2)

    def test_no_proxy_keeps_default_async_client_settings(self):
        with patch("launchpy.httpx.AsyncClient") as client_class:
            asyncio.run(launchpy.process_all_rules([], "folder", {}))
        self.assertNotIn("proxy", client_class.call_args.kwargs)

    def test_property_export_passes_connector_proxy(self):
        property = Mock(spec=launchpy.Property)
        property.name = "test"
        property.header = {}
        property.connector = Mock(proxy="http://proxy.example:8080")
        property.getRules.return_value = []
        property.getDataElements.return_value = []
        property.getExtensions.return_value = []
        with tempfile.TemporaryDirectory() as folder:
            with patch("launchpy.process_all_rules", new_callable=AsyncMock) as process:
                launchpy.extractProperty(property, folder=folder)
        process.assert_awaited_once_with([], folder, {}, property.connector.proxy)


if __name__ == "__main__":
    unittest.main()
