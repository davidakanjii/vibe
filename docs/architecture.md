# Architecture and audio decisions

## Transactional platform

Next.js provides the responsive PWA and same-origin API proxy. FastAPI owns authenticated operations, SQLAlchemy models and authorization; Alembic owns schema evolution. PostgreSQL is the source of truth. PostGIS is available in the Compose database image for future spatial queries; the presence of PostGIS does not establish that distance discovery is implemented. Redis and RQ provide the asynchronous execution boundary. A job must be safe to retry before it is placed in this queue.

Tenants, membership, roles, event assignments and resource ownership must be resolved server-side. A tenant selector or submitted tenant ID is a request parameter, never proof of access. Privileged role assignment must be a separately authorized action. The application must never accept a client claim that a payment succeeded as a licence grant.

S3-compatible storage is separately provisioned; protected identity documents belong in a private bucket with short signed URL lifetimes, restricted operator access, malware scanning and retention limits. The included optional MinIO service does not by itself implement those policies. Do not collect identity documents before that workflow exists.

## Live audio boundary

Bluetooth links the guest phone to its own headphones. Venue Wi-Fi or mobile data carries browser audio. A WebRTC SFU such as LiveKit is the selected boundary because it supports interactive latency and authenticated participant grants, while avoiding custom browser transport protocols. Production listeners require event admission, an active licence, channel permission, an expiring token and enforceable capacity policy. SFU room/channel grants alone do not guarantee concurrency limits; reconcile admissions with authoritative SFU participant events, disconnect revoked users and test concurrent joins before commercial enforcement is claimed.

Separate event/channel rooms can enforce channel isolation. A listener changes the authorized subscription or room when switching DJs. DJs receive publish permission only for their assigned channel. Hypemen must not receive a broad publisher credential that bypasses routing policy. Zone and event assignment must be checked for every routing change.

The required hypeman feature is **server-side mixing before delivery**. An SFU forwards tracks; it does not mix them. A future isolated mixer must ingest DJ and authorized microphone tracks, apply gain, ducking, limiter and echo safeguards, then publish a single mixed channel track. Multiple browser tracks are not a substitute for this requirement. Broadcast-all and emergency priorities need explicit operator authorization and audit. This repository does not claim the full mixer is complete.

## Trade-offs and capacity

WebRTC provides low-latency interactive media but requires UDP reachability, TURN fallback, TLS, observability and device-specific testing. Relay traffic can dominate cost. HLS offers broad buffering/network compatibility and CDN distribution but adds delay; it is unsuitable for real-time microphone interaction and is a future fallback only. No offline audio fallback exists. A failed audio connection must show an actionable reconnect state without charging or pretending playback started.

Plan egress from encoded bitrate multiplied by simultaneous listeners, then measure protocol overhead and relay use. For example, 128 kbit/s × 1,000 listeners is about 128 Mbit/s before overhead. This is a planning calculation, not a measured VibeSync capacity. Mobile Bluetooth latency and operating-system background suspension can add delay independently of the transport. Never promise synchronized venue-wide headphone timing without measurement.

## Required physical verification

Record browser/OS/device versions, network topology, codec, venue load, ingest-to-ear latency percentiles, packet loss, reconnect time, switching delay, battery drain, audio interruption and feedback behavior. Test actual Android Chrome and iPhone Safari with Bluetooth devices; cover lock screen, background tabs, calls, permission revocation, weak Wi-Fi, Wi-Fi/mobile handover and TURN-only networks. Use a staged load test with real SFU telemetry. No such physical test has been performed as part of this repository delivery.

## Geography and privacy

Import only licensed or authoritative datasets with source URL, licence, retrieval date, version, checksum, record counts and validation findings. Distinguish administrative units from informal nightlife areas. No Nigerian ward, LGA, state codes or boundaries are fabricated or bundled. Initial product configuration must wait for a reviewed import. Treat home community, preferred event locations and optional current location as separate concepts. Precise location is opt-in, minimized, retained only for a defined purpose, and excluded from public profiles and advertising targeting by default.
