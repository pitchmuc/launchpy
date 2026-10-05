# Launchpy

Python wrapper for the Adobe Launch API.\
This module is named launchpy.

Current version: **0.5.2**. This version fixes GET retries and adds automatic
HTTP 429 retries across all five connector methods. See the
[0.5.2 release notes](./docs/releases.md#052) for details.

## Installation

You can install the module by realising the following pip command:\
`pip install launchpy`

You can access the version of the module that you run via the following attribute:\
`launchpy.__version__`

## Content of the module

This module is built around 7 main parts:

- Helping functions [Core Components](./docs/main.md)
- Admin instantiating functions [Admin Class](./docs/admin.md)
- Managing properties [Property Class](./docs/property.md)
- Managing Publishing Cycle [Library Class](./docs/library.md)
- Translator functionationality [Translator Class](./docs/translator.md)
- Synchronizer [Synchronizer Class](./docs/synchronizer.md)
- Command Line Interface [CLI](./docs/cli.md)

## Get Started

A [get started guide](./docs/getstarted.md) has been created to explain the different functionality.
You can find a more detail description functionalities at [datanalyst.info](https://datanalyst.info).

## Main documentation

Most of the documentation has been imported from the datanalyst website [here](./docs/main.md).

## Release information

You can find release information [here](./docs/releases.md).

## HTTP retries

The `AdobeRequest` connector always retries HTTP 429 responses for GET, POST,
PUT, PATCH, and DELETE, even when their body is not JSON or `retry=0`.
Rate-limit retries have no attempt limit and do not consume the configured
`retry` budget. A request can therefore keep waiting while the API remains
rate limited; it can be interrupted normally.

The connector
honors `Retry-After` in seconds or HTTP-date format; absent or invalid values
use exponential backoff starting at 45 seconds and capped at 300 seconds.
The JSON-returning methods also always retry Adobe error code `429050`.

The `retry` setting is reserved for other retryable errors: currently, GET
responses that cannot be decoded as JSON. It specifies the number of
**additional attempts**, with a default of `0`. Set
`property.connector.retry = 3` or pass `retry=3` to a connector method to
override this budget; neither setting limits rate-limit retries.

Successful return values are unchanged: DELETE returns the HTTP status code,
while the other methods return decoded JSON. GET also retries invalid JSON
responses with a 30-second delay. Invalid JSON from write operations and
network exceptions do not trigger retries, to avoid replaying writes that
may already have succeeded. This policy applies to the five connector methods,
not the separate OAuth token request or async property-extraction requests.
