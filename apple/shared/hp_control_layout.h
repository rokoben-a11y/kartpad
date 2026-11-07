/* Versioned touch-layout geometry shared by later pad apps.
   Bindings, captions and keyboard fallbacks stay with each game.
   Playport is not a consumer of this policy. */
#ifndef HP_CONTROL_LAYOUT_H
#define HP_CONTROL_LAYOUT_H

#define HP_LAYOUT_POLICY_ID "pad-control-layout"
#define HP_LAYOUT_POLICY_VERSION 1
#define HP_LAYOUT_LARGE_MIN_WIDTH 700.0
#define HP_LAYOUT_LARGE_MIN_HEIGHT 500.0
#define HP_LAYOUT_MIN_TARGET 44.0

enum {
    HP_LAYOUT_COMPACT = 0,
    HP_LAYOUT_LARGE = 1
};

enum {
    HP_LAYOUT_MOVE = 0,
    HP_LAYOUT_LOOK,
    HP_LAYOUT_FIRE,
    HP_LAYOUT_ACTION,
    HP_LAYOUT_SWITCH,
    HP_LAYOUT_ZOOM,
    HP_LAYOUT_GRENADE,
    HP_LAYOUT_MELEE,
    HP_LAYOUT_RELOAD,
    HP_LAYOUT_CROUCH,
    HP_LAYOUT_JUMP,
    HP_LAYOUT_FLASH,
    HP_LAYOUT_NADE,
    HP_LAYOUT_SCORES,
    HP_LAYOUT_PAUSE,
    HP_LAYOUT_SLOT_COUNT
};

typedef struct hp_layout_box {
    double x, y, w, h;
} hp_layout_box;

typedef struct hp_layout_request {
    double safe_x, safe_y, safe_w, safe_h;
    double control_size; /* 0.70 .. 1.35 */
    int ring_spacing;    /* 0 compact gaps, 1 normal, 2 spread */
    int left_handed;
} hp_layout_request;

static inline int hp_layout_size_class(double safe_w, double safe_h)
{
    if (!(safe_w > 0.0 && safe_h > 0.0)) return HP_LAYOUT_COMPACT;
    if (safe_w >= HP_LAYOUT_LARGE_MIN_WIDTH && safe_h >= HP_LAYOUT_LARGE_MIN_HEIGHT) return HP_LAYOUT_LARGE;
    return HP_LAYOUT_COMPACT;
}

static inline int hp_layout_box_inside(const hp_layout_box *box, double x, double y, double w, double h)
{
    return box->w >= HP_LAYOUT_MIN_TARGET - 0.01 && box->h >= HP_LAYOUT_MIN_TARGET - 0.01 &&
           box->x >= x - 0.05 && box->y >= y - 0.05 &&
           box->x + box->w <= x + w + 0.05 && box->y + box->h <= y + h + 0.05;
}

static inline int hp_layout_boxes_overlap(const hp_layout_box *a, const hp_layout_box *b)
{
    double dx = a->x > b->x ? a->x - (b->x + b->w) : b->x - (a->x + a->w);
    double dy = a->y > b->y ? a->y - (b->y + b->h) : b->y - (a->y + a->h);
    return dx < -0.5 && dy < -0.5;
}

