import pytest
from pydantic import ValidationError

from cli.functions.engines.enums import ArgoMethodEnum
from cli.functions.engines.enums import MiddlewareTypeEnum
from cli.functions.engines.enums import TargetTypeEnum
from cli.functions.engines.models import ArgoAdapterBaseModel
from cli.functions.engines.models import \
    ArgoAdapterMiddlewareAllowedMethodsBaseModel
from cli.functions.engines.models import ArgoAdapterMiddlewareCorsBaseModel
from cli.functions.engines.models import ArgoAdapterTargetBaseModel


class TestArgoAdapterMiddlewareAllowedMethodsBaseModel:
    def test_valid_argo_adapter_middleware_allowed_methods(self):
        # Action
        model = ArgoAdapterMiddlewareAllowedMethodsBaseModel()
        # Assert
        assert model.type == MiddlewareTypeEnum.ALLOWED_METHODS
        assert model.methods == [ArgoMethodEnum.GET, ArgoMethodEnum.POST]

    def test_invalid_method_in_argo_adapter_middleware_allowed_methods(self):
        # Action
        with pytest.raises(ValidationError) as exc_info:
            ArgoAdapterMiddlewareAllowedMethodsBaseModel(methods=["INVALID_METHOD"])
        # Assert
        assert "Input should be 'GET', 'POST' or 'OPTIONS'" in str(exc_info.value)


class TestArgoAdapterMiddlewareCorsBaseModel:
    def test_valid_argo_adapter_middleware_cors(self):
        # Action
        model = ArgoAdapterMiddlewareCorsBaseModel()
        # Assert
        assert model.type == MiddlewareTypeEnum.CORS
        assert model.allow_origins == ["*"]
        assert model.allow_methods == [
            ArgoMethodEnum.GET,
            ArgoMethodEnum.POST,
            ArgoMethodEnum.OPTIONS,
        ]
        assert model.allow_headers == [
            "Accept",
            "Accept-Version",
            "Content-Length",
            "Content-MD5",
            "Content-Type",
            "Date",
            "X-Auth-Token",
        ]
        assert model.allow_credentials is True
        assert model.expose_headers == ["X-Auth-Token"]

    def test_invalid_allow_methods_in_argo_adapter_middleware_cors(self):
        # Action
        with pytest.raises(ValidationError) as exc_info:
            ArgoAdapterMiddlewareCorsBaseModel(allow_methods=["INVALID_METHOD"])
        # Assert
        assert "Input should be 'GET', 'POST' or 'OPTIONS'" in str(exc_info.value)


class TestArgoAdapterTargetBaseModel:
    def test_valid_argo_adapter_target(self):
        # Action
        model = ArgoAdapterTargetBaseModel(
            type=TargetTypeEnum.RIE_FUNCTION,
            url="https://example.com",
        )
        # Assert
        assert model.type == TargetTypeEnum.RIE_FUNCTION
        assert model.url == "https://example.com"
        assert model.auth_token == ""

    def test_invalid_target_type(self):
        # Action
        with pytest.raises(ValidationError) as exc_info:
            ArgoAdapterTargetBaseModel(type="INVALID_TYPE", url="https://example.com")
        # Assert
        assert "Input should be 'rie_function' or 'rie_function_raw'" in str(
            exc_info.value
        )


class TestArgoAdapterBaseModel:
    def test_valid_argo_adapter(self):
        # Action
        model = ArgoAdapterBaseModel(
            label="Test Adapter",
            path="/test/path",
            is_strict=True,
            middlewares=[
                ArgoAdapterMiddlewareAllowedMethodsBaseModel(),
                ArgoAdapterMiddlewareCorsBaseModel(),
            ],
            target=ArgoAdapterTargetBaseModel(
                type=TargetTypeEnum.RIE_FUNCTION, url="https://example.com"
            ),
        )
        # Assert
        assert model.label == "Test Adapter"
        assert model.path == "/test/path"
        assert model.is_strict is True
        assert len(model.middlewares) == 2
        assert model.target.type == TargetTypeEnum.RIE_FUNCTION

    def test_invalid_middleware_in_argo_adapter(self):
        # Action
        with pytest.raises(ValidationError) as exc_info:
            ArgoAdapterBaseModel(
                label="Test Adapter",
                path="/test/path",
                middlewares=["INVALID_MIDDLEWARE"],
                target=ArgoAdapterTargetBaseModel(
                    type=TargetTypeEnum.RIE_FUNCTION, url="https://example.com"
                ),
            )
        # Assert
        assert (
            "Input should be a valid dictionary or instance of ArgoAdapterMiddleware"
            in str(exc_info.value)
        )
