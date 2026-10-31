# Test status

This is an experimental native fork. Build success, simulator play, physical launch and compatibility acceptance are separate results.

## Established baseline

- 94 original unit cases and two original regression comparisons pass in unmodified OpenTTD 15.3.
- 37 importer and seven managed-resource checks pass with AddressSanitizer/UndefinedBehaviorSanitizer.
- Original native bus and rail routes have carried passengers and earned fares in owned simulators. The short railway fixture loses money after costs.
- Native saves have round-tripped through unchanged 15.3. One downloaded/imported OpenGFX+ Trains set has been activated and reloaded.
- A development-signed prototype was installed and launched on a physical iPad.

## Current tutorial acceptance

Original-style reading guide and Story Book instructions are implemented. The lesson uses actual button/window events and original world queries, saves its progress, and highlights the original controls. A fresh iPad simulator run passed every stage 0–17 using actual HID: two stops, correctly connected depot, bus purchase, both orders, movement, passengers and fare income. It also asserted that Story Book transitions and two-finger panning preserve Go To. The dependency-free starter save loads/resumes in unchanged 15.3 with no missing NewGRF or error pause. QA also exercised wrong-depot rejection and cold saved-stage recovery: the existing bus was reopened without another purchase, its orders were completed and it earned a fare. A fresh 0–17 regression passed after that recovery change. Other device/configuration variants remain separate checks.

## Still open

Full original-feature parity, multiplayer interoperability, broad NewGRF/AI/GameScript compatibility, compact-layout coverage, physical-device gameplay, frame-time/thermal/battery measurement, continuous pinch scaling, inertia, music, and optional PNG/LZO support. The first guided level teaches a bus route, not every transport type.

No App Store approval or TestFlight availability is implied. Store metadata, signing/upload access, source/asset compliance and interpreted-content policy review are distinct release gates.

## Reproduce

Use the build and check commands in README. Simulator automation reads a locally generated `evidence/ipad-simulator.json` fixture and verifies the simulator is explicitly project-owned. Runtime evidence and all personal saves/device/signing records are intentionally excluded from this public repository. Never run automated construction tests in your real company.

## Build 5 distribution checks

The actual 13-inch iPad simulator renders at both portrait and landscape sizes. All four rotations preserve the active lesson; real caption touches are acknowledged at the expected original coordinates in each orientation. Original road-tool and bus-stop selection still advances coaching after rotation. The signed Release archive includes matching dSYM UUIDs and passes the archive verifier. Apple accepted and processed the upload; build 5 is Missing Compliance, not available to testers.

A clean build 5 install on the 13-inch fixture also passed the complete 0–17 route with an explicit rejection of original engine error windows. A reused document container had retained an obsolete starter; that fixture was fully backed up and reinstalled. Its replacement matches the canonical bundled save. The medium iPhone fixture passed all ten guide pages and began its clean lesson with the road control highlighted.

The simulator accessibility automation service timed out; real HID and native screenshots were used for these checks. A small-phone safe-area scale is applied to QA coordinates using the same transform as the native host. Full physical touch-target/accessibility acceptance remains separate.

## Build 6 placement recovery

Run `python3 script/qa_first_route.py --simulator-record evidence/store-ipad-simulator.json --exercise-placement-errors` from an owned iPad simulator's main menu, after observing its current geometry. This sends real HID through the original interface, deliberately builds a stop and depot on adjacent wrong tiles, builds a wrongly facing depot on the correct tile, repairs it through the original bulldozer, and completes all 18 stages through passenger income. Evidence includes the live Story Book target reference and the close-up camera. No simulation commands are injected.

`python3 script/test_tutorial_resource_update.py` checks the actual native resource updater with the exact shipped lesson files, custom scripts/translations/metadata, symlinks, partial updates and save preservation under address/undefined sanitizers. `python3 script/test_managed_resources.py` checks the existing title migration.

The build 6 simulator route and signed device build pass. Physical-device acceptance of the placement fix is pending. The prior phone acceptance does not establish a complete build 6 phone playthrough.
