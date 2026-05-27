import structlog
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from accounts.serializers.contracts import ACCOUNTS_ERROR_RESPONSES
from accounts.serializers.onboarding import (
    ActivationStateQuerySerializer,
    ActivationStateResponseSerializer,
)
from accounts.services.onboarding.activation_state import (
    resolve_activation_state_for_request,
)
from tfc.utils.general_methods import GeneralMethods

logger = structlog.get_logger(__name__)


class ActivationStateView(APIView):
    permission_classes = [IsAuthenticated]
    _gm = GeneralMethods()

    @swagger_auto_schema(
        query_serializer=ActivationStateQuerySerializer,
        responses={200: ActivationStateResponseSerializer, **ACCOUNTS_ERROR_RESPONSES},
    )
    def get(self, request):
        try:
            query_keys = set(ActivationStateQuerySerializer().fields)
            query_data = {
                key: value
                for key, value in request.query_params.items()
                if key in query_keys
            }
            query_serializer = ActivationStateQuerySerializer(data=query_data)
            query_serializer.is_valid(raise_exception=True)

            payload = resolve_activation_state_for_request(request)
            return self._gm.success_response(payload)
        except Exception as exc:
            user = getattr(request, "user", None)
            organization = getattr(request, "organization", None)
            workspace = getattr(request, "workspace", None)
            logger.exception(
                "Activation state resolution failed",
                error=str(exc),
                user_id=str(getattr(user, "id", "")),
                organization_id=str(getattr(organization, "id", "")),
                workspace_id=str(getattr(workspace, "id", "")),
            )
            return self._gm.internal_server_error_response(
                "Failed to fetch activation state"
            )
