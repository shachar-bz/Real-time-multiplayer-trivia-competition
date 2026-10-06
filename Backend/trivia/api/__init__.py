"""Transport: Socket.IO events and HTTP routes.

The only layer that knows event names, payload shapes (camelCase), rooms and
sound effects. Incoming events are parsed into plain values and handed to the
services; outgoing `GameEvents` are turned into payloads by `serializers` and
emitted by `publisher`. The wire protocol is frozen by
tests/contract/protocol_baseline.json.
"""
