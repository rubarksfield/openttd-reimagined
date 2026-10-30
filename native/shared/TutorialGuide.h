// GPL-2.0. Original OpenTTD widgets, independent of platform frameworks.
#pragma once
#include <string>
#include <functional>
#include "gfx_type.h"
void ShowFirstRouteGuide(const std::string &guide_path);
void VisitFirstRouteGuideText(const std::function<void(const Rect &,const std::string &)> &visitor);
