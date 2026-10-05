import json
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import requests

from launchpy.connector import AdobeRequest


class ConnectorRetryTests(unittest.TestCase):
    methods = ("get", "post", "put", "patch", "delete")
    endpoint = "https://example.invalid/components"

    def setUp(self):
        self.connector = AdobeRequest.__new__(AdobeRequest)
        self.connector.header = {"Authorization": "test"}
        self.connector.retry = 2
        self.connector._checkingDate = Mock()
        sleep_patch = patch("launchpy.connector.time.sleep")
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def response(self, status=200, payload=None, headers=None, body=None):
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers or {})
        response._content = (
            body.encode() if body is not None else json.dumps(payload).encode()
        )
        response.request = requests.Request("GET", self.endpoint).prepare()
        return response

    def call(self, method, **kwargs):
        return getattr(self.connector, method + "Data")(self.endpoint, **kwargs)

    def test_consecutive_429s_retry_all_methods_and_preserve_request(self):
        for method in self.methods:
            with self.subTest(method=method):
                self.sleep.reset_mock()
                self.connector._checkingDate.reset_mock()
                limited = self.response(429, headers={"Retry-After": "2"}, body="not JSON")
                success = self.response(204 if method == "delete" else 200, {"data": []})
                with patch(f"launchpy.connector.requests.{method}",
                           side_effect=[limited, limited, success]) as request:
                    result = self.call(method, params={"page": 1}, data={"value": 1},
                                       headers={"X-Test": "custom"})
                self.assertEqual(result, 204 if method == "delete" else {"data": []})
                self.assertEqual(request.call_count, 3)
                self.assertEqual(self.connector._checkingDate.call_count, 3)
                expected_data = {"value": 1} if method == "get" else '{"value": 1}'
                for call in request.call_args_list:
                    self.assertEqual(call.args, (self.endpoint,))
                    self.assertEqual(call.kwargs, {
                        "headers": {"X-Test": "custom"},
                        "params": {"page": 1},
                        "data": expected_data,
                    })
                self.assertEqual([call.args for call in self.sleep.call_args_list],
                                 [(2.0,), (2.0,)])

    def test_rate_limits_retry_beyond_budget_with_capped_backoff(self):
        for method in self.methods:
            with self.subTest(method=method):
                self.sleep.reset_mock()
                limited = self.response(429)
                success = self.response(204 if method == "delete" else 200, {"data": []})
                with patch(f"launchpy.connector.requests.{method}",
                           side_effect=[limited] * 5 + [success]) as request:
                    self.assertEqual(self.call(method),
                                     204 if method == "delete" else {"data": []})
                self.assertEqual(request.call_count, 6)
                self.assertEqual([call.args for call in self.sleep.call_args_list],
                                 [(45,), (90,), (180,), (300,), (300,)])

    def test_rate_limits_ignore_per_call_retry_override(self):
        for method in self.methods:
            for retries in (0, 1, 3):
                with self.subTest(method=method, retry=retries):
                    self.sleep.reset_mock()
                    success = self.response(204 if method == "delete" else 200, {"data": []})
                    with patch(f"launchpy.connector.requests.{method}",
                               side_effect=[self.response(429)] * 4 + [success]) as request:
                        self.assertEqual(self.call(method, retry=retries),
                                         204 if method == "delete" else {"data": []})
                    self.assertEqual(request.call_count, 5)
                    self.assertEqual(self.sleep.call_count, 4)
                    self.assertEqual(self.connector.retry, 2)

    def test_rate_limits_retry_with_zero_budget(self):
        self.connector.retry = 0
        for method in self.methods:
            with self.subTest(method=method):
                self.sleep.reset_mock()
                success = self.response(204 if method == "delete" else 200, {"data": []})
                with patch(f"launchpy.connector.requests.{method}",
                           side_effect=[self.response(429)] * 3 + [success]) as request:
                    self.assertEqual(self.call(method),
                                     204 if method == "delete" else {"data": []})
                self.assertEqual(request.call_count, 4)
                self.assertEqual(self.sleep.call_count, 3)

    def test_adobe_rate_limit_code(self):
        self.connector.retry = 0
        for method in ("get", "post", "put", "patch"):
            with self.subTest(method=method):
                self.sleep.reset_mock()
                with patch(f"launchpy.connector.requests.{method}", side_effect=[
                    self.response(400, {"error_code": "429050"}),
                    self.response(200, {"data": []}),
                ]) as request:
                    self.assertEqual(self.call(method), {"data": []})
                self.assertEqual(request.call_count, 2)
                self.sleep.assert_called_once_with(45)

    def test_retry_after_http_date(self):
        now = datetime(2026, 10, 5, 10, tzinfo=timezone.utc)
        for offset, expected in ((20, 20.0), (-20, 0.0)):
            with self.subTest(offset=offset):
                response = self.response(429, headers={
                    "Retry-After": format_datetime(now + timedelta(seconds=offset), usegmt=True),
                })
                with patch("launchpy.connector.datetime") as clock:
                    clock.now.return_value = now
                    self.assertEqual(self.connector._retry_delay(response, 0), expected)

    def test_retry_after_zero_invalid_and_missing(self):
        for value, expected in (("0", 0.0), ("invalid", 45), ("-1", 45), (None, 45)):
            with self.subTest(value=value):
                headers = {} if value is None else {"Retry-After": value}
                self.assertEqual(self.connector._retry_delay(self.response(429, headers=headers), 0),
                                 expected)
        self.assertEqual(self.connector._retry_delay(self.response(429), 100), 300)

    def test_successful_return_types_and_empty_requests(self):
        for method in self.methods:
            with self.subTest(method=method):
                response = self.response(204, body="") if method == "delete" else self.response(
                    200, ["one", "two"])
                with patch(f"launchpy.connector.requests.{method}", return_value=response) as request:
                    self.assertEqual(self.call(method), 204 if method == "delete" else ["one", "two"])
                request.assert_called_once_with(self.endpoint, headers=self.connector.header)
        self.sleep.assert_not_called()

    def test_get_json_decode_failure_retries(self):
        with patch("launchpy.connector.requests.get", side_effect=[
            self.response(body="invalid JSON"), self.response(payload={"data": []}),
        ]) as request:
            self.assertEqual(self.call("get"), {"data": []})
        self.assertEqual(request.call_count, 2)
        self.sleep.assert_called_once_with(30)

    def test_rate_limits_neither_consume_nor_reset_other_error_budget(self):
        with patch("launchpy.connector.requests.get", side_effect=[
            self.response(body="invalid JSON"),
            self.response(429),
            self.response(429),
            self.response(body="invalid JSON"),
            self.response(429),
            self.response(body="invalid JSON"),
        ]) as request:
            with self.assertLogs("launchpy.connector", level="WARNING"):
                self.assertEqual(self.call("get"), {"error": "Request Error"})
        self.assertEqual(request.call_count, 6)
        self.assertEqual([call.args for call in self.sleep.call_args_list],
                         [(30,), (45,), (90,), (30,), (180,)])

    def test_per_call_budget_still_limits_other_errors(self):
        for retries in (0, 1, 3):
            with self.subTest(retry=retries):
                self.sleep.reset_mock()
                with patch("launchpy.connector.requests.get",
                           return_value=self.response(body="invalid JSON")) as request:
                    with self.assertLogs("launchpy.connector", level="WARNING"):
                        self.assertEqual(self.call("get", retry=retries),
                                         {"error": "Request Error"})
                self.assertEqual(request.call_count, retries + 1)
                self.assertEqual(self.sleep.call_count, retries)
                self.assertEqual(self.connector.retry, 2)

    def test_rate_limit_wait_can_be_interrupted(self):
        self.sleep.side_effect = KeyboardInterrupt
        with patch("launchpy.connector.requests.get",
                   return_value=self.response(429)) as request:
            with self.assertRaises(KeyboardInterrupt):
                self.call("get")
        request.assert_called_once()

    def test_retries_use_refreshed_default_headers(self):
        def refresh_headers():
            self.connector.header = {"Authorization": str(
                self.connector._checkingDate.call_count)}

        self.connector._checkingDate.side_effect = refresh_headers
        with patch("launchpy.connector.requests.post", side_effect=[
            self.response(429), self.response(payload={"data": []}),
        ]) as request:
            self.assertEqual(self.call("post"), {"data": []})
        self.assertEqual(request.call_args_list[0].kwargs["headers"],
                         {"Authorization": "1"})
        self.assertEqual(request.call_args_list[1].kwargs["headers"],
                         {"Authorization": "2"})

    def test_invalid_json_write_is_not_replayed(self):
        for method in ("post", "put", "patch"):
            with self.subTest(method=method):
                with patch(f"launchpy.connector.requests.{method}",
                           return_value=self.response(body="invalid JSON")) as request:
                    with self.assertLogs("launchpy.connector", level="WARNING"):
                        self.assertEqual(self.call(method), {"error": "Request Error"})
                request.assert_called_once()
        self.sleep.assert_not_called()

    def test_get_json_decode_exhaustion_is_logged(self):
        with patch("launchpy.connector.requests.get",
                   return_value=self.response(body="invalid JSON")) as request:
            with self.assertLogs("launchpy.connector", level="WARNING"):
                self.assertEqual(self.call("get"), {"error": "Request Error"})
        self.assertEqual(request.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_other_http_errors_are_not_retried(self):
        for method in self.methods:
            with self.subTest(method=method):
                payload = {"errors": ["bad request"]}
                with patch(f"launchpy.connector.requests.{method}",
                           return_value=self.response(400, payload)) as request:
                    self.assertEqual(self.call(method), 400 if method == "delete" else payload)
                request.assert_called_once()
        self.sleep.assert_not_called()

    def test_network_errors_propagate_without_replaying_writes(self):
        for method in self.methods:
            with self.subTest(method=method):
                with patch(f"launchpy.connector.requests.{method}",
                           side_effect=requests.ConnectionError("connection failed")) as request:
                    with self.assertRaises(requests.ConnectionError):
                        self.call(method)
                request.assert_called_once()
        self.sleep.assert_not_called()

    def test_invalid_retry_budget_is_rejected(self):
        for value in (-1, 1.5, "2", True):
            with self.subTest(value=value):
                with patch("launchpy.connector.requests.get") as request:
                    with self.assertRaises(ValueError):
                        self.call("get", retry=value)
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
