from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from patients.models import Patient, PatientBiologicalRecord, AuditLog, ClinicalKnowledge, TspiSettings, PatientHistory, Appointment, PdpaConsent, AutomationTask
from patients.permissions import IsClinicalStaffOrOwner
from patients.serializers import (
    PatientSerializer, 
    PatientBiologicalRecordSerializer, 
    AuditLogSerializer, 
    ClinicalKnowledgeSerializer,
    TspiSettingsSerializer,
    PatientHistorySerializer,
    AppointmentSerializer,
    PdpaConsentSerializer,
    AutomationTaskSerializer
)

from rest_framework.pagination import PageNumberPagination

class DynamicPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 10000

    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get('no_pagination') == 'true' or request.query_params.get('page_size') == 'no':
            return None
        return super().paginate_queryset(queryset, request, view)


class PatientViewSet(viewsets.ModelViewSet):
    pagination_class = DynamicPageNumberPagination
    serializer_class = PatientSerializer
    permission_classes = [IsClinicalStaffOrOwner]

    def get_queryset(self):
        user = self.request.user
        if Patient.objects.count() == 0:
            try:
                from django.core.management import call_command
                call_command('import_patients_pg')
            except Exception as import_err:
                print("⚠️ Auto import patients error:", import_err)

        if user.is_staff or user.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists():
            return Patient.objects.all()
        return Patient.objects.filter(id_card=user.username)

    @action(detail=False, methods=['get'], url_path='list-lightweight')
    def list_lightweight(self, request):
        """
        Fast optimized endpoint to list minimal patient data (id, fname, lname, hn, gender, birth_date) for dropdowns and selectors.
        Prevents N+1 database queries of detailed nested structures.
        """
        patients = self.get_queryset().only('id', 'first_name', 'last_name', 'hn', 'gender', 'birth_date')
        data = [{
            'id': p.id,
            'fname': p.first_name,
            'lname': p.last_name,
            'hn': p.hn,
            'gender': 'male' if p.gender == 'M' else 'female' if p.gender == 'F' else 'other' if p.gender == 'O' else None,
            'age': p.age
        } for p in patients]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='all-lab-results')
    def all_lab_results(self, request):
        """
        Fast optimized database lookup to compile EMR lab report entries across all patients.
        Avoids client-side iteration and reduces payload size.
        """
        patients = self.get_queryset().filter(extra_data__has_key='lab_results')
        all_results = []
        for p in patients:
            lab_results = p.extra_data.get('lab_results', [])
            if isinstance(lab_results, list):
                for lr in lab_results:
                    lr['patientId'] = p.id
                    lr['patientName'] = f"{p.first_name} {p.last_name}".strip()
                    lr['patientHn'] = p.hn
                    all_results.append(lr)
        return Response(all_results)

    def perform_update(self, serializer):
        instance = serializer.save()
        request_data = self.request.data

        # Intercept and log EMR Lab result updates for patient trend charts
        if 'labs' in request_data:
            labs_data = request_data['labs']
            if isinstance(labs_data, dict):
                fbs_v = labs_data.get('FBS') or labs_data.get('fbs')
                hba1c_v = labs_data.get('HbA1c') or labs_data.get('hba1c')
                ldl_v = labs_data.get('LDL') or labs_data.get('ldl')
                crp_v = labs_data.get('CRP') or labs_data.get('crp')
                
                if any(v is not None for v in [fbs_v, hba1c_v, ldl_v, crp_v]):
                    from patients.models import PatientHistory
                    PatientHistory.objects.create(
                        patient=instance,
                        type="Lab Result",
                        title="บันทึกผลแล็บทางการแพทย์ (แพทย์)",
                        content=f"ผลแล็บได้รับการอัปเดตเข้าระบบ EMR:\n- น้ำตาลในเลือด FBS: {fbs_v if fbs_v is not None else '--'} mg/dL\n- น้ำตาลสะสม HbA1c: {hba1c_v if hba1c_v is not None else '--'} %\n- ไขมันเลว LDL: {ldl_v if ldl_v is not None else '--'} mg/dL\n- ดัชนีการอักเสบ CRP: {crp_v if crp_v is not None else '--'} mg/L"
                    )

        if 'axes' in request_data:
            axes_data = request_data['axes']
            if isinstance(axes_data, dict):
                record = PatientBiologicalRecord(patient=instance)
                latest = instance.axes_records.all().order_by('-record_date').first()
                for i in range(1, 40):
                    axis_key = f"AXIS_{i}"
                    axis_payload = axes_data.get(axis_key) or axes_data.get(str(i))
                    score = None
                    if isinstance(axis_payload, dict):
                        score = axis_payload.get('score')
                    elif isinstance(axis_payload, (int, float)):
                        score = axis_payload
                    if score is not None:
                        setattr(record, f"axis_{i}", int(score))
                    elif latest:
                        setattr(record, f"axis_{i}", getattr(latest, f"axis_{i}"))
                    else:
                        setattr(record, f"axis_{i}", None)
                record.save()
                print(f"📈 Synced 39 Axes to PostgreSQL for patient HN: {instance.hn}")

        extra_fields = {}
        model_fields = [f.name for f in instance._meta.get_fields()]
        for key, value in request_data.items():
            if key not in model_fields and key != 'axes':
                extra_fields[key] = value
        if extra_fields:
            if not instance.extra_data:
                instance.extra_data = {}
            instance.extra_data.update(extra_fields)
            instance.save()

    @action(detail=True, methods=['get'], url_path='tspi-analysis')
    def tspi_analysis(self, request, pk=None):
        """Return the immutable ledger selected for this patient; never recompute here."""
        from .permissions import can_review_clinical_reports
        if not can_review_clinical_reports(request.user):
            return Response({'error': 'Clinical analysis review access is required.'}, status=403)
        patient = self.get_object()
        requested_analysis_id = request.query_params.get("analysis_record_id")
        analysis_records = patient.analysis_records
        analysis_record = (
            analysis_records.filter(id=requested_analysis_id).first()
            if requested_analysis_id
            else analysis_records.order_by("-created_at").first()
        )
        if not analysis_record:
            return Response(
                {
                    "error": "ไม่พบ Analysis Record ที่ผ่านการตรวจสอบ กรุณารันการวิเคราะห์ก่อน",
                    "required_action": "RUN_VERIFIED_ANALYSIS",
                },
                status=status.HTTP_409_CONFLICT,
            )

        result = analysis_record.ledger.copy()
        result["patient_id"] = patient.id
        result["patient_name"] = f"{patient.first_name} {patient.last_name}"
        result["analysis_record_id"] = analysis_record.id

        if result.get("analysis_state") == "BLOCKED_DATA_RECONCILIATION":
            return Response(
                {
                    "analysis_record_id": analysis_record.id,
                    "patient_id": patient.id,
                    "analysis_state": "BLOCKED_DATA_RECONCILIATION",
                    "allowed_output": "DATA_RECONCILIATION_REPORT_ONLY",
                    "identity_validation": result.get("identity_validation", {}),
                    "conflict_details": result.get("identity_validation", {}).get("conflict_details", []),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)

    @action(detail=True, methods=['get'], url_path='canonical-evidence')
    def canonical_evidence(self, request, pk=None):
        """Read-only source history for explicitly authorized evidence reviewers."""
        if not request.user.has_perm('patients.view_clinicalevidencerevision'):
            return Response({'error': 'Evidence review permission is required.'}, status=403)
        patient = self.get_object()
        from .canonical_state import canonical_hash
        # Reuse pagination; do not return an unbounded clinical history in one response.
        rows = patient.evidence_revisions.all()
        page = self.paginate_queryset(rows)
        selected = page if page is not None else rows[:100]
        data = []
        for row in selected:
            if canonical_hash(row.payload) != row.payload_hash:
                return Response({'error': 'EVIDENCE_INTEGRITY_FAILURE'}, status=409)
            data.append({'id': str(row.pk), 'payload': row.payload,
                         'payload_hash': row.payload_hash,
                         'created_at': row.created_at.isoformat()})
        if page is not None:
            return self.get_paginated_response(data)
        return Response({'results': data, 'limit': 100})

    @action(detail=True, methods=['get'], url_path='canonical-state')
    def canonical_state(self, request, pk=None):
        """Read a backend-validated snapshot; never accept client unit dictionaries."""
        if not request.user.has_perm('patients.view_clinicalevidencerevision'):
            return Response({'error': 'Evidence review permission is required.'}, status=403)
        patient = self.get_object()
        registry_id = request.query_params.get('registry_id')
        if not registry_id:
            return Response({'error': 'registry_id is required; no implicit version selection.'}, status=400)
        from django.core.exceptions import ValidationError
        from .models import CanonicalUnitRegistry
        from .evidence_service import read_evidence_state
        try:
            state = read_evidence_state(patient, registry_id=registry_id)
        except CanonicalUnitRegistry.DoesNotExist:
            return Response({'error': 'Registry version not found.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'CANONICAL_STATE_BLOCKED', 'details': exc.messages}, status=409)
        return Response(state, status=409 if state['status'] == 'BLOCKED' else 200)

    @action(detail=True, methods=['post'], url_path='analysis-input-preview')
    def analysis_input_preview(self, request, pk=None):
        """Read-only preflight; never create biological scores or analysis records."""
        required = {'unit_registry_id', 'selection'}
        if not isinstance(request.data, dict) or not required <= set(request.data) or (
            set(request.data) - required - {'expected_manifest_hash'}
        ):
            return Response({'error': 'Expected unit_registry_id, selection and optional expected_manifest_hash.'}, status=400)
        for permission in ('patients.view_clinicalevidencerevision', 'patients.view_governedregistry'):
            if not request.user.has_perm(permission):
                return Response({'error': 'Evidence and registry view permissions are required.'}, status=403)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .analysis_inputs import prepare_analysis_inputs
        from .models import CanonicalUnitRegistry
        try:
            preview = prepare_analysis_inputs(patient_id=patient.pk, actor=request.user,
                unit_registry_id=request.data['unit_registry_id'], selection=request.data['selection'],
                expected_manifest_hash=request.data.get('expected_manifest_hash'))
        except CanonicalUnitRegistry.DoesNotExist:
            return Response({'error': 'Unit registry not found.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'ANALYSIS_INPUT_BLOCKED', 'details': exc.messages}, status=409)
        return Response(preview, status=409 if preview['status'] == 'BLOCKED' else 200)

    @action(detail=True, methods=['post'], url_path='safety-preview')
    def safety_preview(self, request, pk=None):
        """Read-only completeness review, not an all-clear or release decision."""
        required = {'unit_registry_id', 'selection', 'policy_id'}
        if not isinstance(request.data, dict) or not required <= set(request.data) or (
            set(request.data) - required - {'expected_manifest_hash'}
        ):
            return Response({'error': 'Invalid safety preview request.'}, status=400)
        for permission in ('patients.view_clinicalevidencerevision', 'patients.view_governedregistry'):
            if not request.user.has_perm(permission):
                return Response({'error': 'Evidence and registry view permissions are required.'}, status=403)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import CanonicalUnitRegistry
        from .safety_service import preview_safety
        try:
            result = preview_safety(patient_id=patient.pk, actor=request.user,
                unit_registry_id=request.data['unit_registry_id'], selection=request.data['selection'],
                policy_id=request.data['policy_id'], expected_manifest_hash=request.data.get('expected_manifest_hash'))
        except CanonicalUnitRegistry.DoesNotExist:
            return Response({'error': 'Unit registry not found.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'SAFETY_PREVIEW_BLOCKED', 'details': exc.messages}, status=409)
        # 200 is successful retrieval of an assessment, not clinical permission.
        return Response(result)

    @action(detail=True, methods=['post'], url_path='safety-assessments')
    def create_safety_assessment(self, request, pk=None):
        """Record a reviewed input snapshot, not a medical approval."""
        if not request.user.has_perm('patients.add_safetyassessment'):
            return Response({'error': 'Safety assessment write permission is required.'}, status=403)
        required = {'unit_registry_id', 'selection', 'policy_id', 'expected_manifest_hash'}
        if not isinstance(request.data, dict) or set(request.data) != required:
            return Response({'error': 'Invalid safety assessment request.'}, status=400)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import CanonicalUnitRegistry
        from .safety_service import record_safety_assessment
        try:
            result = record_safety_assessment(patient_id=patient.pk, actor=request.user, **request.data)
        except CanonicalUnitRegistry.DoesNotExist:
            return Response({'error': 'Unit registry not found.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'SAFETY_ASSESSMENT_BLOCKED', 'details': exc.messages}, status=409)
        return Response(result, status=201)

    @action(detail=True, methods=['get'], url_path='safety-assessments/(?P<assessment_id>[^/.]+)')
    def safety_assessment_history(self, request, pk=None, assessment_id=None):
        if not request.user.has_perm('patients.view_safetyassessment'):
            return Response({'error': 'Safety history permission is required.'}, status=403)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import SafetyAssessment
        from .safety_history import read_safety_assessment
        try:
            history = read_safety_assessment(patient_id=patient.pk, assessment_id=assessment_id, actor=request.user)
        except SafetyAssessment.DoesNotExist:
            return Response({'error': 'Safety assessment not found for this patient.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'SAFETY_HISTORY_BLOCKED', 'details': exc.messages}, status=409)
        return Response(history, status=409 if history['replay']['status'] == 'MISMATCH' else 200)

    @action(detail=False, methods=['get'], url_path='artifact-review-patients')
    def artifact_review_patients(self, request):
        from django.db.models import Q
        from .permissions import can_review_clinical_reports
        if not can_review_clinical_reports(request.user) or not request.user.has_perm('patients.view_agenticartifact'):
            return Response({'error': 'REVIEW_PERMISSION_REQUIRED'}, status=403)
        query = request.query_params.get('q', '').strip()
        if not 2 <= len(query) <= 100:
            return Response({'error': 'Search requires 2 to 100 characters.'}, status=400)
        rows = Patient.objects.filter(agentic_artifacts__isnull=False).filter(
            Q(hn__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).distinct().order_by('pk')[:51]
        rows = list(rows)
        response = Response({'results': [{'id': row.pk, 'hn': row.hn,
            'name': f'{row.first_name} {row.last_name}'.strip()} for row in rows[:50]],
            'truncated': len(rows) > 50})
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['get'], url_path='artifact-review-list')
    def artifact_review_list(self, request, pk=None):
        from uuid import UUID
        from .models import AgenticArtifact
        from .permissions import can_review_clinical_reports
        if not can_review_clinical_reports(request.user) or not request.user.has_perm('patients.view_agenticartifact'):
            return Response({'error': 'REVIEW_PERMISSION_REQUIRED'}, status=403)
        patient = self.get_object()
        rows = AgenticArtifact.objects.filter(patient=patient).order_by('-id')
        cursor = request.query_params.get('before_id')
        if cursor:
            try:
                rows = rows.filter(id__lt=UUID(cursor))
            except (ValueError, TypeError):
                return Response({'error': 'INVALID_ARTIFACT_CURSOR'}, status=400)
        rows = list(rows[:51])
        response = Response({'results': [{'id': str(row.pk), 'kind': row.kind,
            'created_at': row.created_at.isoformat()} for row in rows[:50]],
            'next_before_id': str(rows[49].pk) if len(rows) > 50 else None})
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['post'], url_path='agentic-artifacts')
    def create_agentic_artifact(self, request, pk=None):
        if not request.user.has_perm('patients.add_agenticartifact'):
            return Response({'error': 'Agentic artifact permission is required.'}, status=403)
        common = {'kind', 'unit_registry_id', 'selection', 'expected_manifest_hash'}
        if not isinstance(request.data, dict) or request.data.get('kind') not in ('WORKFLOW', 'EVIDENCE_DRAFT'):
            return Response({'error': 'Invalid artifact kind.'}, status=400)
        required = common | ({'scoring_run_id', 'safety_policy_id'} if request.data['kind'] == 'WORKFLOW' else set())
        if set(request.data) != required:
            return Response({'error': 'Invalid artifact request fields.'}, status=400)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import CanonicalUnitRegistry, ScoringRun
        from .agentic_service import create_evidence_report_drafts, create_workflow_review
        arguments = {key: value for key, value in request.data.items() if key != 'kind'}
        creator = create_workflow_review if request.data['kind'] == 'WORKFLOW' else create_evidence_report_drafts
        try:
            result = creator(patient_id=patient.pk, actor=request.user, **arguments)
        except (CanonicalUnitRegistry.DoesNotExist, ScoringRun.DoesNotExist):
            return Response({'error': 'Required registry/run not found for this request.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'ARTIFACT_CREATION_BLOCKED', 'details': exc.messages}, status=409)
        return Response(result, status=201)

    @action(detail=True, methods=['get'], url_path='agentic-artifacts/(?P<artifact_id>[^/.]+)')
    def agentic_artifact_history(self, request, pk=None, artifact_id=None):
        if not request.user.has_perm('patients.view_agenticartifact'):
            return Response({'error': 'Agentic artifact view permission is required.'}, status=403)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import AgenticArtifact
        from .agentic_service import read_agentic_artifact
        try:
            result = read_agentic_artifact(patient_id=patient.pk, artifact_id=artifact_id, actor=request.user)
        except AgenticArtifact.DoesNotExist:
            return Response({'error': 'Artifact not found for this patient.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'ARTIFACT_HISTORY_BLOCKED', 'details': exc.messages}, status=409)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='agentic-artifacts/(?P<artifact_id>[^/.]+)/release-readiness')
    def agentic_release_readiness(self, request, pk=None, artifact_id=None):
        if not request.user.has_perm('patients.view_agenticartifact'):
            return Response({'error': 'Agentic artifact view permission is required.'}, status=403)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import AgenticArtifact
        from .release_readiness import inspect_release_readiness
        try:
            result = inspect_release_readiness(patient_id=patient.pk, artifact_id=artifact_id, actor=request.user)
        except AgenticArtifact.DoesNotExist:
            return Response({'error': 'Artifact not found for this patient.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'RELEASE_READINESS_BLOCKED', 'details': exc.messages}, status=409)
        response = Response(result)
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['get', 'post'], url_path='agentic-artifacts/(?P<artifact_id>[^/.]+)/reviews')
    def artifact_reviews(self, request, pk=None, artifact_id=None):
        from uuid import UUID
        from django.core.exceptions import PermissionDenied, ValidationError
        from .permissions import can_review_clinical_reports
        from .artifact_review import list_artifact_reviews, record_artifact_review
        from .models import AgenticArtifact
        operation = 'add' if request.method == 'POST' else 'view'
        if not can_review_clinical_reports(request.user) or not all(request.user.has_perm(p) for p in (
                'patients.view_agenticartifact', f'patients.{operation}_artifactreviewevent')):
            return Response({'error': 'REVIEW_PERMISSION_REQUIRED'}, status=403)
        try:
            UUID(artifact_id)
        except (ValueError, TypeError, AttributeError):
            return Response({'error': 'INVALID_ARTIFACT_ID'}, status=400)
        patient = self.get_object()
        args = dict(patient_id=patient.pk, artifact_id=artifact_id, actor=request.user)
        try:
            if request.method == 'POST':
                required = {'expected_artifact_hash', 'decision', 'reason', 'request_id'}
                data = request.data
                if (not isinstance(data, dict) or set(data) != required or
                        any(not isinstance(data[k], str) for k in required) or
                        len(data['expected_artifact_hash']) != 64 or
                        data['decision'] not in {'REVIEWED_NOT_APPROVED', 'REQUEST_CHANGES', 'REJECT'} or
                        not data['reason'].strip() or len(data['reason']) > 4000):
                    return Response({'error': 'INVALID_REVIEW_FIELDS'}, status=400)
                try:
                    UUID(data['request_id'])
                except (ValueError, TypeError, AttributeError):
                    return Response({'error': 'INVALID_REVIEW_REQUEST_ID'}, status=400)
                result = record_artifact_review(**args, **data)
            else:
                cursor = request.query_params.get('before_id')
                if cursor is not None and (not cursor.isascii() or not cursor.isdigit() or
                                           len(cursor) > 18 or int(cursor) < 1):
                    return Response({'error': 'INVALID_REVIEW_CURSOR'}, status=400)
                result = list_artifact_reviews(**args, before_id=int(cursor) if cursor else None)
        except PermissionDenied:
            return Response({'error': 'REVIEW_PERMISSION_REQUIRED'}, status=403)
        except AgenticArtifact.DoesNotExist:
            return Response({'error': 'Artifact not found for this patient.'}, status=404)
        except ValidationError:
            return Response({'error': 'ARTIFACT_REVIEW_BLOCKED'}, status=409)
        response = Response(result, status=201 if request.method == 'POST' and not result.get('replayed') else 200)
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['get'], url_path='scoring-runs/(?P<run_id>[^/.]+)')
    def scoring_run_history(self, request, pk=None, run_id=None):
        """Historical snapshot and deterministic replay, never a new clinical approval."""
        if not request.user.has_perm('patients.view_scoringrun'):
            return Response({'error': 'Scoring history permission is required.'}, status=403)
        patient = self.get_object()
        from django.core.exceptions import ValidationError
        from .models import ScoringRun
        from .scoring_history import read_scoring_run
        try:
            history = read_scoring_run(patient_id=patient.pk, run_id=run_id, actor=request.user)
        except ScoringRun.DoesNotExist:
            return Response({'error': 'Scoring run not found for this patient.'}, status=404)
        except ValidationError as exc:
            return Response({'error': 'SCORING_HISTORY_BLOCKED', 'details': exc.messages}, status=409)
        return Response(history, status=409 if history['replay']['status'] == 'MISMATCH' else 200)

    @action(detail=True, methods=['get'], url_path='analysis-records/(?P<record_id>[^/.]+)')
    def get_analysis_record(self, request, pk=None, record_id=None):
        """
        Fetch one immutable AnalysisRecord ledger by id, so report generation / PDF export
        can render from the exact same analysis instead of recomputing (ans.txt problem #9).
        """
        patient = self.get_object()
        record = patient.analysis_records.filter(id=record_id).first()
        if not record:
            return Response({"error": "Analysis record not found"}, status=404)
        return Response({
            "analysis_record_id": record.id,
            "patient_id": patient.id,
            "created_at": record.created_at.isoformat(),
            "framework_version": record.framework_version,
            "is_valid": record.is_valid,
            "invariant_violations": record.invariant_violations,
            "analysis": record.ledger,
        })

    @action(detail=True, methods=['post'], url_path='calculate-precision-medicine')
    def calculate_precision_medicine(self, request, pk=None):
        import os
        import json
        import urllib.request
        
        patient = self.get_object()
        
        symptoms = request.data.get('symptoms', '')
        history = request.data.get('history', '')
        fbs = request.data.get('fbs', '')
        hba1c = request.data.get('hba1c', '')
        doppler = request.data.get('doppler', '')
        other_labs = request.data.get('otherLabs', '')
        bowel_status = request.data.get('bowelStatus', 'normal')
        
        # P0-1 Identity Validator Gate — check demographics and source
        # ownership before any biological record or AnalysisRecord is created.
        from .tspi_engine import validate_patient_identity
        identity_input = {
            "patient_id": patient.pk,
            "dob": patient.birth_date.isoformat() if patient.birth_date else None,
            "age": getattr(patient, "age", None),
            "gender": getattr(patient, "gender", None),
            "hn": getattr(patient, "hn", None),
            "symptoms": symptoms,
            "history": history,
            "soap_age": request.data.get("soap_age"),
            "soap_gender": request.data.get("soap_gender"),
            "soap_hn": request.data.get("soap_hn"),
            "lab_owner_hn": request.data.get("lab_owner_hn"),
            "lab_source_record_id": request.data.get("lab_source_record_id"),
            "source_document_owner_hn": request.data.get("source_document_owner_hn"),
            "source_document_id": request.data.get("source_document_id"),
            "clinical_history_owner_hn": request.data.get("clinical_history_owner_hn"),
            "clinical_history_source_id": request.data.get("clinical_history_source_id"),
            "source_ownership": request.data.get("source_ownership", []),
            "omics_clinical_question": request.data.get("omics_clinical_question"),
            "omics_actionability_plan": request.data.get("omics_actionability_plan"),
            "omics_informed_consent": request.data.get("omics_informed_consent"),
            "omics_utility": request.data.get("omics_utility", {}),
        }
        identity_check = validate_patient_identity(identity_input)
        if identity_check.get("identity_validation_status") != "VERIFIED":
            return Response({
                "identity_validation": identity_check,
                "analysis_state": "BLOCKED_DATA_RECONCILIATION",
                "allowed_output": "DATA_RECONCILIATION_REPORT_ONLY",
                "error": "Patient identity data conflict detected. Biological analysis blocked until data reconciliation.",
                "conflict_details": identity_check.get("conflict_details", [])
            }, status=400)

        # 1. Retrieve or create latest biological record
        latest_record = patient.axes_records.all().order_by('-record_date').first()
        
        def safe_max(a, b):
            if a is None:
                return b
            if b is None:
                return a
            return max(a, b)

        # Extract previous axis scores (default to None if none)
        updated_axes = {}
        for i in range(1, 40):
            val = getattr(latest_record, f"axis_{i}", None) if latest_record else None
            if val == 50:
                val = None
            updated_axes[i] = val


        # 1.5. TSPI Brain Local Self-Learning Prediction Branch
        use_brain_model = request.data.get('use_brain_model', False)
        brain_predicted = False
        if use_brain_model:
            import os
            import json
            tspi_data_dir = getattr(settings, 'TSPI_DATA_DIR', os.path.join(settings.BASE_DIR.parent, 'data'))
            weights_path = str(tspi_data_dir / "tspi_brain_weights.json")
            if os.path.exists(weights_path):
                try:
                    with open(weights_path, "r", encoding="utf-8") as f:
                        weights = json.load(f)
                    
                    # Extract lab values (parse from request or otherLabs)
                    simulated_labs = {
                        "fbs": fbs,
                        "hba1c": hba1c,
                        "crp": request.data.get("crp", ""),
                        "ldl": request.data.get("ldl", ""),
                        "alt": request.data.get("alt", ""),
                        "ggt": request.data.get("ggt", ""),
                    }
                    if other_labs:
                        for line in other_labs.split("\n"):
                            if ":" in line:
                                k, v = line.split(":", 1)
                                simulated_labs[k.strip().lower()] = v.strip()

                    # Extract database values as fallback if empty
                    db_labs = patient.labs if isinstance(patient.labs, dict) else {}
                    
                    def get_float_val(key, fallback):
                        val = simulated_labs.get(key)
                        if val in (None, ""):
                            val = db_labs.get(key) or db_labs.get(key.upper())
                        if val in (None, ""):
                            if key == "fbs": val = db_labs.get("Fasting Glucose") or db_labs.get("fasting_glucose") or db_labs.get("FBS")
                            elif key == "crp": val = db_labs.get("hsCRP") or db_labs.get("hscrp") or db_labs.get("CRP") or db_labs.get("Crp")
                            elif key == "ldl": val = db_labs.get("LDL Cholesterol") or db_labs.get("cholesterol_ldl") or db_labs.get("LDL")
                            elif key == "alt": val = db_labs.get("sgpt") or db_labs.get("SGPT") or db_labs.get("ALT")
                            elif key == "ggt": val = db_labs.get("GGT")
                        
                        try:
                            if val not in (None, ""):
                                return float(val)
                        except ValueError:
                            pass
                        return fallback

                    fbs_v = get_float_val("fbs", 90.0)
                    hba1c_v = get_float_val("hba1c", 5.5)
                    crp_v = get_float_val("crp", 0.5)
                    ldl_v = get_float_val("ldl", 110.0)
                    alt_v = get_float_val("alt", 30.0)
                    ggt_v = get_float_val("ggt", 35.0)

                    # Compute outputs: score_i = bias_i + fbs*coef_fbs_i + ...
                    bias = weights["bias"]
                    coefs = weights["coefficients"]
                    
                    for i in range(1, 40):
                        idx = i - 1
                        pred_score = (
                            bias[idx] +
                            fbs_v * coefs["fbs"][idx] +
                            hba1c_v * coefs["hba1c"][idx] +
                            crp_v * coefs["crp"][idx] +
                            ldl_v * coefs["ldl"][idx] +
                            alt_v * coefs["alt"][idx] +
                            ggt_v * coefs["ggt"][idx]
                        )
                        updated_axes[i] = int(max(0, min(100, round(pred_score))))
                    
                    brain_predicted = True
                except Exception as brain_err:
                    print("⚠️ TSPI Brain prediction failed, falling back to deterministic rules:", brain_err)

        # 2. Deterministic Systemic Scoring Logic based on Biomarkers (Only run if Brain didn't predict)
        mentzer_index = None
        if not brain_predicted:
            det_labs = {
                "fbs": fbs,
                "hba1c": hba1c,
                "crp": request.data.get("crp", ""),
                "ldl": request.data.get("ldl", ""),
                "alt": request.data.get("alt", ""),
                "ggt": request.data.get("ggt", ""),
            }
            if other_labs:
                for line in other_labs.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        det_labs[k.strip().lower()] = v.strip()
            
            db_labs = patient.labs if isinstance(patient.labs, dict) else {}
            def get_det_val(key):
                val = det_labs.get(key)
                if val in (None, ""):
                    val = db_labs.get(key) or db_labs.get(key.upper())
                if val in (None, ""):
                    if key == "fbs": val = db_labs.get("Fasting Glucose") or db_labs.get("fasting_glucose") or db_labs.get("FBS")
                    elif key == "crp": val = db_labs.get("hsCRP") or db_labs.get("hscrp") or db_labs.get("CRP") or db_labs.get("Crp")
                    elif key == "ldl": val = db_labs.get("LDL Cholesterol") or db_labs.get("cholesterol_ldl") or db_labs.get("LDL")
                    elif key == "alt": val = db_labs.get("sgpt") or db_labs.get("SGPT") or db_labs.get("ALT")
                    elif key == "ggt": val = db_labs.get("GGT")
                    elif key == "hb": val = db_labs.get("HGB") or db_labs.get("Hb") or db_labs.get("Hemoglobin") or db_labs.get("hgb")
                    elif key == "hct": val = db_labs.get("HCT") or db_labs.get("Hct") or db_labs.get("Hematocrit") or db_labs.get("hct")
                    elif key == "mcv": val = db_labs.get("MCV") or db_labs.get("Mcv") or db_labs.get("mcv")
                    elif key == "rbc": val = db_labs.get("RBC") or db_labs.get("Rbc") or db_labs.get("Red Blood Cell") or db_labs.get("rbc")
                try:
                    if val not in (None, ""):
                        return float(val)
                except ValueError:
                    pass
                return None

            fbs_val = get_det_val("fbs")
            hba1c_val = get_det_val("hba1c")
            hb_val = get_det_val("hb")
            hct_val = get_det_val("hct")
            mcv_val = get_det_val("mcv")
            rbc_val = get_det_val("rbc")

            mentzer_index = None
            if mcv_val is not None and rbc_val is not None and rbc_val > 0:
                mentzer_index = round(mcv_val / rbc_val, 2)

            # P1-D: every marker->axis assignment below records which entry of
            # tspi_engine.MARKER_AXIS_RELATIONS justified it, so the response can show *why*
            # each axis got touched (relation type) instead of an unlabelled if/elif.
            from .tspi_engine import MARKER_AXIS_RELATIONS
            marker_provenance = []

            def record_provenance(marker_key, raw_value):
                for rel in MARKER_AXIS_RELATIONS.get(marker_key, []):
                    marker_provenance.append({**rel, "marker": marker_key, "raw_value": raw_value})

            # 🧪 Fasting Blood Sugar (FBS) -> Glycemic (5), Glycation (27)
            if fbs_val is not None:
                if fbs_val > 125:
                    updated_axes[5] = safe_max(updated_axes[5], 85)
                    updated_axes[27] = safe_max(updated_axes[27], 70)
                    record_provenance("fbs_high", fbs_val)
                elif fbs_val > 100:
                    updated_axes[5] = safe_max(updated_axes[5], 65)
                    record_provenance("fbs_prediabetic", fbs_val)
                elif fbs_val < 70:
                    updated_axes[5] = safe_max(updated_axes[5], 60)
                    record_provenance("fbs_low", fbs_val)

            # 🧪 HbA1c -> Glycemic (5), Glycation (27)
            if hba1c_val is not None:
                if hba1c_val > 6.5:
                    updated_axes[5] = safe_max(updated_axes[5], 85)
                    updated_axes[27] = safe_max(updated_axes[27], 70)
                    record_provenance("hba1c_high", hba1c_val)
                elif hba1c_val > 5.7:
                    updated_axes[5] = safe_max(updated_axes[5], 65)
                    record_provenance("hba1c_prediabetic", hba1c_val)

            # 🧪 Hematology (Anemia) -> Stem Cell & Hematopoiesis (26), Inflammatory Load (1)
            if hb_val is not None or hct_val is not None or mcv_val is not None:
                is_anemic = False
                if hb_val is not None and hb_val < 12.0:
                    is_anemic = True
                if hct_val is not None and hct_val < 36.0:
                    is_anemic = True
                if mcv_val is not None and mcv_val < 80.0:
                    is_anemic = True

                if is_anemic:
                    updated_axes[26] = safe_max(updated_axes[26], 85)
                    updated_axes[1] = safe_max(updated_axes[1], 65)
                    record_provenance("anemia", {"hb": hb_val, "hct": hct_val, "mcv": mcv_val})

            # 🧪 Doppler Assessment -> Endothelial (20), Microvascular (21), Hemodynamics (23)
            if doppler:
                doppler_lower = doppler.lower()
                if any(x in doppler_lower for x in ["plaque", "stenosis", "calcify", "calcification", "block", "narrow", "athero"]):
                    updated_axes[20] = safe_max(updated_axes[20], 80)
                    updated_axes[21] = safe_max(updated_axes[21], 80)
                    updated_axes[23] = safe_max(updated_axes[23], 85)
                    record_provenance("doppler_atherosclerotic", doppler)

            # 🦠 Symptoms extraction (Thai & English keyword mapping to Systems)
            symptoms_lower = symptoms.lower()
            # Tiredness/Fatigue -> Mitochondrial (8), Adrenal (33)
            if any(x in symptoms_lower for x in ["เหนื่อย", "เพลีย", "fatigue", "tired", "weak", "ไม่มีแรง"]):
                updated_axes[8] = safe_max(updated_axes[8], 75)
                updated_axes[33] = safe_max(updated_axes[33], 75)
                record_provenance("symptom_fatigue", symptoms)
            # Constipation/Gut issues -> Digestive (16), Microbiome (17), Colon Biofilm (19)
            if any(x in symptoms_lower for x in ["ท้องผูก", "constipat", "ถ่ายยาก", "อืด", "เหม็น"]):
                updated_axes[16] = safe_max(updated_axes[16], 70)
                updated_axes[17] = safe_max(updated_axes[17], 75)
                updated_axes[19] = safe_max(updated_axes[19], 70)
                record_provenance("symptom_constipation", symptoms)
            # Sleep issues / Stress -> Neuro-Sleep-Stress (34)
            if any(x in symptoms_lower for x in ["นอนไม่หลับ", "insomnia", "เครียด", "stress", "กังวล", "panic"]):
                updated_axes[34] = safe_max(updated_axes[34], 75)
                record_provenance("symptom_sleep_stress", symptoms)
            # Joint/Muscle pain -> Inflammation (1), Muscle Turnover (28), Connective Tissue (30)
            if any(x in symptoms_lower for x in ["ปวดข้อ", "อักเสบ", "inflam", "joint pain", "ปวดเมื่อย", "ปวดหลัง"]):
                updated_axes[1] = safe_max(updated_axes[1], 75)
                updated_axes[28] = safe_max(updated_axes[28], 70)
                updated_axes[30] = safe_max(updated_axes[30], 75)
                record_provenance("symptom_joint_pain", symptoms)
        else:
            marker_provenance = []

        # Create new record in Django PostgreSQL EMR
        from patients.models import PatientBiologicalRecord
        new_record = PatientBiologicalRecord(patient=patient)
        for i in range(1, 40):
            setattr(new_record, f"axis_{i}", updated_axes[i])
        new_record.save()

        # Run scoring mechanics via tspi_engine.py
        from .tspi_engine import calculate_tspi_analysis
        tspi_result = calculate_tspi_analysis(
            new_record,
            bowel_status=bowel_status,
            mentzer_index=mentzer_index,
            patient_data=identity_input,
        )
        # P1-D: attach marker->axis provenance to the persisted ledger too, not just the
        # immediate response, so it stays auditable alongside the AnalysisRecord it belongs to.
        tspi_result["marker_provenance"] = marker_provenance
        tspi_result["patient_identity"] = {
            "patient_id": patient.pk, "hn": patient.hn,
            "dob": identity_input["dob"], "sex": patient.gender,
            "age_at_analysis": patient.age, "name": patient.full_name,
        }

        # Persist ONE immutable AnalysisRecord for this calculation (ans.txt problem #9 —
        # "หนึ่ง analysis record — หลาย views"). Physician/Patient/Multi-Omics report editions
        # generated later reference this same analysis_record_id instead of each recomputing
        # or caching their own copy, so they cannot silently diverge from one another.
        import hashlib
        from .models import AnalysisRecord
        from django.utils import timezone

        inputs_payload = json.dumps(
            {
                "axes": updated_axes,
                "identity": identity_input,
                "evidence": request.data.get("labs", {}),
                "marker_provenance": marker_provenance,
                "registry": tspi_result.get("canonical_registry"),
                "bowel_status": bowel_status,
                "mentzer_index": mentzer_index,
                "source_ownership": identity_input["source_ownership"],
                "lab_owner_hn": identity_input["lab_owner_hn"],
                "source_document_owner_hn": identity_input["source_document_owner_hn"],
                "clinical_history_owner_hn": identity_input["clinical_history_owner_hn"],
            },
            sort_keys=True, default=str
        )
        inputs_hash = hashlib.sha256(inputs_payload.encode("utf-8")).hexdigest()

        analysis_record = AnalysisRecord.objects.filter(
            patient=patient, inputs_hash=inputs_hash, created_at__date=timezone.now().date()
        ).order_by('-created_at').first()
        if analysis_record is None:
            analysis_record = AnalysisRecord.objects.create(
                patient=patient,
                source_record=new_record,
                framework_version=tspi_result.get("framework_version", "39-axis-master-260715"),
                inputs_hash=inputs_hash,
                ledger=tspi_result,
                is_valid=tspi_result.get("is_valid", True),
                invariant_violations=tspi_result.get("invariant_violations", []),
                identity_snapshot=tspi_result["patient_identity"],
                evidence_provenance={
                    "source_ownership": identity_input["source_ownership"],
                    "lab_source_record_id": identity_input["lab_source_record_id"],
                    "source_document_id": identity_input["source_document_id"],
                    "clinical_history_source_id": identity_input["clinical_history_source_id"],
                    "marker_provenance": marker_provenance,
                },
                registry_versions={
                    "canonical_registry": tspi_result.get("canonical_registry", {}),
                    "framework_version": tspi_result.get("framework_version"),
                    "module_registry": tspi_result.get("module_registry_status", {}),
                    "network_registry": tspi_result.get("network_registry", {}),
                },
                created_by=request.user if request.user.is_authenticated else None,
            )

        # 2.5 Save timeline entry in patient_history for real EMR tracking
        from .models import PatientHistory
        PatientHistory.objects.create(
            patient=patient,
            type="AI Assessment",
            title="การประเมินสรีรวิทยาและเวชศาสตร์แม่นยำ (TSPI Precision Engine)",
            content=f"ประเมินแกนชีวภาพ 39 แกนสำเร็จ\n- รหัสวิเคราะห์: AnalysisRecord #{analysis_record.id}\n- สภาพลำไส้: {bowel_status or 'ปกติ'}"
        )

        # 3. Call the Local Deterministic Clinical Report Generator in Python (Zero API dependency)
        from .local_report_generator import generate_local_precision_report
        
        # Parse labs passed from request or fall back
        simulated_labs = {
            "fbs": fbs,
            "hba1c": hba1c,
            "crp": request.data.get("crp"),
            "ldl": request.data.get("ldl"),
            "alt": request.data.get("alt"),
            "ggt": request.data.get("ggt"),
        }
        if other_labs:
            try:
                for line in other_labs.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        simulated_labs[k.strip().lower()] = v.strip()
            except Exception:
                pass

        insight_summary = generate_local_precision_report(patient, tspi_result, simulated_labs)

        # Save to EMR metadata
        if not patient.extra_data:
            patient.extra_data = {}
        patient.extra_data["latest_precision_insight"] = insight_summary
        patient.save()

        return Response({
            "success": True,
            "patient_id": patient.id,
            "calculated_scores": {key: axis["severity_score"] for key, axis in tspi_result["thirty_nine_axes"].items()},
            "analysis": tspi_result,
            "analysis_record_id": analysis_record.id,
            "is_valid": tspi_result.get("is_valid", True),
            "invariant_violations": tspi_result.get("invariant_violations", []),
            "insight": insight_summary,
            "mentzer_index": mentzer_index,
            "marker_provenance": marker_provenance
        })

    @action(detail=False, methods=['get'], url_path='active-intake-sessions')
    def active_intake_sessions(self, request):
        patients = Patient.objects.exclude(extra_data__intake_sessions={})
        results = []
        for p in patients:
            if p.extra_data and 'intake_sessions' in p.extra_data:
                for sid, sess in p.extra_data['intake_sessions'].items():
                    if sess.get('status') == 'active':
                        name = f"{p.first_name or ''} {p.last_name or ''}".strip() or "ไม่ทราบชื่อคนไข้"
                        results.append({
                            'id': sid,
                            'patientId': p.id,
                            'name': name,
                            'hn': p.hn,
                            'status': sess.get('status', 'active'),
                            'aiActive': sess.get('aiActive', True),
                            'messages': sess.get('messages', [])
                        })
        return Response(results)

    @action(detail=True, methods=['post'], url_path='save-intake-message')
    def save_intake_message(self, request, pk=None):
        patient = self.get_object()
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        system_message = request.data.get('system_message')
        ai_active = request.data.get('ai_active')
        
        if not session_id or not message:
            return Response({"error": "session_id and message are required"}, status=400)
            
        if not patient.extra_data:
            patient.extra_data = {}
            
        if 'intake_sessions' not in patient.extra_data:
            patient.extra_data['intake_sessions'] = {}
            
        sessions = patient.extra_data['intake_sessions']
        sess = sessions.get(session_id)
        if not sess:
            sess = {"status": "active", "aiActive": True, "messages": []}
            
        sess['messages'] = sess.get('messages', [])
        
        # Save system message first if provided (auto-intervention log)
        if system_message:
            sess['messages'].append(system_message)
            
        sess['messages'].append(message)
        
        if ai_active is not None:
            sess['aiActive'] = ai_active
            
        sessions[session_id] = sess
        patient.extra_data['intake_sessions'] = sessions
        patient.save()
        
        return Response({"success": True, "session": sess})

    @action(detail=True, methods=['post'], url_path='update-intake-status')
    def update_intake_status(self, request, pk=None):
        patient = self.get_object()
        session_id = request.data.get('session_id')
        ai_active = request.data.get('ai_active')
        
        if not session_id or ai_active is None:
            return Response({"error": "session_id and ai_active are required"}, status=400)
            
        if not patient.extra_data or 'intake_sessions' not in patient.extra_data:
            return Response({"error": "No sessions found"}, status=404)
            
        sessions = patient.extra_data['intake_sessions']
        sess = sessions.get(session_id)
        if not sess:
            return Response({"error": "Session not found"}, status=404)
            
        sess['aiActive'] = ai_active
        sessions[session_id] = sess
        patient.extra_data['intake_sessions'] = sessions
        patient.save()
        
        return Response({"success": True, "aiActive": sess['aiActive']})


class PatientBiologicalRecordViewSet(viewsets.ModelViewSet):
    pagination_class = DynamicPageNumberPagination
    serializer_class = PatientBiologicalRecordSerializer
    permission_classes = [IsClinicalStaffOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists():
            return PatientBiologicalRecord.objects.all()
        return PatientBiologicalRecord.objects.filter(patient__id_card=user.username)

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

class ClinicalKnowledgeViewSet(viewsets.ModelViewSet):
    queryset = ClinicalKnowledge.objects.all()
    serializer_class = ClinicalKnowledgeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class TspiSettingsViewSet(viewsets.ModelViewSet):
    queryset = TspiSettings.objects.all()
    serializer_class = TspiSettingsSerializer
    lookup_field = 'setting_key'

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def retrieve(self, request, *args, **kwargs):
        setting_key = self.kwargs.get('setting_key')
        if setting_key == 'ai_settings':
            import os, json
            google_key = os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
            groq_key = os.environ.get("GROQ_API_KEY", "")
            deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
            deepseek_key_v2 = os.environ.get("DEEPSEEK_API_KEY_V2", "") or deepseek_key
            
            val = {}
            try:
                instance = TspiSettings.objects.get(setting_key=setting_key)
                if instance.setting_value:
                    val = json.loads(instance.setting_value) if isinstance(instance.setting_value, str) else instance.setting_value
            except Exception:
                pass
                
            val["google_api_key"] = google_key
            val["groq_api_key"] = groq_key
            val["deepseek_api_key"] = deepseek_key
            val["deepseek_api_key_v2"] = deepseek_key_v2
            val["model"] = "gemini-2.5-flash"
            if "provider" not in val:
                val["provider"] = "gemini"
                
            return Response({
                "setting_key": setting_key,
                "setting_value": val,
                "category": "AI"
            })

        try:
            instance = TspiSettings.objects.get(setting_key=setting_key)
        except TspiSettings.DoesNotExist:
            return Response({
                "setting_key": setting_key,
                "setting_value": "{}",
                "category": "General"
            })
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        setting_key = self.kwargs.get('setting_key')
        setting_value = request.data.get('setting_value', '{}')
        category = request.data.get('category', 'General')
        
        instance, created = TspiSettings.objects.get_or_create(
            setting_key=setting_key,
            defaults={'setting_value': setting_value, 'category': category}
        )
        if not created:
            instance.setting_value = setting_value
            instance.category = category
            instance.save()
            
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PatientHistoryViewSet(viewsets.ModelViewSet):
    pagination_class = DynamicPageNumberPagination
    serializer_class = PatientHistorySerializer
    permission_classes = [IsClinicalStaffOrOwner]

    def get_queryset(self):
        user = self.request.user
        queryset = PatientHistory.objects.all()
        if not (user.is_staff or user.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()):
            queryset = queryset.filter(patient__id_card=user.username)
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

class AppointmentViewSet(viewsets.ModelViewSet):
    pagination_class = DynamicPageNumberPagination
    serializer_class = AppointmentSerializer
    permission_classes = [IsClinicalStaffOrOwner]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.all()
        if not (user.is_staff or user.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists()):
            patient = Patient.objects.filter(id_card=user.username).first()
            if patient:
                from django.db.models import Q
                queryset = queryset.filter(Q(userid=patient.legacy_id) | Q(userid=patient.hn) | Q(userid=patient.id_card) | Q(userid=patient.phone))
            else:
                queryset = queryset.filter(userid=user.username)
        userid = self.request.query_params.get('user')
        if userid:
            queryset = queryset.filter(userid=userid)
        return queryset


from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import date

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """
    Get clinical stats for the Doctor Dashboard
    """
    total_patients = Patient.objects.count()
    
    # Urgent count
    urgent_cases = Patient.objects.filter(status__in=['ด่วน', 'เคสด่วน']).count()
    
    # Active appointments today
    today = date.today()
    active_now = Appointment.objects.filter(date_meet=today).count()
    
    total_axes = 39
    total_modules = 271
    
    completion_rate = "100%" if total_patients > 0 else "0%"
    
    return Response({
        "total_patients": total_patients,
        "urgent_cases": urgent_cases,
        "active_now": active_now,
        "completion_rate": completion_rate,
        "total_axes": total_axes,
        "total_modules": total_modules
    })


class PdpaConsentViewSet(viewsets.ModelViewSet):
    serializer_class = PdpaConsentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists():
            return PdpaConsent.objects.all()
        return PdpaConsent.objects.filter(user=user)

    def perform_create(self, serializer):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
            
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        serializer.save(user=self.request.user, ip_address=ip, user_agent=user_agent)


class AutomationTaskViewSet(viewsets.ModelViewSet):
    pagination_class = DynamicPageNumberPagination
    serializer_class = AutomationTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.groups.filter(name__in=['admin', 'doctor', 'nurse']).exists():
            return AutomationTask.objects.all()
        
        patient = Patient.objects.filter(id_card=user.username).first()
        if patient:
            from django.db.models import Q
            return AutomationTask.objects.filter(Q(patient_hn=patient.hn) | Q(patient_name=patient.full_name))
        return AutomationTask.objects.none()

    @action(detail=False, methods=['post'], url_path='run-workers')
    def run_workers(self, request):
        from django.utils import timezone
        import urllib.request
        import json
        import os
        
        now = timezone.now()
        pending_tasks = AutomationTask.objects.filter(status='pending', scheduled_for__lte=now)
        
        processed_count = 0
        for task in pending_tasks:
            task.status = 'processing'
            task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] เริ่มต้นประมวลผลงานรันคิวอัตโนมัติ...")
            task.save()
            
            try:
                # ค้นหาข้อมูลคนไข้ใน PostgreSQL EMR
                from patients.models import Patient
                patient = None
                if task.patient_hn:
                    patient = Patient.objects.filter(hn=task.patient_hn).first()
                if not patient and task.patient_name:
                    patient = Patient.objects.filter(full_name=task.patient_name).first()

                if patient:
                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ตรวจพบข้อมูลเวชระเบียนคนไข้ HN: {patient.hn} | ชื่อ: {patient.full_name}")
                else:
                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ไม่พบข้อมูลคนไข้ในระบบ EMR ดำเนินการส่งแบบจำลองทั่วไป...")

                message_text = ""
                if task.task_type == 'PRE_VISIT_REMINDER':
                    message_text = f"สวัสดีครับคุณ {task.patient_name} ขอแจ้งเตือนนัดหมายตรวจล่วงหน้าของท่านในวันพรุ่งนี้ กรุณางดน้ำและอาหาร 8-12 ชั่วโมงก่อนตรวจด้วยครับ"
                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] จัดเตรียมข้อความแจ้งเตือนก่อนวันนัดหมาย")
                    
                elif task.task_type == 'NO_SHOW_CHECK':
                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] เริ่มตรวจสอบบันทึกการเข้าตรวจ EMR...")
                    from django.db.models import Q
                    appts = Appointment.objects.filter(
                        Q(userid=task.patient_hn) | Q(symptom__icontains=task.patient_name)
                    ).order_by('-date_meet')
                    
                    if appts.exists() and appts.first().status.lower() in ['pending', 'รอหมอ', 'รอดำเนินการ']:
                        task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ผลการตรวจสอบ: ตรวจพบนัดตกหล่น (ไม่เข้าเช็คอินเข้าพบแพทย์)")
                        message_text = f"สวัสดีครับคุณ {task.patient_name} เนื่องจากระบบตรวจพบนัดตกหล่นของท่านในวันนี้ สะดวกทำแบบสอบถามเลื่อนนัดหมายใหม่ไหมครับ?"
                    else:
                        task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ผลการตรวจสอบ: เข้าเช็คอินปกติหรือไม่มีนัดหมายตกหล่น")
                        task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] สิ้นสุดกระบวนการ (Triage Clean)")
                        
                elif task.task_type == 'FOLLOW_UP':
                    message_text = f"สวัสดีครับคุณ {task.patient_name} หลังจากเข้ารับยาสมุนไพรฟื้นฟูแล้ว อาการคัดกรองหรือคุณภาพชีวิตดีขึ้นไหมครับ?"
                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] จัดเตรียมข้อความส่งคำถามติดตามผลผ่าน LINE/FCM")
                
                # ส่งการแจ้งเตือนสองช่องทางขนานกัน (LINE OA & FCM Push)
                if message_text:
                    # 1. FCM Web Push Notification
                    fcm_token = patient.extra_data.get('fcm_token') if patient and patient.extra_data else None
                    if fcm_token:
                        fcm_url = "http://127.0.0.1:3000/api/ai/send-fcm-notification"
                        fcm_headers = {"Content-Type": "application/json"}
                        fcm_body = {
                            "token": fcm_token,
                            "title": "แจ้งเตือนระบบสุขภาพ EMR",
                            "body": message_text
                        }
                        try:
                            fcm_req = urllib.request.Request(
                                fcm_url,
                                data=json.dumps(fcm_body).encode('utf-8'),
                                headers=fcm_headers,
                                method='POST'
                            )
                            with urllib.request.urlopen(fcm_req, timeout=5) as fcm_res:
                                fcm_res_data = json.loads(fcm_res.read().decode('utf-8'))
                                if fcm_res_data.get('success'):
                                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ✅ ส่งข้อความ FCM Web Push เด้งแจ้งเตือนบนเบราว์เซอร์คนไข้สำเร็จ")
                                else:
                                    task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ❌ ส่ง FCM ล้มเหลว: {fcm_res_data.get('error')}")
                        except Exception as fcm_err:
                            # ในสภาวะไม่มี Node.js server รันอยู่ หรือไม่มี credentials ให้ทำแบบจำลองความคืบหน้า
                            task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ⚙️ จำลองระบบส่ง FCM: '{message_text}' ไปยังโทเค็น [{fcm_token[:15]}...]")
                    else:
                        task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ℹ️ ไม่พบ FCM Token ของคนไข้ในระบบ EMR (ข้าม Web Push)")

                    # 2. LINE OA Message Push
                    line_user_id = patient.line_user_id if patient else None
                    if line_user_id:
                        from patients.views_line import push_line_message
                        channel_access_token = os.environ.get("LINE_DOCTORPATT_CHANNEL_ACCESS_TOKEN", "")
                        if channel_access_token:
                            try:
                                push_line_message(
                                    line_user_id,
                                    [{"type": "text", "text": message_text}],
                                    channel_access_token
                                )
                                task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ✅ ส่งข้อความ Line Push Notification ไปยังแชทส่วนตัวของคนไข้สำเร็จ")
                            except Exception as line_err:
                                task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ❌ ส่ง LINE ล้มเหลว: {str(line_err)}")
                        else:
                            task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ⚙️ จำลองระบบส่ง LINE OA: '{message_text}' ไปยังแชทคนไข้ [{line_user_id[:10]}...]")
                    else:
                        task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ℹ️ ไม่พบบัญชี LINE ที่ผูกไว้ของคนไข้ในระบบ EMR (ข้าม LINE Push)")
                
                task.status = 'completed'
                task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] ดำเนินภารกิจคิวงานเสร็จสมบูรณ์เรียบร้อย")
            except Exception as ex:
                task.status = 'failed'
                task.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] 🚨 เกิดข้อขัดข้องระหว่างดำเนินงาน: {str(ex)}")
                
            task.save()
            processed_count += 1
            
        return Response({
            "success": True,
            "processed": processed_count,
            "message": f"Successfully simulated running {processed_count} automation tasks."
        })
