"""Clean setup and isolated-port regression checks.
sow: software-factories-masterclass-SOW-02
"""
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import launcher

class LauncherTests(unittest.TestCase):
    def args(self, **changes):
        v=dict(host='127.0.0.1', viewer_access='', viewer_name='', allow_peer=[],
               entry_port=8960, inspector_port=5020, mcp_port=8961,
               builder_mode='SCRIPTED', worker_python='/absent/live-worker',
               env_file=None, evidence_root='/unused',
               expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
        v.update(changes)
        return Namespace(**v)

    def test_scripted_uses_project_python_and_isolated_ports(self):
        child=MagicMock();child.poll.return_value=None;child.pid=999999
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);python=root/'python';python.touch()
            with patch.object(launcher,'ROOT',root), patch.object(launcher,'PYTHON',python), patch.dict(os.environ,{'RASA_LICENSE':'synthetic-test-only'},clear=True), patch.object(launcher.socket,'socket') as sockets, patch.object(launcher.subprocess,'run') as train, patch.object(launcher.subprocess,'Popen',return_value=child) as start, patch.object(launcher,'wait_ready') as ready, patch.object(launcher.time,'sleep',side_effect=KeyboardInterrupt), patch.object(launcher.signal,'signal'), patch.object(launcher.os,'killpg'):
                train.return_value.returncode=0
                launcher.run(self.args())
                env=train.call_args.kwargs['env']
                self.assertEqual(env['FACTORY_WORKER_PYTHON'],str(python))
                self.assertEqual(env['FACTORY_MCP_URL'],'http://127.0.0.1:8961/mcp')
                self.assertEqual(env['FACTORY_INSPECTOR_PORT'],'5020')
                self.assertEqual(env['FACTORY_ENTRY_PORT'],'8960')
                self.assertEqual(start.call_count,3)
                self.assertEqual([c.args[1] for c in ready.call_args_list],['http://127.0.0.1:5020/status','http://127.0.0.1:8960/'])
                self.assertEqual([c.args[0] for c in sockets.return_value.__enter__.return_value.bind.call_args_list],[('127.0.0.1',8960),('127.0.0.1',5020),('127.0.0.1',8961)])

    def test_invalid_or_repeated_ports_fail_before_binding(self):
        for changes in ({'entry_port':0},{'mcp_port':65536},{'mcp_port':8960}):
            with self.subTest(changes=changes),patch.object(launcher.socket,'socket') as bind:
                with self.assertRaisesRegex(ValueError,'distinct ports'):
                    launcher.run(self.args(**changes))
                bind.assert_not_called()

    def test_frontend_targets_selected_inspector(self):
        from server import frontend
        from starlette.testclient import TestClient
        with patch.dict(os.environ,{'FACTORY_ALLOWED_PEERS':'testclient','FACTORY_INSPECTOR_PORT':'5020','FACTORY_VIEWER_NAME':'127.0.0.1'},clear=True):
            r=TestClient(frontend('127.0.0.1')).get('/')
            self.assertEqual(r.status_code,200)
            self.assertIn('127.0.0.1:5020/webhooks/inspector/',r.text)
            self.assertIn('127.0.0.1%3A5020',r.text)
            self.assertNotIn(':5007',r.text)

if __name__=='__main__':unittest.main()
