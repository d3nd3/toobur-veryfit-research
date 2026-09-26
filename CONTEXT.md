# Toobur / VeryFit protocol research

Reverse-engineering and Gadgetbridge driver work for IDO/Realtek (0x0AF0) fitness bands sold as Toobur, Runlio, VeryFit skins, etc.

## Language

**Driver completeness**:
The Gadgetbridge Toobur driver is “complete” when every feature Gadgetbridge already exposes (notifications, alarms, health charts, device settings) is wired end-to-end — not when the official VeryFit app is fully replicated.
_Avoid_: Full parity, feature-complete, done

**Protocol coverage**:
The watch accepts and returns the correct bytes for a command, verifiable via logcat or Web Bluetooth experiments.
_Avoid_: Implemented (ambiguous — may mean GB UI only)

**Gadgetbridge integration**:
Protocol behavior plus persistence, UI, and coordinator hooks so the feature is usable inside Gadgetbridge (e.g. sleep in charts, not just parsed in logcat).
_Avoid_: End-to-end (too generic)

**VeryFit parity**:
Matching the official VeryFit app feature-for-feature (message center, OTA firmware, watch-face store, etc.).
_Avoid_: Complete driver (we use that for GB integration instead)

**Phase A / B / C**:
Staged driver milestones. **A** = GB hooks for existing UI (notifications, calls, v3 alarms, sleep/HR/activity persistence, scheduled DND/brightness). **B** = remaining logcat-confirmed SET/GET toggles. **C** = device-specific or speculative (watch faces, OTA, blood sugar, VO2Max, …).
_Avoid_: MVP, v1, backlog

**Logcat-confirmed command**:
A TX/RX byte sequence backed by a capture in `logcat_dumps/` or `packetdumps/` — the wire reference for implementation.
_Avoid_: Documented, known command

**Canonical firmware**:
TOOBUR A200 / BAND 8 with v3 health sync — the reference capture set in this repo. Other VeryFit skins are supported via func-table gating, not a second parallel implementation.
_Avoid_: Default device, primary watch

**Banglejs build flavor**:
The Gadgetbridge APK variant that bundles Bangle.js device support alongside mainline devices. Chosen for multi-watch households (Bangle.js + Toobur), not because VeryFit protocol differs in that flavor.
_Avoid_: Bangle driver, bangle protocol

**Stock chart integration**:
Surfacing synced health data through Gadgetbridge’s built-in Charts / Activity / Sleep / SpO₂ / Stress tabs via sample providers and coordinator flags — not custom Toobur Activities.
_Avoid_: Native UI, custom dashboard (unless GB has no chart for the metric)

**Custom Toobur screen**:
A device-specific Activity reserved for metrics or diagnostics Gadgetbridge has no stock chart for (sport session breakdown, raw v3 sync inspect).
_Avoid_: Graphs, charts (use stock chart integration when possible)

**Confirmed feature**:
A VeryFit capability whose TX bytes, RX parsing, and expected domain output are locked by passing unit tests against logcat-derived fixtures — not merely listed in docs or HTML tools.
_Avoid_: Implemented, documented

**Feature confirmation pipeline**:
Build order for each capability: (1) TX builder test against capture hex → (2) RX parser test producing domain objects → (3) entry added to confirmed-features manifest → (4) Gadgetbridge integration (persist, coordinator flags, stock charts). UI wiring never precedes parser confirmation.
_Avoid_: TDD, test-first (too generic)

**Response data**:
The structured domain output parsed from watch replies (e.g. sleep stages, workout duration, alarm slot) — what tests assert on before any DB or UI work.
_Avoid_: Payload, bytes (raw wire format)

**Confirmed-features manifest**:
Human-readable registry at `docs/confirmed-features.md`: feature ID, source capture, test class, confirmation stage. Kept in sync with `@ConfirmedFeature` annotations on tests; CI guard via `ConfirmedFeaturesTest`.
_Avoid_: Feature list, roadmap

**Confirmation stage**:
Lifecycle of a capability: `tx-confirmed` (outbound packet matches capture) → `rx-confirmed` (parser test passes on reply hex) → `gb-wired` (persist + coordinator + chart). GB/UI work starts only at `rx-confirmed`.
_Avoid_: Done, implemented

**Live BLE probe**:
Host-side script (Python + Bleak on the USB BT adapter) that sends TX bytes, records RX notifications, and writes hex fixtures for offline JUnit parser tests. Used when logcat dumps are missing or incomplete.
_Avoid_: Integration test, hardware test

**Fixture test**:
Offline JUnit test using hex files in `app/src/test/resources/toobur/fixtures/` — runs in CI without a watch. The only gate for `rx-confirmed` and GB wiring.
_Avoid_: Unit test (too generic)

**Live probe session**:
Short window where the Toobur is in range, awake, and disconnected from the phone so the host BT adapter can connect exclusively. On-demand during development, not continuous.
_Avoid_: Hardware CI, paired testing

**A200 protocol reference**:
The canonical BLE command document [`A200-PROTOCOL.md`](../A200-PROTOCOL.md) — bruteforce-valid keys, capture examples, and Gadgetbridge wiring status. Single source of wire truth for this repo.
_Avoid_: TOOBUR.md (for command tables), confirmed-only (for authoritative status)
