// GPL-2.0: Update only a recognised bundled title scene, preserving custom files.
#pragma once
#import <Foundation/Foundation.h>
BOOL InstallClassicMenuIfUnmodified(NSURL *bundleData, NSURL *root, NSError **error);
