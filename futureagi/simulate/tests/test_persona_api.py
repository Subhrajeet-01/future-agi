import pytest
from rest_framework import status

from simulate.models import Persona


@pytest.fixture
def source_persona(db, organization, workspace):
    return Persona.no_workspace_objects.create(
        persona_type=Persona.PersonaType.WORKSPACE,
        organization=organization,
        workspace=workspace,
        name="Source Persona",
        description="Reusable source persona",
    )


@pytest.mark.integration
@pytest.mark.api
class TestPersonaDuplicateView:
    def test_duplicate_custom_route_success(self, auth_client, source_persona):
        response = auth_client.post(
            f"/simulate/api/personas/duplicate/{source_persona.id}/",
            {"name": "Workspace Copy"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] is True
        assert data["result"]["name"] == "Workspace Copy"

    def test_duplicate_custom_route_rejects_unknown_body_field(
        self, auth_client, source_persona
    ):
        response = auth_client.post(
            f"/simulate/api/personas/duplicate/{source_persona.id}/",
            {"name": "Workspace Copy", "legacy_extra": "ignore me"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["status"] is False
        assert data["details"]["legacy_extra"] == ["Unknown field."]

    def test_duplicate_viewset_route_success(self, auth_client, source_persona):
        response = auth_client.post(
            f"/simulate/api/personas/{source_persona.id}/duplicate/",
            {"name": "Workspace Copy From ViewSet"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] is True
        assert data["result"]["name"] == "Workspace Copy From ViewSet"

    def test_duplicate_viewset_route_rejects_unknown_body_field(
        self, auth_client, source_persona
    ):
        response = auth_client.post(
            f"/simulate/api/personas/{source_persona.id}/duplicate/",
            {"name": "Workspace Copy From ViewSet", "legacy_extra": "ignore me"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["status"] is False
        assert data["details"]["legacy_extra"] == ["Unknown field."]
