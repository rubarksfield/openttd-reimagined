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

The build 6 simulator route and signed device build pass. Physical-device acceptance of the placement fix is pending.

## Additional build 6 checks, 31 October 2026

A clean local staging build verified all 106 published source/asset manifest entries against commit `b6fa26216a7fef18839c0af5daef5ac94445c135`. Fresh runs passed 94 unchanged upstream unit cases, both original regression comparisons, the original save/tick smoke checks, 37 importer cases, ten tutorial resource-update cases and seven title-resource cases. The last two suites run the native Foundation implementations with address/undefined sanitizers; the importer has its own sanitizer build.

The new Show build tile link was exercised through actual HID after zooming out in each of the four iPad orientations. Each returned to the correct tile at zoom level 1. Merely displaying the link or retaining its state was not counted as action acceptance.

The medium iPhone simulator passed all ten guide pages and completed the actual bus lesson: a misplaced stop triggered feedback, both required stops and a connected depot were built, a passenger bus was purchased, both orders were entered, and the bus carried passengers and earned a fare. Original oversized purchase/load windows required two-finger scrolling; overlapping orders/vehicle windows required dragging aside. The original Switch toolbars control reveals Save/Load on compact screens. These are working controls, with remaining compact-layout usability work.

The completed phone save loaded with the current lesson script in unchanged OpenTTD 15.3, resumed the completed lesson and advanced 100 simulation ticks. The native app then loaded the returned save through the original Load Game interface without a load/script error. A first attempt used a user-paused save and correctly advanced zero simulation ticks; the verification was repeated with an actual unpaused native save rather than editing pause bits.

Real original mixer PCM and progressing native audio callbacks passed in the phone simulator. This does not verify hardware-speaker output, interruptions, Bluetooth, battery or thermal behavior. No physical iPad was attached for these additional checks.

### Importer fixture prerequisites

The importer suite is a native executable, not a Python-only test. Before running it, prepare the verified upstream and archive sources with the build scripts, configure/build `cmake/content-import-tests`, and create the original fixture layout:

- `runtime/native-save-roundtrip/content_download/newgrf/4f472b31-OpenGFX_Trains-0.3.0.tar`, an actual OpenGFX+ Trains 0.3.0 package downloaded through OpenTTD's original content interface. The exercised archive's SHA-256 is `7ca9a4743d87c3470a201a001aa3ede2129b637d54393ae9cb3dd7bc28245f49`.
- `runtime/native-save-roundtrip/native-created.sav`, a real native-created OpenTTD save.

These runtime fixtures are deliberately not in this public source repository. Missing fixture errors must be resolved with the real files, not by skipping security cases. The 37 cases include real imports, path traversal, links, Unicode/case collisions, hostile archives and preservation of the existing player save. The title-resource test also requires `build/ipad-resources/baseset/opntitle.dat`, generated by the app preparation scripts.
