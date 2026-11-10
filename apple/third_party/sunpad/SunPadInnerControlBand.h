#pragma once

#include <algorithm>
#include <stddef.h>

// Layout rect in the view's own coordinate space. Callers pass scene bounds,
// safe-area insets, and reserved-region frames. Nothing here reads a screen
// or a fixed device size.
struct SunPadLayoutRect {
    double x;
    double y;
    double width;
    double height;
};

// Share of the safe scene height used for the inner-display control band.
// Tech Talk 111463 puts touch controls in the lower region. Two fifths is
// entirely below the vertical middle and matches the band a docked keyboard
// occupies, without a pixel size.
inline constexpr double kSunPadInnerControlBandFraction = 0.40;

inline double SunPadLayoutMaxX(const SunPadLayoutRect &rect) {
    return rect.x + rect.width;
}

inline double SunPadLayoutMaxY(const SunPadLayoutRect &rect) {
    return rect.y + rect.height;
}

inline bool SunPadLayoutRectsIntersect(const SunPadLayoutRect &a, const SunPadLayoutRect &b) {
    return a.width > 0.0 && a.height > 0.0 && b.width > 0.0 && b.height > 0.0 &&
           a.x < SunPadLayoutMaxX(b) && SunPadLayoutMaxX(a) > b.x &&
           a.y < SunPadLayoutMaxY(b) && SunPadLayoutMaxY(a) > b.y;
}

inline SunPadLayoutRect SunPadInsetLayoutRect(SunPadLayoutRect bounds,
                                              double left, double top,
                                              double right, double bottom) {
    return SunPadLayoutRect{
        bounds.x + left,
        bounds.y + top,
        std::max(0.0, bounds.width - left - right),
        std::max(0.0, bounds.height - top - bottom),
    };
}

inline SunPadLayoutRect SunPadBottomControlBand(SunPadLayoutRect safe) {
    double height = safe.height * kSunPadInnerControlBandFraction;
    return SunPadLayoutRect{safe.x, SunPadLayoutMaxY(safe) - height, safe.width, height};
}

// A horizontal fold (wider than tall) splits the scene. Keep the controls on
// the larger side of that hinge, preferring the side that still touches the
// bottom edge.
inline SunPadLayoutRect SunPadAvoidHorizontalDivision(SunPadLayoutRect band,
                                                     SunPadLayoutRect division) {
    if (!SunPadLayoutRectsIntersect(band, division))
        return band;
    double bandBottom = SunPadLayoutMaxY(band);
    double divisionTop = division.y;
    double divisionBottom = SunPadLayoutMaxY(division);
    double belowTop = std::max(band.y, divisionBottom);
    double belowHeight = std::max(0.0, bandBottom - belowTop);
    double aboveHeight = std::max(0.0, std::min(SunPadLayoutMaxY(band), divisionTop) - band.y);
    if (belowHeight >= 1.0 && belowHeight >= aboveHeight)
        return SunPadLayoutRect{band.x, belowTop, band.width, belowHeight};
    if (aboveHeight >= 1.0)
        return SunPadLayoutRect{band.x, divisionTop - aboveHeight, band.width, aboveHeight};
    if (belowHeight >= 1.0)
        return SunPadLayoutRect{band.x, belowTop, band.width, belowHeight};
    return band;
}

// A vertical fold is a strip through the scene. Keep the whole control group
// on the wider side so the group does not cover the hinge.
inline SunPadLayoutRect SunPadAvoidVerticalDivision(SunPadLayoutRect band,
                                                   SunPadLayoutRect division) {
    if (!SunPadLayoutRectsIntersect(band, division))
        return band;
    double leftWidth = std::max(0.0, std::min(SunPadLayoutMaxX(band), division.x) - band.x);
    double rightOrigin = std::max(band.x, SunPadLayoutMaxX(division));
    double rightWidth = std::max(0.0, SunPadLayoutMaxX(band) - rightOrigin);
    if (leftWidth >= rightWidth)
        return SunPadLayoutRect{band.x, band.y, leftWidth, band.height};
    return SunPadLayoutRect{rightOrigin, band.y, rightWidth, band.height};
}

inline SunPadLayoutRect SunPadAvoidOcclusion(SunPadLayoutRect band, SunPadLayoutRect occlusion) {
    if (!SunPadLayoutRectsIntersect(band, occlusion))
        return band;
    double overlapWidth = std::min(SunPadLayoutMaxX(band), SunPadLayoutMaxX(occlusion)) -
                          std::max(band.x, occlusion.x);
    if (overlapWidth >= band.width * 0.5) {
        double bandBottom = SunPadLayoutMaxY(band);
        double occlusionBottom = SunPadLayoutMaxY(occlusion);
        if (occlusionBottom < bandBottom) {
            double top = std::max(band.y, occlusionBottom);
            return SunPadLayoutRect{band.x, top, band.width, bandBottom - top};
        }
        double above = std::max(0.0, occlusion.y - band.y);
        if (above >= 1.0)
            return SunPadLayoutRect{band.x, band.y, band.width, above};
        return band;
    }
    double leftWidth = std::max(0.0, std::min(SunPadLayoutMaxX(band), occlusion.x) - band.x);
    double rightOrigin = std::max(band.x, SunPadLayoutMaxX(occlusion));
    double rightWidth = std::max(0.0, SunPadLayoutMaxX(band) - rightOrigin);
    if (leftWidth >= rightWidth)
        return SunPadLayoutRect{band.x, band.y, leftWidth, band.height};
    return SunPadLayoutRect{rightOrigin, band.y, rightWidth, band.height};
}

// Outer/cover scenes (any compact size class) keep the full safe rect, so the
// existing compact phone layout is unchanged. The inner/open display reports
// regular x regular; there the controls sit in the bottom band.
inline SunPadLayoutRect SunPadTouchControlArea(SunPadLayoutRect bounds,
                                              double insetLeft, double insetTop,
                                              double insetRight, double insetBottom,
                                              bool regularWidth, bool regularHeight,
                                              const SunPadLayoutRect *divisions, size_t divisionCount,
                                              const SunPadLayoutRect *occlusions, size_t occlusionCount) {
    SunPadLayoutRect safe = SunPadInsetLayoutRect(bounds, insetLeft, insetTop, insetRight, insetBottom);
    if (!regularWidth || !regularHeight)
        return safe;
    SunPadLayoutRect band = SunPadBottomControlBand(safe);
    for (size_t index = 0; index < divisionCount; ++index) {
        const SunPadLayoutRect &division = divisions[index];
        if (division.width <= 0.0 || division.height <= 0.0)
            continue;
        if (division.width >= division.height)
            band = SunPadAvoidHorizontalDivision(band, division);
        else
            band = SunPadAvoidVerticalDivision(band, division);
    }
    for (size_t index = 0; index < occlusionCount; ++index)
        band = SunPadAvoidOcclusion(band, occlusions[index]);
    return band;
}
