import os,json,socket,traceback
from pathlib import Path
from unittest.mock import patch
from importlib.metadata import version
from rasa.mantle.config.channels import parse_channels,resolve_voice_channel_speech
from rasa.core.channels import BUILTIN_CHANNELS
result={'runtime':version('rasa-pro'),'provider_calls':0,'cases':[]}
with patch.object(socket.socket,'connect',side_effect=AssertionError('network_forbidden')):
 for name in ('inspector','browser_audio','twilio_media_streams'):
  raw={'enabled':True,'server_url':'http://127.0.0.1:5005','speech_model':{'name':'rime_prism','voice':'aurora','instructions':'Delegate fictional banking tasks to Rasa.'}}
  case={'channel':name,'raw_media_keys':['speech_model']}
  try:
   resolved=resolve_voice_channel_speech(parse_channels({name:raw}))
   case['resolved_media_keys']=[k for k in ('asr','tts','speech_model') if k in resolved[name]]
   BUILTIN_CHANNELS[name].from_credentials(resolved[name])
   case['outcome']='NATIVE_CHANNEL_CONSTRUCTED'
  except Exception as error:
   case.update(outcome='NATIVE_CONFIG_REFUSED',exception_type=type(error).__name__,reason=str(error))
  result['cases'].append(case)
p=Path('/workspaces/rasa-rc1-three-channel-proof-with-twilio.json');p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