static inline void hp_layout_compute(const hp_layout_request *in, double fit, hp_layout_box *out)
{
    double safe_x = in->safe_x, safe_y = in->safe_y, safe_w = in->safe_w, safe_h = in->safe_h;
    int large = hp_layout_size_class(safe_w, safe_h) == HP_LAYOUT_LARGE;
    int wide = large && safe_w >= 1000.0;
    int spacing = in->ring_spacing;
    double control = in->control_size;
    double gaps[3] = {8.0, 12.0, 18.0};
    double size_factor, k, cap_w, cap_h, floor_k, stick, action, utility, fire, gap;
    double inset_floor, inset_cap, inset, left, right, pitch, row_over, bottom_inset, bottom;
    double mid_y, low_y, row_y, near_x, far_x, fire_x, fire_y, left_inner, safe_max_x;
    double centers[HP_LAYOUT_SLOT_COUNT][2];
    double dias[HP_LAYOUT_SLOT_COUNT];
    int mirror_slot[HP_LAYOUT_SLOT_COUNT];
    int i;
    if (spacing < 0) spacing = 0;
    if (spacing > 2) spacing = 2;
    if (!(control >= 0.7)) control = 0.7;
    if (control > 1.35) control = 1.35;
    if (!(fit > 0.0)) fit = 1.0;
    size_factor = (wide ? 1.10 : 1.0) * control * fit;
    cap_w = safe_w / 760.0;
    cap_h = (safe_h - 68.0) / 260.0;
    k = size_factor;
    if (cap_w < k) k = cap_w;
    if (cap_h < k) k = cap_h;
    floor_k = 0.65 * fit;
    if (k < floor_k) k = floor_k;
    stick = 144.0 * k;
    action = 52.0 * k;
    utility = 44.0 * k;
    fire = 72.0 * k;
    if (fit >= 1.0) {
        if (stick < 100.0) stick = 100.0;
        if (fire < 60.0) fire = 60.0;
    }
    if (stick < HP_LAYOUT_MIN_TARGET) stick = HP_LAYOUT_MIN_TARGET;
    if (action < HP_LAYOUT_MIN_TARGET) action = HP_LAYOUT_MIN_TARGET;
    if (utility < HP_LAYOUT_MIN_TARGET) utility = HP_LAYOUT_MIN_TARGET;
    if (fire < HP_LAYOUT_MIN_TARGET) fire = HP_LAYOUT_MIN_TARGET;
    gap = gaps[spacing] * k;
    if (fit >= 1.0 && gap < 8.0) gap = 8.0;
    if (gap < 4.0) gap = 4.0;
    inset_floor = (large ? 36.0 : 20.0) * k;
    if (inset_floor < 16.0) inset_floor = 16.0;
    inset_cap = 160.0 - stick / 2.0;
    inset = inset_cap < inset_floor ? inset_cap : inset_floor;
    left = safe_x + inset;
    right = safe_x + safe_w - inset;
    pitch = action + gap;
    row_over = pitch + action / 2.0 - stick / 2.0;
    if (row_over < 0.0) row_over = 0.0;
    bottom_inset = large ? (160.0 > 128.0 * k ? 160.0 : 128.0 * k)
                         : (20.0 > 32.0 * k ? 20.0 : 32.0 * k);
    bottom = safe_y + safe_h - bottom_inset - row_over;
    mid_y = bottom - stick / 2.0;
    low_y = mid_y + pitch;
    row_y = mid_y - pitch;
    near_x = right - stick - gap - action / 2.0;
    far_x = near_x - pitch;
    fire_x = right - stick / 2.0;
    fire_y = bottom - stick - gap - fire / 2.0;
    left_inner = left + stick + gap + action / 2.0;
    safe_max_x = safe_x + safe_w;
    centers[HP_LAYOUT_MOVE][0] = left + stick / 2.0;
    centers[HP_LAYOUT_MOVE][1] = bottom - stick / 2.0;
    centers[HP_LAYOUT_LOOK][0] = right - stick / 2.0;
    centers[HP_LAYOUT_LOOK][1] = centers[HP_LAYOUT_MOVE][1];
    centers[HP_LAYOUT_FIRE][0] = fire_x;
    centers[HP_LAYOUT_FIRE][1] = fire_y;
    centers[HP_LAYOUT_ACTION][0] = far_x;
    centers[HP_LAYOUT_ACTION][1] = mid_y;
    centers[HP_LAYOUT_SWITCH][0] = far_x;
    centers[HP_LAYOUT_SWITCH][1] = low_y;
    centers[HP_LAYOUT_ZOOM][0] = far_x;
    centers[HP_LAYOUT_ZOOM][1] = row_y;
    centers[HP_LAYOUT_GRENADE][0] = left + stick / 2.0;
    centers[HP_LAYOUT_GRENADE][1] = fire_y;
    centers[HP_LAYOUT_MELEE][0] = near_x;
    centers[HP_LAYOUT_MELEE][1] = mid_y;
    centers[HP_LAYOUT_RELOAD][0] = near_x;
    centers[HP_LAYOUT_RELOAD][1] = row_y;
    centers[HP_LAYOUT_CROUCH][0] = left_inner;
    centers[HP_LAYOUT_CROUCH][1] = low_y;
    centers[HP_LAYOUT_JUMP][0] = near_x;
    centers[HP_LAYOUT_JUMP][1] = low_y;
    centers[HP_LAYOUT_FLASH][0] = left_inner;
    centers[HP_LAYOUT_FLASH][1] = mid_y;
    centers[HP_LAYOUT_NADE][0] = left_inner;
    centers[HP_LAYOUT_NADE][1] = row_y;
    centers[HP_LAYOUT_SCORES][0] = safe_x + safe_w / 2.0 - utility / 2.0 - 6.0;
    centers[HP_LAYOUT_SCORES][1] = safe_y + utility / 2.0 + 12.0;
    centers[HP_LAYOUT_PAUSE][0] = safe_x + safe_w / 2.0 + utility / 2.0 + 6.0;
    centers[HP_LAYOUT_PAUSE][1] = centers[HP_LAYOUT_SCORES][1];
    dias[HP_LAYOUT_MOVE] = dias[HP_LAYOUT_LOOK] = stick;
    dias[HP_LAYOUT_FIRE] = fire;
    dias[HP_LAYOUT_SCORES] = dias[HP_LAYOUT_PAUSE] = utility;
    for (i = HP_LAYOUT_ACTION; i <= HP_LAYOUT_NADE; i++) dias[i] = action;
    for (i = 0; i < HP_LAYOUT_SLOT_COUNT; i++) mirror_slot[i] = i < HP_LAYOUT_SCORES;
    for (i = 0; i < HP_LAYOUT_SLOT_COUNT; i++) {
        double cx = centers[i][0];
        if (in->left_handed && mirror_slot[i]) cx = safe_x + safe_max_x - cx;
        out[i].w = out[i].h = dias[i];
        out[i].x = cx - dias[i] / 2.0;
        out[i].y = centers[i][1] - dias[i] / 2.0;
    }
}

