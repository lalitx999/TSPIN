from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient
from uuid import uuid4

from . import tests_agentic_service as fixtures
from .agentic_service import create_evidence_report_drafts
from .artifact_review import record_artifact_review
from .models import ArtifactReviewEvent, Patient


class ArtifactReviewTests(TestCase):
    def setUp(self):
        fixtures.EvidenceArtifactServiceTests.setUp(self)
        self.author.user_permissions.add(Permission.objects.get(codename='add_artifactreviewevent'))
        self.author = User.objects.get(pk=self.author.pk)
        self.args['actor'] = self.author
        self.artifact = create_evidence_report_drafts(**self.args)
        self.review_args = dict(patient_id=self.patient.pk, artifact_id=self.artifact['artifact_id'],
            actor=self.author, expected_artifact_hash=self.artifact['integrity_hash'],
            decision='REQUEST_CHANGES', reason='Synthetic review feedback')

    def api(self):
        self.author.user_permissions.add(Permission.objects.get(codename='view_artifactreviewevent'))
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=self.author.pk))
        path = f'/api/patients/{self.patient.pk}/agentic-artifacts/{self.artifact["artifact_id"]}/reviews/'
        body = {key: self.review_args[key] for key in ('expected_artifact_hash', 'decision', 'reason')}
        body['request_id'] = str(uuid4())
        return client, path, body

    def test_api_retries_return_same_event_and_conflicts_do_not_write(self):
        client, path, body = self.api()
        first = client.post(path, body, format='json')
        retry = client.post(path, body, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.data['replayed'])
        self.assertEqual(first.data['review_event_id'], retry.data['review_event_id'])
        self.assertEqual(client.post(path, {**body, 'reason': 'different'}, format='json').status_code, 409)
        self.assertEqual(ArtifactReviewEvent.objects.count(), 1)
        self.assertEqual(client.post(path, {**body, 'request_id': str(uuid4())}, format='json').status_code, 201)
        self.assertEqual(ArtifactReviewEvent.objects.count(), 2)

    def test_api_requires_valid_request_id(self):
        client, path, body = self.api()
        for value in (None, '', 'invalid', [], 1):
            self.assertEqual(client.post(path, {**body, 'request_id': value}, format='json').status_code, 400)
        del body['request_id']
        self.assertEqual(client.post(path, body, format='json').status_code, 400)
        self.assertFalse(ArtifactReviewEvent.objects.exists())

    def test_replay_still_requires_current_permission(self):
        client, path, body = self.api()
        self.assertEqual(client.post(path, body, format='json').status_code, 201)
        self.author.user_permissions.remove(Permission.objects.get(codename='add_artifactreviewevent'))
        client.force_authenticate(User.objects.get(pk=self.author.pk))
        self.assertEqual(client.post(path, body, format='json').status_code, 403)
        self.assertEqual(ArtifactReviewEvent.objects.count(), 1)

    def test_database_enforces_unique_request_identity(self):
        request_id = uuid4()
        result = record_artifact_review(**self.review_args, request_id=request_id)
        event = ArtifactReviewEvent.objects.get(pk=result['review_event_id'])
        with self.assertRaises(IntegrityError), transaction.atomic():
            ArtifactReviewEvent.objects.create(artifact=event.artifact, actor=event.actor,
                artifact_hash=event.artifact_hash, request_id=request_id,
                decision=event.decision, reason=event.reason)
        self.assertEqual(ArtifactReviewEvent.objects.count(), 1)

    def test_api_post_and_read_are_non_releasing_and_uncached(self):
        client, path, body = self.api()
        response = client.post(path, body, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['send_allowed'])
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['results'][0]['actor_id'], self.author.pk)
        self.assertEqual(response.data['results'][0]['reason'], body['reason'])
        self.assertEqual(client.patch(path, {}, format='json').status_code, 405)
        self.assertEqual(client.delete(path).status_code, 405)

    def test_api_rejects_client_actor_approval_malformed_and_stale(self):
        client, path, body = self.api()
        for payload in ([], {**body, 'actor_id': self.author.pk}, {**body, 'decision': 'APPROVE'},
                        {**body, 'decision': []}, {**body, 'reason': ' '}, {**body, 'reason': 'x' * 4001}):
            self.assertEqual(client.post(path, payload, format='json').status_code, 400)
        self.assertEqual(client.post(path, {**body, 'expected_artifact_hash': '0' * 64}, format='json').status_code, 409)
        self.assertFalse(ArtifactReviewEvent.objects.exists())

    def test_api_denies_unauthorized_and_wrong_patient(self):
        client, path, body = self.api()
        client.force_authenticate(None)
        self.assertIn(client.get(path).status_code, (401, 403))
        outsider = User.objects.create_user(username='review-outsider', password='synthetic')
        client.force_authenticate(outsider)
        self.assertEqual(client.post(path, body, format='json').status_code, 403)
        self.assertEqual(client.get(path).status_code, 403)
        client.force_authenticate(self.author)
        other = Patient.objects.create(first_name='Synthetic', last_name='Other', hn='REVIEW-OTHER', legacy_id='review-other')
        wrong = path.replace(f'/patients/{self.patient.pk}/', f'/patients/{other.pk}/')
        self.assertEqual(client.post(wrong, body, format='json').status_code, 404)
        self.assertFalse(ArtifactReviewEvent.objects.exists())

    def test_api_cursor_and_uuid_validation(self):
        client, path, body = self.api()
        for cursor in ('-1', '0', 'abc', '9' * 30):
            self.assertEqual(client.get(path, {'before_id': cursor}).status_code, 400)
        bad = path.replace(self.artifact['artifact_id'], 'not-a-uuid')
        self.assertEqual(client.get(bad).status_code, 400)

    def test_api_history_is_bounded_and_cursor_has_no_overlap(self):
        client, path, body = self.api()
        for _ in range(51):
            record_artifact_review(**self.review_args)
        page = client.get(path).data
        self.assertEqual(len(page['results']), 50)
        older = client.get(path, {'before_id': page['next_before_id']}).data
        self.assertEqual(len(older['results']), 1)
        self.assertIsNone(older['next_before_id'])
        self.assertNotIn(older['results'][0]['id'], [r['id'] for r in page['results']])

    def test_feedback_is_persisted_without_granting_approval(self):
        result = record_artifact_review(**self.review_args)
        self.assertFalse(result['send_allowed'])
        self.assertFalse(result['clinical_use_authorized'])
        event = ArtifactReviewEvent.objects.get(pk=result['review_event_id'])
        self.assertEqual(event.actor, self.author)
        self.assertEqual(event.artifact_hash, self.artifact['integrity_hash'])
        self.assertIsNotNone(event.created_at)

    def test_picker_search_and_list_do_not_expose_payloads(self):
        client, _, _ = self.api()
        search = '/api/patients/artifact-review-patients/'
        response = client.get(search, {'q': self.patient.hn})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.patient.pk, [row['id'] for row in response.data['results']])
        self.assertEqual(response['Cache-Control'], 'no-store')
        path = f'/api/patients/{self.patient.pk}/artifact-review-list/'
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['id'], self.artifact['artifact_id'])
        self.assertNotIn('payload', response.data['results'][0])
        self.assertEqual(client.get(path, {'before_id': 'invalid'}).status_code, 400)
        self.assertEqual(client.get(search, {'q': 'x'}).status_code, 400)
        client.force_authenticate(User.objects.create_user(username='picker-outsider'))
        self.assertEqual(client.get(search, {'q': self.patient.hn}).status_code, 403)
        self.assertEqual(client.get(path).status_code, 403)

    def test_stale_hash_and_approval_decision_are_rejected(self):
        for change in ({'expected_artifact_hash': '0' * 64}, {'decision': 'APPROVE'},
                       {'reason': ''}, {'reason': 'x' * 4001}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                record_artifact_review(**{**self.review_args, **change})
        self.assertFalse(ArtifactReviewEvent.objects.exists())

    def test_inactive_actor_and_missing_permission_cannot_review(self):
        self.author.is_active = False
        with self.assertRaises(PermissionDenied):
            record_artifact_review(**self.review_args)
        self.author.is_active = True
        self.author.user_permissions.remove(Permission.objects.get(codename='add_artifactreviewevent'))
        actor = User.objects.get(pk=self.author.pk)
        with self.assertRaises(PermissionDenied):
            record_artifact_review(**{**self.review_args, 'actor': actor})
        self.assertFalse(ArtifactReviewEvent.objects.exists())

    def test_history_cannot_be_overwritten_or_deleted(self):
        record_artifact_review(**self.review_args)
        event = ArtifactReviewEvent.objects.get()
        for mutation in (event.save, event.delete,
                         lambda: ArtifactReviewEvent.objects.all().update(reason='changed'),
                         lambda: ArtifactReviewEvent.objects.all().delete()):
            with self.assertRaises(ValidationError):
                mutation()
        record_artifact_review(**{**self.review_args, 'decision': 'REJECT'})
        self.assertEqual(ArtifactReviewEvent.objects.count(), 2)
