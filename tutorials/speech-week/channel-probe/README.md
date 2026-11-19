# Native rc1 channel configuration probe

Internal qualification for the Speech Week publication plan, not a tutorial or
provider acceptance run. Select a separate locked environment for this project.
The Twilio version range is the exact rc1 wheel's optional channel dependency.
`probe.py` checks Inspector, browser_audio and Twilio Media Streams through the
native channel resolver with Rime-only input. All socket connects are denied.
No keys, phone call, WhatsApp message, model request or bank operation is used.
The result is retained locally; a construction failure is not a provider failure.
