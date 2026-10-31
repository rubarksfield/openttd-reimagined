// GPL-2.0. Original OpenTTD widgets, independent of platform frameworks.
#pragma once
#include <string>
#include <functional>
#include "gfx_type.h"
void ShowFirstRouteGuide(const std::string &guide_path);
void VisitFirstRouteGuideText(const std::function<void(const Rect &,const std::string &)> &visitor);

// Presentation-only target from this lesson's original Story Book location.
#include "tile_type.h"
void RefreshFirstRouteTarget();
TileIndex FirstRouteTargetTile();
void FocusFirstRouteTarget(TileIndex tile);
std::string_view FirstRouteTargetLabel();
