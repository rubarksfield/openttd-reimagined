# Encryption review facts for OpenTTD Reimagined 0.1.0 (5)

Status: Apple accepted the upload and processed build 5. Its TestFlight status is **Missing Compliance**. No export exemption or classification is claimed by this document. The technical choice in Apple’s wizard was inspected but has not been submitted as a completed declaration.

## Verified implementation

- The primary application is an offline-capable transport simulation using original OpenTTD 15.3 C++. Networking is an optional original feature.
- Original `src/network/network_crypto.cpp:110` calls `crypto_aead_init_x`. The bundled Monocypher implementation uses extended-nonce XChaCha20/Poly1305, not only the 96-bit-nonce ChaCha20 form. Original `network_crypto_internal.h` defines a 24-byte nonce and 32-byte X25519 keys.
- Original authentication supports X25519 key exchange, password-authenticated key agreement and authorized keys. Review the complete original protocol and bundled Monocypher source, not just cipher names.
- Original `network_crypto.cpp:126` and `:131` decrypt/encrypt packet data. This is implemented in bundled C/C++ code; it is not solely Apple operating-system encryption.
- The implementation and complete original source/dependencies are preserved. No claim that the app contains no encryption is accurate.

## Review required

Confirm US export classification/exemptions and any reporting obligations, and French import requirements for the intended availability. Do not tick “None” or add `ITSAppUsesNonExemptEncryption=NO` merely to clear the build. That key is appropriate only after a supported exemption determination.

The IETF record for XChaCha is an expired Internet-Draft with no formal standing in the standards process. This complicates an unqualified “standard algorithms only” answer; the published protocol/algorithm and the precise export-law definition need review. It does not establish that the cipher is unsafe or that this game necessarily needs a particular licence.

Apple’s inspected wizard requests export documentation when its bundled-standard-algorithm option and France availability are selected. That is an observed UI result, not a final legal determination. No country has been excluded to bypass it. No agency filing or specialist outreach has been sent.

## Primary references

- [Original network crypto](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/network/network_crypto.cpp)
- [Original crypto types and nonce lengths](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/network/network_crypto_internal.h)
- [XChaCha document status](https://datatracker.ietf.org/doc/draft-irtf-cfrg-xchacha/)
- [Apple export compliance](https://developer.apple.com/help/app-store-connect/manage-app-information/overview-of-export-compliance/)
- [Apple documentation process](https://developer.apple.com/help/app-store-connect/manage-app-information/determine-and-upload-app-encryption-documentation/)
- [Apple Info.plist guidance](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations)

This technical packet does not certify an export classification, submit regulatory documents, replace the GPL/store-terms review, or authorize a change to the account’s trader status.
