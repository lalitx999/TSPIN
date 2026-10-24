"""Read-only registry bundle validation. No registry writes or clinical decisions."""
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .registry_governance import resolve_registry_bundle


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_registry_bundle(request):
    if not request.user.has_perm('patients.view_governedregistry'):
        return Response({'error': 'Registry view permission is required.'}, status=403)
    if not isinstance(request.data, dict) or set(request.data) != {'selection'}:
        return Response({'error': 'Expected a selection object only.'}, status=400)
    try:
        result = resolve_registry_bundle(request.data['selection'])
    except ValidationError as exc:
        return Response({'error': 'REGISTRY_BUNDLE_BLOCKED', 'details': exc.messages}, status=409)
    return Response(result)
