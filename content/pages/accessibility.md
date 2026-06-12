Title: Accessibility
Slug: accessibility
URL: accessibility/
Save_as: accessibility/index.html
Author: RivasSec
Summary: Accessibility statement for rivassec.com: target conformance, known limitations, and how to report issues.

This site targets [WCAG 2.1 Level AA](https://www.w3.org/WAI/WCAG21/quickref/) conformance.

## Target conformance

`rivassec.com` is built and maintained as a personal blog by one person. I aim for WCAG 2.1 Level AA across all published posts. I do not claim full conformance; the site is reviewed continuously rather than certified.

## What is in place

- Alt text on all informational images, enforced at commit time by a script that fails CI on any image missing an alt attribute.
- Color contrast targeting WCAG AA (4.5:1 for normal text, 3:1 for large text), verified with Pa11y running axe-core and HTML CodeSniffer against representative pages on every push.
- Semantic heading order (`h1` → `h2` → `h3`) without skips.
- Link distinguishability beyond color (underlines on hero and footer links).
- Open Graph and Twitter card alt text on social previews.
- ASCII diagrams wrapped in `figure` elements with descriptive `aria-label` and `figcaption` so screen readers receive a prose summary instead of character-by-character output.

## Known limitations

- The hero gradient on article headers can produce ambiguous contrast measurements in automated scanners, even when the underlying contrast is adequate. White text on the gradient is well above WCAG AA across all gradient stops.
- Embedded third-party content (badge images from `img.shields.io`, etc.) inherits the alt text those services provide. Where I can override, I do; where I cannot, the upstream alt text applies.

## Tooling

- The accessibility CI workflow lives at [`.github/workflows/a11y-check.yml`](https://github.com/rivassec/devsecops-notes/blob/main/.github/workflows/a11y-check.yml) and runs Pa11y CI against the built site on every push and pull request.
- The image alt-text check lives at [`.github/workflows/image-alt-check.yml`](https://github.com/rivassec/devsecops-notes/blob/main/.github/workflows/image-alt-check.yml) and is enforced as a blocking check.
- The full site source is open at [`rivassec/devsecops-notes`](https://github.com/rivassec/devsecops-notes).

## Reporting an issue

If you encounter content that is hard to use with assistive technology, or if anything on the site fails to meet WCAG 2.1 AA in practice, please open an issue at [`rivassec/devsecops-notes/issues`](https://github.com/rivassec/devsecops-notes/issues) or email `oliver@rivassec.com`.

I aim to respond to reported accessibility issues within seven days. Fixes ship the same way every other change to the site does: a commit on the public main branch.

## Last reviewed

2026-06-12.
