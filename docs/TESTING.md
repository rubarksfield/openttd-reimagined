# Test status

This is an experimental native fork. Build success, simulator play, physical launch and compatibility acceptance are separate results.

## Established baseline

- 94 original unit cases and two original regression comparisons pass in unmodified OpenTTD 15.3.
- 37 importer and seven managed-resource checks pass with AddressSanitizer/UndefinedBehaviorSanitizer.
- Original native bus and rail routes have carried passengers and earned fares in owned simulators. The short railway fixture loses money after costs.
- Native saves have round-tripped through unchanged 15.3. One downloaded/imported OpenGFX+ Trains set has been activated and reloaded.
- A development-signed prototype was installed and launched on a physical iPad.

## Current tutorial acceptance

Original-style reading guide and Story Book instructions are implemented. The lesson uses actual button/window events and original world queries, saves its progress, and highlights the original controls. A fresh iPad simulator run passed every stage 0–17 using actual HID: two stops, correctly connected depot, bus purchase, both orders, movement, passengers and fare income. It also asserted that Story Book transitions and two-finger panning preserve Go To. The dependency-free starter save loads/resumes in unchanged 15.3 with no missing NewGRF or error pause. Earlier QA exercised wrong-depot rejection and saved-stage recovery. Other device/configuration variants remain separate checks.

## Still open

Full original-feature parity, multiplayer interoperability, broad NewGRF/AI/GameScript compatibility, compact-layout coverage, physical-device gameplay, frame-time/thermal/battery measurement, continuous pinch scaling, inertia, music, and optional PNG/LZO support. The first guided level teaches a bus route, not every transport type.

No App Store approval or TestFlight availability is implied. Store metadata, signing/upload access, source/asset compliance and interpreted-content policy review are distinct release gates.

## Reproduce

Use the build and check commands in README. Simulator automation reads a locally generated `evidence/ipad-simulator.json` fixture and verifies the simulator is explicitly project-owned. Runtime evidence and all personal saves/device/signing records are intentionally excluded from this public repository. Never run automated construction tests in your real company.
