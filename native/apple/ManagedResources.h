// GPL-2.0: Update only a recognised bundled title scene, preserving custom files.
#pragma once
#import <Foundation/Foundation.h>
BOOL InstallClassicMenuIfUnmodified(NSURL *bundleData, NSURL *root, NSError **error);
// Preserve modified scripts, saves and unrelated content when updating coaching.
BOOL InstallTutorialIfUnmodified(NSURL *bundleData, NSURL *root, NSError **error);
