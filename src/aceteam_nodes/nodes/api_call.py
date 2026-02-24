"""API Call node - HTTP requests with Jinja templating."""

import json
import logging
from functools import cached_property
from typing import Any, Literal

import httpx
from overrides import override
from pydantic import Field
from workflow_engine import (
    Context,
    Data,
    FieldSchemaMappingValue,
    FloatValue,
    IntegerValue,
    JSONValue,
    Node,
    NodeTypeInfo,
    Params,
    StringMapValue,
    StringValue,
    UserException,
    Value,
)
from workflow_engine.files import JSONFileValue, JSONLinesFileValue, TextFileValue

from ..utils import format_jinja

logger = logging.getLogger(__name__)


class APICallParams(Params):
    url: StringValue = Field(
        title="URL",
        description="The API endpoint URL.",
    )
    method: StringValue = Field(
        title="Method",
        description="The HTTP method to use.",
        default=StringValue("GET"),
    )
    headers: StringMapValue[StringValue] = Field(
        title="Headers",
        description="HTTP headers to include in the request.",
        default=StringMapValue({}),
    )
    body_template: StringValue = Field(
        title="Body Template",
        description="The request body template.",
        default=StringValue(""),
    )
    parameters: FieldSchemaMappingValue = Field(
        title="Parameters",
        description="Parameters used in URL and body templates.",
        default=FieldSchemaMappingValue({}),
    )
    timeout: FloatValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=FloatValue(30.0),
    )


class APICallOutput(Data):
    status_code: IntegerValue = Field(
        title="Status Code",
        description="The HTTP status code of the response.",
    )
    response: JSONValue = Field(
        title="Response",
        description="The response data.",
    )
    headers: StringMapValue[StringValue] = Field(
        title="Headers",
        description="HTTP headers of the response.",
    )


class APICallNode(
    Node[
        Data,
        APICallOutput,
        APICallParams,
    ]
):
    """Node that makes HTTP API calls with Jinja templating for URL and request body."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="APICall",
        display_name="API Call",
        description="Makes HTTP API calls with Jinja templating for URL and request body.",
        version="0.4.0",
        parameter_type=APICallParams,
    )

    type: Literal["APICall"] = "APICall"

    @cached_property
    def supports_json_output(self) -> bool:
        content_type = self.params.headers.get("Accept")
        return content_type is not None and "application/json" in content_type

    @cached_property
    def input_schema(self):
        return self.params.parameters.to_data_schema("APICallInput")

    @cached_property
    def input_type(self):
        return self.input_schema.build_data_cls()

    @cached_property
    def output_type(self):
        return APICallOutput

    async def _expand_parameter_value(self, context: Context, value: Value) -> Any:
        """Expand data files into their content for templating."""
        assert isinstance(value, Value)
        if isinstance(value, JSONFileValue):
            try:
                return await value.read_data(context)
            except Exception as e:
                raise UserException(f"Failed to read JSON file '{value.path}'.") from e
        elif isinstance(value, JSONLinesFileValue):
            try:
                return await value.read_data(context)
            except Exception as e:
                raise UserException(f"Failed to read JSON lines file '{value.path}'.") from e
        elif isinstance(value, TextFileValue):
            try:
                return await value.read_text(context)
            except Exception as e:
                raise UserException(f"Failed to read text file '{value.path}'.") from e
        return value.root

    def _is_json_response(self, response: httpx.Response) -> bool:
        content_type = response.headers.get("content-type", "")
        assert isinstance(content_type, str)
        content_type = content_type.lower()
        return "application/json" in content_type or "text/json" in content_type

    def _parse_response_data(self, response: httpx.Response) -> Any:
        try:
            if self._is_json_response(response):
                return response.json()
            else:
                return response.text
        except json.JSONDecodeError:
            try:
                return response.text
            except Exception:
                return str(response.content)
        except Exception:
            return str(response.content)

    @override
    async def run(self, context: Context, input: Data) -> APICallOutput:
        # Prepare template parameters
        parameters: dict[str, Any] = {}
        if len(self.params.parameters) > 0:
            for key, value in self.params.parameters.items():
                parameters[key] = await self._expand_parameter_value(context, value)

        # Format URL with Jinja templating
        try:
            url_template = self.params.url.root
            url = format_jinja(url_template, parameters)
        except Exception as e:
            raise UserException(f"Failed to format URL template: {e}") from e

        # Format request body with Jinja templating
        request_body = None
        body_template = self.params.body_template.root
        if body_template.strip():
            try:
                body_text = format_jinja(body_template, parameters)
                if body_text.strip().startswith(("{", "[")):
                    try:
                        request_body = json.loads(body_text)
                    except json.JSONDecodeError:
                        request_body = body_text
                else:
                    request_body = body_text
            except Exception as e:
                raise UserException(f"Failed to format request body template: {e}") from e

        # Prepare headers
        headers = {k: v.root for k, v in self.params.headers.items()}

        if request_body is not None and isinstance(request_body, (dict, list)):
            if "content-type" not in {k.lower() for k in headers.keys()}:
                headers["Content-Type"] = "application/json"

        logger.info(f"Making {self.params.method} request to: {url}")

        # Make the HTTP request
        try:
            timeout = self.params.timeout.root
            method = self.params.method.root
            async with httpx.AsyncClient(timeout=timeout) as client:
                if isinstance(request_body, (dict, list)):
                    response = await client.request(
                        method=method, url=url, headers=headers, json=request_body
                    )
                elif request_body is not None:
                    response = await client.request(
                        method=method, url=url, headers=headers, content=request_body
                    )
                else:
                    response = await client.request(method=method, url=url, headers=headers)
        except httpx.TimeoutException as e:
            raise UserException(f"Request timed out after {self.params.timeout} seconds.") from e
        except httpx.RequestError as e:
            raise UserException(f"Request failed: {e}") from e
        except Exception as e:
            raise UserException(f"Unexpected error during API call: {e}") from e

        # Parse response
        status_code = IntegerValue(response.status_code)
        response_data = self._parse_response_data(response)
        response_headers = StringMapValue[StringValue](
            {k: StringValue(v) for k, v in response.headers.items()}
        )

        return APICallOutput(
            status_code=status_code,
            response=response_data,
            headers=response_headers,
        )


__all__ = [
    "APICallNode",
    "APICallParams",
]
