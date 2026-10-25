"""Traveller-language requirements over deterministic parsing and real MCP transport.
No model request or real provider request is made.
sow: software-factories-masterclass-SOW-02 / flagship-resources-SOW-01
"""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys
import unittest

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from briefing.traveller import TravellerQuestion, destination_hint, journey, transfer_time

NOW = datetime(2026, 10, 22, 23, tzinfo=timezone.utc)
TECHNICAL_QUESTION = re.compile(r'\b(?:callsign|ADS-B|ICAO|ISO|timezone|UTC|minutes)\b', re.I)


class OrdinaryLanguageControls(unittest.TestCase):
    def test_city_alias_and_explicit_destination_beat_origin_table_order(self):
        for text, expected in (
            ('Manhattan', 'New York'), ('New York City', 'New York'),
            ('Lufthansa 400 from Frankfurt to JFK', 'KJFK'),
            ('from LHR to New York', 'New York'),
            ('to London via New York', 'London'),
            ('to John F. Kennedy airport', 'KJFK'),
        ):
            with self.subTest(text=text):
                self.assertEqual(destination_hint(text), expected)
        with self.assertRaises(TravellerQuestion) as caught:
            journey('Lufthansa 400 to JFK or Newark', now=NOW)
        self.assertEqual(caught.exception.field, 'destination')
        self.assertIsNone(TECHNICAL_QUESTION.search(caught.exception.question))

    def test_half_and_compound_travel_times_do_not_match_shorter_substrings(self):
        for text, expected in (('Allow half an hour', 30), ('allow an hour and a half', 90),
                               ('allow 1 hour 30 minutes', 90), ('allow an hour', 60)):
            with self.subTest(text=text):
                self.assertEqual(transfer_time(text), expected)
        self.assertIsNone(transfer_time('allow 1.5 hours'))  # Never misread the 5 as five hours.

    def test_an_unreadable_correction_does_not_silently_restore_the_default(self):
        original = journey('Lufthansa 400 to JFK, 6 pm tomorrow', now=NOW)
        previous = {**original, 'awaiting':'transfer_minutes'}
        with self.assertRaises(TravellerQuestion) as caught:
            journey('not sure yet', previous, now=NOW)
        self.assertEqual(caught.exception.field, 'transfer_minutes')
        self.assertEqual(caught.exception.inputs['callsign'], original['callsign'])
        self.assertEqual(caught.exception.inputs['meeting_time'], original['meeting_time'])
        self.assertIsNone(TECHNICAL_QUESTION.search(caught.exception.question))


def sources_fixture():
    from zeo_core.integrations.briefing_sources import PublicBriefingSources, PublicSourceHTTP
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.host == 'api.adsb.lol':
            if request.method == 'POST':
                return httpx.Response(201)
            return httpx.Response(200, json={'now':NOW.timestamp()*1000,'ac':[{
                'flight':'DLH400','lat':40.5,'lon':-74.0,'gs':350.0,'seen_pos':5,'alt_baro':25000}]})
        if request.url.host == 'api.met.no':
            return httpx.Response(200,json={'properties':{'meta':{'updated_at':NOW.isoformat()},
                'timeseries':[{'time':(NOW+timedelta(hours=n)).isoformat(),'data':{
                    'instant':{'details':{'air_temperature':15+n}},'next_1_hours':{'details':{
                        'precipitation_amount':0,'probability_of_precipitation':10}}}} for n in range(4)]}})
        if request.url.host != 'data-api.ecb.europa.eu':
            raise AssertionError('Unexpected source request')
        return httpx.Response(200,text='FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n'
            'D,USD,EUR,SP00,A,2026-10-20,1.1\nD,USD,EUR,SP00,A,2026-10-21,1.2\n'
            'D,GBP,EUR,SP00,A,2026-10-20,0.8\nD,GBP,EUR,SP00,A,2026-10-21,0.9\n')
    tick = [0.0]
    def sleep(seconds):
        tick[0] += seconds
    return PublicBriefingSources(PublicSourceHTTP(transport=httpx.MockTransport(handler),clock=lambda:NOW,
        monotonic=lambda:tick[0],sleep=sleep),clock=lambda:NOW), requests


class NaturalAnswerMCP(unittest.IsolatedAsyncioTestCase):
    async def test_ordinary_answers_resume_same_briefing_and_reach_validated_cards(self):
        from briefing.jobs import Jobs
        from briefing.mcp_app import create_app
        from briefing.public_sources import PublicSourcesRunner
        sources, requests = sources_fixture()
        runner = PublicSourcesRunner(sources, clock=lambda:NOW)
        jobs = Jobs(runner,ownership_mode='capability')
        token = 'synthetic-traveller-language-transport-control'
        app = create_app(jobs,transport_token=token)
        try:
            async with app._app.router.lifespan_context(app._app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://127.0.0.1:8942',
                    headers={'accept':'application/json, text/event-stream','authorization':'Bearer '+token}) as client:
                    serial = 0
                    async def rpc(method,params):
                        nonlocal serial
                        serial += 1
                        response = await client.post('/mcp',json={'jsonrpc':'2.0','id':serial,'method':method,'params':params})
                        self.assertEqual(response.status_code,200)
                        return response.json()['result']
                    await rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},
                        'clientInfo':{'name':'traveller-control','version':'1'}})
                    async def call(arguments):
                        result = await rpc('tools/call',{'name':'briefing','arguments':arguments})
                        self.assertFalse(result.get('isError',False),result)
                        return result['structuredContent']
                    started = await call({'action':'start','request':'JFK'})
                    private_id = started['briefing_id']
                    await jobs._jobs[private_id].task
                    state = await call({'action':'get','briefing_id':private_id})
                    self.assertEqual(state['needs_input']['field'],'flight')
                    self.assertIsNone(TECHNICAL_QUESTION.search(state['needs_input']['question']))
                    self.assertEqual(requests,[])
                    await call({'action':'revise','briefing_id':private_id,'change':'Lufthansa 400'})
                    await jobs._jobs[private_id].task
                    state = await call({'action':'get','briefing_id':private_id})
                    self.assertEqual(state['needs_input']['field'],'meeting_time')
                    self.assertIsNone(TECHNICAL_QUESTION.search(state['needs_input']['question']))
                    self.assertEqual(requests,[])
                    await call({'action':'revise','briefing_id':private_id,'change':'6 pm tomorrow'})
                    await jobs._jobs[private_id].task
                    state = await call({'action':'get','briefing_id':private_id})
                    self.assertEqual(state['status'],'complete',state)
                    self.assertEqual(len(state['cards']),4)
                    inputs = jobs._jobs[private_id].inputs
                    self.assertEqual(inputs['callsign'],'DLH400')
                    self.assertEqual(inputs['meeting_time'],'2026-10-23T18:00:00-04:00')
                    self.assertEqual(inputs['transfer_minutes'],90)
                    self.assertTrue(inputs['transfer_assumed'])
                    timeline = next(c['data_ref'] for c in state['cards'] if c['event']['component']=='arrival_timeline')
                    self.assertTrue(any(a['kind']=='assumption' for a in timeline['assumptions']))
                    self.assertEqual(datetime.fromisoformat(timeline['payload']['meeting_time']),
                                     datetime.fromisoformat(inputs['meeting_time']))
                    page = (await client.get('/cards')).text
                    self.assertNotIn(private_id,page)
                    self.assertIn('ASSUMPTION',page)
        finally:
            await jobs.close()
            runner.close()


if __name__ == '__main__':
    unittest.main()