static inline int hp_layout_fits(const hp_layout_request *in, const hp_layout_box *boxes)
{
    int i, j;
    for (i = 0; i < HP_LAYOUT_SLOT_COUNT; i++)
        if (!hp_layout_box_inside(&boxes[i], in->safe_x, in->safe_y, in->safe_w, in->safe_h)) return 0;
    for (i = 0; i < HP_LAYOUT_SLOT_COUNT; i++)
        for (j = i + 1; j < HP_LAYOUT_SLOT_COUNT; j++)
            if (hp_layout_boxes_overlap(&boxes[i], &boxes[j])) return 0;
    return 1;
}

static inline void hp_layout_clamp(const hp_layout_request *in, hp_layout_box *box)
{
    if (box->w > in->safe_w) box->w = in->safe_w;
    if (box->h > in->safe_h) box->h = in->safe_h;
    if (box->x < in->safe_x) box->x = in->safe_x;
    if (box->y < in->safe_y) box->y = in->safe_y;
    if (box->x + box->w > in->safe_x + in->safe_w) box->x = in->safe_x + in->safe_w - box->w;
    if (box->y + box->h > in->safe_y + in->safe_h) box->y = in->safe_y + in->safe_h - box->h;
}

/* Default frames for one safe rectangle. User nudges stay outside this function. */
static inline void hp_layout_frames(const hp_layout_request *in, hp_layout_box *out)
{
    double fit;
    int attempt, i;
    for (attempt = 0, fit = 1.0; attempt < 14; attempt++, fit *= 0.90) {
        hp_layout_compute(in, fit, out);
        if (hp_layout_fits(in, out)) return;
    }
    for (i = 0; i < HP_LAYOUT_SLOT_COUNT; i++) hp_layout_clamp(in, &out[i]);
}

#endif
