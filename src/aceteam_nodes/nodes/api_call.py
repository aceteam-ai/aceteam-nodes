"""API Call node - HTTP requests with Jinja templating."""

import json
import logging
from collections.abc import Sequence
from functools import cached_property
from typing import Any, Literal

import httpx
from overrides import override
from pydantic import Field
from workflow_engine import (
    BooleanValue,
    Context,
    Data,
    File,
    FloatValue,
    IntegerValue,
    JSONValue,
    Params,
    SequenceValue,
    StringMapValue,
    StringValue,
    UserException,
    Value,
)
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo
from workflow_engine.files import JSONFileValue, JSONLinesFileValue, TextFileValue

from ..field import FieldInfo, FieldInfoValue, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo
from ..utils import format_jinja

logger = logging.getLogger(__name__)


class APICallParams(Params):
    url: StringValue
    method: StringValue = Field(default_factory=lambda: StringValue("GET"))
    headers: StringMapValue[StringValue] = Field(
        default_factory=lambda: StringMapValue[StringValue]({})
    )
    body_template: StringValue = Field(default_factory=lambda: StringValue(""))
    parameters: SequenceValue[FieldInfoValue] = Field(
        default_factory=lambda: SequenceValue[FieldInfoValue]([])
    )
    timeout: FloatValue = Field(default_factory=lambda: FloatValue(30.0))
    output_file: BooleanValue = Field(default_factory=lambda: BooleanValue(False))


class APICallOutput(Data):
    status_code: IntegerValue
    response: JSONValue
    headers: StringMapValue[StringValue]


class APICallTextFileOutput(Data):
    status_code: IntegerValue
    response: TextFileValue
    headers: StringMapValue[StringValue]


class APICallJSONFileOutput(Data):
    status_code: IntegerValue
    response: JSONFileValue
    headers: StringMapValue[StringValue]


class APICallNode(
    AceTeamNode[
        Data,
        APICallOutput | APICallTextFileOutput | APICallJSONFileOutput,
        APICallParams,
    ]
):
    """Node that makes HTTP API calls with Jinja templating for URL and request body."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="APICall",
        display_name="API Call",
        description="Makes HTTP API calls with Jinja templating for URL and request body.",
        version="0.4.0",
        parameter_type=APICallParams,
    )

    type: Literal["APICall"] = "APICall"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="APICall",
            display_name="API Call",
            description="Makes HTTP API calls with Jinja templating for URL and request body.",
            params=(
                FieldInfo(
                    name="url",
                    display_name="URL Template",
                    description="The API endpoint URL.",
                    type=FieldType.SHORT_TEXT,
                ),
                FieldInfo(
                    name="method",
                    display_name="HTTP Method",
                    description="The HTTP method to use.",
                    type=FieldType.SHORT_TEXT,
                    default="GET",
                ),
                FieldInfo(
                    name="headers",
                    display_name="Headers",
                    description="HTTP headers to include in the request.",
                    type=FieldType.JSON,
                    default={},
                ),
                FieldInfo(
                    name="body_template",
                    display_name="Request Body Template",
                    description="The request body template.",
                    type=FieldType.LONG_TEXT,
                    default="",
                ),
                FieldInfo(
                    name="timeout",
                    display_name="Timeout (seconds)",
                    description="Request timeout in seconds.",
                    type=FieldType.NUMBER,
                    default=30.0,
                    min=1.0,
                    max=300.0,
                    step=1.0,
                ),
                FieldInfo(
                    name="output_file",
                    display_name="Output to File",
                    description="Whether to save the response to a file.",
                    type=FieldType.BOOLEAN,
                    default=False,
                ),
                FieldInfo(
                    name="parameters",
                    display_name="Template Parameters",
                    description="Parameters used in URL and body templates.",
                    type=FieldType.FIELD_LIST,
                    default=(),
                ),
            ),
        )

    @cached_property
    def supports_json_output(self) -> bool:
        content_type = self.params.headers.get("Accept")
        return content_type is not None and "application/json" in content_type

    @cached_property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        return tuple(field.root for field in self.params.parameters)

    @cached_property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        if self.params.output_file:
            return (
                FieldInfo(
                    name="status_code",
                    display_name="Status Code",
                    description="HTTP response status code.",
                    type=FieldType.NUMBER,
                ),
                FieldInfo(
                    name="response",
                    display_name="Response File",
                    description="File containing the API response.",
                    type=FieldType.FILE_JSON
                    if self.supports_json_output
                    else FieldType.FILE_TEXT,
                ),
                FieldInfo(
                    name="headers",
                    display_name="Response Headers",
                    description="HTTP response headers.",
                    type=FieldType.JSON,
                ),
            )
        else:
            return (
                FieldInfo(
                    name="status_code",
                    display_name="Status Code",
                    description="HTTP response status code.",
                    type=FieldType.NUMBER,
                ),
                FieldInfo(
                    name="response",
                    display_name="Response",
                    description="The API response data.",
                    type=FieldType.JSON,
                ),
                FieldInfo(
                    name="headers",
                    display_name="Response Headers",
                    description="HTTP response headers.",
                    type=FieldType.JSON,
                ),
            )

    @property
    def output_type(self):
        if self.params.output_file:
            if self.supports_json_output:
                return APICallJSONFileOutput
            else:
                return APICallTextFileOutput
        else:
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
    async def run(
        self, context: Context, input: Data
    ) -> APICallOutput | APICallTextFileOutput | APICallJSONFileOutput:
        # Prepare template parameters
        parameters: dict[str, Any] = {}
        if len(self.params.parameters) > 0:
            for field in self.params.parameters:
                if hasattr(input, field.name):
                    parameters[field.name] = await self._expand_parameter_value(
                        context, getattr(input, field.name)
                    )
                elif field.default is not None:
                    parameters[field.name] = field.default
                else:
                    raise UserException(
                        f"Parameter {field.name} is not set and has no default value."
                    )

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
            raise UserException(
                f"Request timed out after {self.params.timeout} seconds."
            ) from e
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

        # Handle file output
        if self.params.output_file:
            if self._is_json_response(response) and isinstance(response_data, (dict, list)):
                response_file = JSONFileValue(File(path="api_response.json"))
                response_file = await response_file.write_data(context, response_data)
                return APICallJSONFileOutput(
                    status_code=status_code, response=response_file, headers=response_headers
                )
            else:
                response_file = TextFileValue(File(path="api_response.txt"))
                response_text = (
                    response_data if isinstance(response_data, str) else str(response_data)
                )
                response_file = await response_file.write_text(context, response_text)
                return APICallTextFileOutput(
                    status_code=status_code, response=response_file, headers=response_headers
                )
        else:
            return APICallOutput(
                status_code=status_code, response=response_data, headers=response_headers
            )


__all__ = [
    "APICallNode",
    "APICallParams",
]
