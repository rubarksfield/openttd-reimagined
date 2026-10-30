# Upstream work, assets and notices

This independent application links original OpenTTD 15.3 C++ code. The linked application and our modifications/tutorial are GPL-2.0; see COPYING.md. Original per-file notices remain authoritative. This project does not claim ownership of OpenTTD, its name or its contributors' work.

| Component | Version / source | Notice handling |
|---|---|---|
| OpenTTD | 15.3, official source archive | `script/prepare_upstream.py` pins the SHA-256, verifies every file and applies the reviewed UI patches; preserve COPYING and per-file notices |
| Original bundled libraries | OpenTTD's exact `src/3rdparty` tree, including modified Squirrel, fmt, nlohmann JSON and crypto | Preserve upstream component notices; they are not all GPL-2.0 |
| XZ / liblzma | 5.8.1, official release | Pinned archive in `prepare_ipad_sources.py`; preserve COPYING, COPYING.0BSD and applicable file notices |
| libarchive | 3.8.10, official release | Pinned archive in `prepare_archive.py`; COPYING is bundled in GameData/licenses |
| zlib | Apple target SDK library | System linkage; its own licence applies |
| OpenGFX | 8.0, official free graphics | Downloaded by `prepare_graphics.py`; preserve the package's GPL notices and corresponding source obligations |
| OpenSFX | 1.0.3, official free effects | Downloaded by `prepare_sound.py`; preserve every package licence, sound attribution and share-alike obligation |
| Classic opening save | Official OpenTTD 16.0-beta5 title scene | Exact hash and origin in `native/apple/ClassicMenu/origin.json`; GPL-2.0; editable save data, no proprietary graphics included |
| First Route | Project-authored original-editor scenario and GameScript | GPL-2.0; source scenario and script are included |
| Train app icon | Project AI-generated artwork | Released with this project under GPL-2.0 |

The build obtains external source/assets from their official upstream URLs. It does not download proprietary Transport Tycoon Deluxe graphics, music or sounds. Imported community content retains its own licence; private import does not grant redistribution rights.

Before distributing a binary, assemble complete corresponding source, modifications, build scripts, exact linked dependency sources and asset notices/source as required. A GitHub source snapshot that omits upstream/dependency source is not by itself the complete corresponding-source bundle for the linked executable. No App Store/TestFlight release is claimed by this source publication. Apple terms, interpreted community scripts and branding require review before those channels are accepted.

Screenshots use the free OpenGFX graphics and OpenSFX effects. OpenTTD's content creation guidance: https://www.openttd.org/content-creators .
