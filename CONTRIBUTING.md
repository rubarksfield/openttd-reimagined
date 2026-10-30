# Help make the original game feel good under your fingers

Fork this project and experiment. We welcome original UI improvements, accessibility fixes, lessons, platform work, documentation and reproducible bug reports. This is an independent prototype; upstream OpenTTD is a separate project.

## Keep the engine honest

1. Inspect the affected original code and current behaviour.
2. Keep gameplay rules in the original C++ engine. Use its validated commands.
3. Put original UI changes in a small, reviewable patch in `patches/`.
4. Verify the source tree with `python3 script/prepare_upstream.py`.
5. Run the nearest relevant build/check, then play the affected flow.
6. Explain what you observed and what you could not test.

Please do not claim multiplayer, save, NewGRF or performance compatibility from compilation alone. Back up saves before testing. Use a simulator owned by your project for automation, and keep personal saves, device IDs, signing identities and credentials out of commits.

## First contributions

- Try the first-route lesson as a new player and report where you got stuck.
- Improve a clipped or awkward original window on a small screen.
- Add accessible descriptions using actual original widget layout.
- Reproduce a compatibility issue with content you may redistribute.
- Add another GameScript lesson without automating the player's purchases or orders.

Use an issue with reproduction steps, platform/version and expected/actual behaviour. Attach only screenshots or saves you intend to make public. For a pull request, describe the change, its original-engine boundary and the checks you ran.

## Licence and attribution

Contributions must be GPL-2.0-compatible and preserve relevant upstream and third-party notices. By submitting a contribution, you license your contribution under GPL-2.0 unless a file clearly carries a compatible component licence. No separate CLA is required. Do not contribute proprietary Transport Tycoon assets, copied third-party NewGRFs without permission, credentials, or generated claims presented as test evidence.

AI-assisted contributions are welcome with the same review and evidence standards. Disclose substantial assistance; the human author remains responsible for the contribution.
