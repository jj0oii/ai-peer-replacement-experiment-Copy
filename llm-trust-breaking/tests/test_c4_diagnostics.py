"""Offline HTTP fixtures; no original journals are opened for writing."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import requests
import test_c4_extension as fixtures
from peer_identity import c4_extension as c
from peer_identity import c4_http_diagnostics as d
from peer_identity.inference import StopRun

class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.C4Tests(methodName='test_state_and_handoff')
        self.fixture.setUp();self.addCleanup(self.fixture.tmp.cleanup)
        self.journal=self.fixture.journal
        self.payload=self.journal.payload(c.MODEL,self.fixture.prompts[0][2],3915,1)
        self.secret='sk-or-v1-'+'secret'*10
        self.transport=object.__new__(c.RouterTransport)
        self.transport.key=self.secret;self.transport.session=SimpleNamespace(post=Mock())

    def response(self,status,body):
        return SimpleNamespace(status_code=status,json=lambda:body,text=json.dumps(body),headers={
            'x-request-id':'request-123','cf-ray':'ray-123','Authorization':'Bearer '+self.secret,
            'Set-Cookie':'sensitive-cookie'})

    def test_status_body_route_and_request_id_preserved(self):
        response=self.response(429,{'error':{'code':429,'message':'Rate limit exceeded',
            'metadata':{'provider_name':'Google AI Studio','raw':json.dumps({'error':{'status':'RESOURCE_EXHAUSTED','message':'quota exhausted'}})}}})
        self.transport.session.post.return_value=response
        with self.assertRaises(d.RouterDiagnosticFailure) as caught:self.transport(self.payload)
        detail=caught.exception.diagnostic
        self.assertEqual(detail['http_status'],429)
        self.assertEqual(detail['request_identifiers']['x-request-id'],'request-123')
        self.assertEqual(detail['provider_error']['upstream_error']['status'],'RESOURCE_EXHAUSTED')
        self.assertEqual(detail['requested_provider_route'],c.PIN)
        self.assertTrue(detail['could_have_incurred_charge'])
        self.assertFalse(detail['automatic_retry'])
        self.transport.session.post.assert_called_once()
        self.assertFalse(self.transport.session.post.call_args.kwargs['allow_redirects'])
        self.assertNotIn('sensitive-cookie',json.dumps(detail))
        self.assertNotIn(self.secret,json.dumps(detail))

    def test_known_credentials_and_prompt_echo_redacted(self):
        message='Authorization: Bearer '+self.secret+' '+self.payload['messages'][0]['content']
        result=d.http_failure(self.response(400,{'error':{'message':message,'metadata':{'api_key':self.secret}}}),self.payload,(self.secret,)).diagnostic
        text=json.dumps(result)
        self.assertNotIn(self.secret,text)
        self.assertNotIn(self.payload['messages'][0]['content'],text)
        self.assertIn('[REDACTED]',text)

    def test_non_json_body_omitted(self):
        response=self.response(502,{})
        response.json=Mock(side_effect=ValueError())
        response.text='private proxy body '+self.secret
        result=d.http_failure(response,self.payload,(self.secret,)).diagnostic
        self.assertEqual(result['provider_error']['format'],'non-json')
        self.assertNotIn('private proxy body',json.dumps(result))

    def test_timeout_uncertain_no_exception_details_or_retry(self):
        self.transport.session.post.side_effect=requests.Timeout('URL contains '+self.secret)
        with self.assertRaises(d.RouterDiagnosticFailure) as caught:self.transport(self.payload)
        self.assertEqual(caught.exception.diagnostic['response_disposition'],'uncertain')
        self.assertIsNone(caught.exception.diagnostic['http_status'])
        self.assertNotIn(self.secret,json.dumps(caught.exception.diagnostic))
        self.transport.session.post.assert_called_once()

    def test_journal_preserves_diagnostics_and_unknown_reservation(self):
        self.transport.session.post.return_value=self.response(503,{'error':{'message':'upstream unavailable'}})
        self.journal.router=self.transport
        _,_,prompt,seed,temp=self.fixture.prompts[0]
        for _ in range(2):
            with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,prompt,seed,temp)
        self.transport.session.post.assert_called_once()
        record=self.journal.records()[0]
        self.assertEqual(record['http_diagnostic']['http_status'],503)
        self.assertNotIn('cost_usd',record)
        self.assertEqual(self.journal.totals()['accounted_usd'],record['reserved_usd'])
        self.assertEqual(record['status'],'blocked')

    def test_completed_a_reused_even_when_b_blocked(self):
        _,_,prompt,seed,temp=self.fixture.prompts[0]
        a=self.journal.ask('trial/r6/planning/A','gpt-4o-mini',prompt,seed,temp)
        successful_calls=self.fixture.mock.backend.calls
        self.transport.session.post.return_value=self.response(502,{'error':{'message':'upstream failure'}})
        self.journal.router=self.transport
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,prompt,seed,temp)
        self.assertEqual(self.journal.ask('trial/r6/planning/A','gpt-4o-mini',prompt,seed,temp),a)
        self.assertEqual(self.fixture.mock.backend.calls,successful_calls)
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,prompt,seed,temp)
        self.transport.session.post.assert_called_once()

    def test_success_diagnostic_and_original_payload_unchanged(self):
        response=self.fixture.mock(self.payload)
        body={'id':response['response_id'],'provider':response['provider'],'model':response['model_returned'],
            'usage':response['usage'],'choices':[{'message':{'content':response['content']},'finish_reason':'stop'}]}
        self.transport.session.post.return_value=self.response(200,body)
        before=copy.deepcopy(self.payload);result=self.transport(self.payload)
        self.assertEqual(result['http_diagnostic']['response_disposition'],'http_accepted')
        self.assertEqual(self.payload,before)
        self.assertEqual(self.transport.session.post.call_args.kwargs['json'],before)

    def test_local_rejection_distinguished_from_http_rejection(self):
        def invalid(payload):
            response=self.fixture.mock(payload);response['provider']='Wrong';return response
        self.journal.router=invalid
        _,_,prompt,seed,temp=self.fixture.prompts[0]
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,prompt,seed,temp)
        record=self.journal.records()[0]
        self.assertEqual(record['http_diagnostic']['response_disposition'],'http_accepted_locally_rejected')

    def test_diagnostic_text_bounded(self):
        result=d.http_failure(self.response(500,{'error':{'message':'x'*10000}}),self.payload).diagnostic
        self.assertLessEqual(len(result['provider_error']['message']),1500)

if __name__=='__main__':unittest.main()
