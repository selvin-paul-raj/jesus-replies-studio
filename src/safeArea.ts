/**
 * ============================================================================
 * CHARACTER-SAFE AREA -- measured from the actual background art
 * ============================================================================
 * Measured directly from public/backgrounds/boy/boy_1.png (941x1672): scanning
 * every column for the first non-sky pixel, the topmost point across both
 * the boy and Jesus is Jesus's hairline at y=927 (55.4% down the image) --
 * see CHARACTER_TOP_PERCENT below.
 *
 * The image's aspect ratio (941/1672) matches the video frame's (1080/1920)
 * to within 0.06%, so with <Img objectFit="cover"> that percentage carries
 * over almost exactly to the rendered frame/thumbnail -- no per-render
 * re-measurement needed.
 *
 * Being technically clear of that line isn't the goal -- composition is:
 * text should read as floating in the empty sky, with visible breathing
 * room before the characters, not stuck to the top of their heads. So
 * SAFE_LINE_PERCENT sits well above CHARACTER_TOP_PERCENT (not just a
 * couple of percent), leaving a deliberate visual gap.
 *
 * Every text block reads its growth ceiling from these constants instead of
 * a hand-picked topPercent, so any script's dialogue/verse/title -- however
 * long -- structurally stops short of the characters with room to spare. If
 * the background art ever changes, re-run the scan and update
 * CHARACTER_TOP_PERCENT/SAFE_LINE_PERCENT; nothing else needs to change.
 * ============================================================================
 */

/** Where the characters actually start (measured, see above). Not used as a
 * layout boundary directly -- SAFE_LINE_PERCENT below is deliberately well
 * clear of it -- kept here so the gap is visible/documented and easy to
 * re-check after any background-art change. */
export const CHARACTER_TOP_PERCENT = 55.4;

/** The dialogue/reflection/reference floor: their fixed edge pins here and
 * they only grow up (away from characters), giving a ~13% visual gap above
 * CHARACTER_TOP_PERCENT -- enough for the text to read as floating in the
 * sky rather than sitting on the characters' heads. */
export const SAFE_LINE_PERCENT = 42;

/** Breathing room every bottom-anchored text block keeps from the very top
 * of the frame -- this is the ceiling for how far a long line may grow up. */
export const TOP_MARGIN_PERCENT = 9;

/** Vertical room reserved below top-anchored content (the verse quote) for
 * the one-line reference/citation that sits under it. */
const CONTENT_RESERVE_BELOW_PERCENT = 5;

/** Ceiling for anything that grows *down* from a fixed top edge (the verse
 * quote, the thumbnail title) -- stops short of SAFE_LINE_PERCENT to leave
 * room for whatever sits just below it. */
export const SAFE_CONTENT_BOTTOM_PERCENT = SAFE_LINE_PERCENT - CONTENT_RESERVE_BELOW_PERCENT;

/** The verse quote's own fixed top edge -- its own region in the upper sky,
 * distinct from where dialogue sits, growing down toward
 * SAFE_CONTENT_BOTTOM_PERCENT for longer verses. */
export const VERSE_TOP_PERCENT = 14;
