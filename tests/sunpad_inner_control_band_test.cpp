#include "SunPadInnerControlBand.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

static int gFailures = 0;

static bool near(double actual, double expected) {
    return std::fabs(actual - expected) < 1e-6;
}

static void expect(bool condition, const char *message) {
    if (condition)
        return;
    std::fprintf(stderr, "FAIL: %s\n", message);
    ++gFailures;
}

static void expect_rect(const char *label, SunPadLayoutRect actual,
                        double x, double y, double width, double height) {
    if (near(actual.x, x) && near(actual.y, y) &&
        near(actual.width, width) && near(actual.height, height))
        return;
    std::fprintf(stderr, "FAIL: %s got (%.4f, %.4f, %.4f, %.4f)\n",
                 label, actual.x, actual.y, actual.width, actual.height);
    ++gFailures;
}

int main() {
    SunPadLayoutRect square{0, 0, 1000, 1000};

    SunPadLayoutRect outer = SunPadTouchControlArea(
        square, 0, 0, 0, 0, false, false, nullptr, 0, nullptr, 0);
    expect_rect("compact cover screen uses the full safe rect", outer, 0, 0, 1000, 1000);

    SunPadLayoutRect portrait = SunPadTouchControlArea(
        square, 12, 20, 48, 34, false, true, nullptr, 0, nullptr, 0);
    expect_rect("portrait phone keeps each inset and the full safe height",
                portrait, 12, 20, 940, 946);

    SunPadLayoutRect inner = SunPadTouchControlArea(
        square, 0, 0, 0, 0, true, true, nullptr, 0, nullptr, 0);
    expect_rect("open inner display anchors a 40% band to the bottom",
                inner, 0, 600, 1000, 400);
    expect(inner.y > square.height * 0.5,
           "the inner band starts below the vertical middle");
    expect(near(SunPadLayoutMaxY(inner), square.height),
           "the inner band reaches the bottom edge");

    SunPadLayoutRect inset = SunPadTouchControlArea(
        square, 10, 20, 40, 34, true, true, nullptr, 0, nullptr, 0);
    double safeHeight = 1000 - 20 - 34;
    expect_rect("inner band honors asymmetric safe-area insets",
                inset, 10, 20 + safeHeight * 0.6, 950, safeHeight * 0.4);
    expect(near(SunPadLayoutMaxY(inset), 1000 - 34),
           "the home-indicator inset stays below the controls");

    SunPadLayoutRect upperFold{0, 480, 1000, 40};
    SunPadLayoutRect aboveKeyboard = SunPadTouchControlArea(
        square, 0, 0, 0, 0, true, true, &upperFold, 1, nullptr, 0);
    expect_rect("a fold above the keyboard band is left alone",
                aboveKeyboard, 0, 600, 1000, 400);
    expect(!SunPadLayoutRectsIntersect(aboveKeyboard, upperFold),
           "controls do not cover a fold above the band");

    SunPadLayoutRect lowFold{0, 700, 1000, 50};
    SunPadLayoutRect belowFold = SunPadTouchControlArea(
        square, 0, 0, 0, 0, true, true, &lowFold, 1, nullptr, 0);
    expect_rect("a horizontal fold keeps controls below the hinge",
                belowFold, 0, 750, 1000, 250);
    expect(!SunPadLayoutRectsIntersect(belowFold, lowFold),
           "controls do not cover a horizontal fold");

    SunPadLayoutRect bottomFold{0, 900, 1000, 80};
    SunPadLayoutRect aboveBottomFold = SunPadTouchControlArea(
        square, 0, 0, 0, 0, true, true, &bottomFold, 1, nullptr, 0);
    expect(!SunPadLayoutRectsIntersect(aboveBottomFold, bottomFold),
           "controls move above a hinge that covers the bottom edge");
    expect(SunPadLayoutMaxY(aboveBottomFold) <= bottomFold.y + 1e-6,
           "controls stay on the keyboard side of a bottom hinge");

    SunPadLayoutRect verticalFold{480, 0, 40, 1000};
    SunPadLayoutRect besideFold = SunPadTouchControlArea(
        square, 0, 0, 0, 0, true, true, &verticalFold, 1, nullptr, 0);
    expect_rect("a vertical fold keeps the group on the wider side",
                besideFold, 0, 600, 480, 400);
    expect(!SunPadLayoutRectsIntersect(besideFold, verticalFold),
           "controls do not cover a vertical fold");

    SunPadLayoutRect camera{900, 820, 80, 80};
    SunPadLayoutRect clearOfCamera = SunPadTouchControlArea(
        square, 0, 0, 0, 0, true, true, nullptr, 0, &camera, 1);
    expect_rect("a narrow camera occlusion keeps the wider side of the band",
                clearOfCamera, 0, 600, 900, 400);
    expect(!SunPadLayoutRectsIntersect(clearOfCamera, camera),
           "controls do not cover a camera occlusion");

    if (gFailures != 0) {
        std::fprintf(stderr, "%d failure(s)\n", gFailures);
        return EXIT_FAILURE;
    }
    std::puts("ok");
    return EXIT_SUCCESS;
}
