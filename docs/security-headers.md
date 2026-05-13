# Security headers for rivassec.com (Cloudflare Transform Rules)

Site is on GitHub Pages behind Cloudflare (per `CNAME`). GH Pages
does not let us set response headers directly, but Cloudflare
Transform Rules ("Modify Response Header") do. This doc captures
the canonical set of headers to paste into the Cloudflare dashboard.

As of the last audit (2026-05-13), the response carried **no**
security headers. securityheaders.com grade: F. Applying the set
below should take it to A.

## What to add

**Cloudflare dashboard path:** Rules -> Overview -> Transform Rules
-> Modify Response Header -> Create rule.

Create **one** rule named `rivassec.com security headers`, apply to
**All incoming requests**, and add these headers one by one (click
"Add Modification" for each). All are "Set static".

### 1. Strict-Transport-Security

- **Header:** `Strict-Transport-Security`
- **Value:** `max-age=63072000; includeSubDomains`

Declares HTTPS-only for 2 years. `includeSubDomains` is only safe
if every subdomain of rivassec.com supports HTTPS - confirm before
applying.

**`preload` is intentionally NOT included by default.** Submitting
to hstspreload.org is a one-way door: rollback takes weeks and the
domain (with subdomains) is hardcoded into every major browser.
Only add `preload` after:

1. Every subdomain of rivassec.com is HTTPS-only and will remain so.
2. The site has been running with the header above for at least a
   few weeks without HSTS-related incident reports.
3. You've read https://hstspreload.org/ and accept the commitment.

When ready, change the header value to
`max-age=63072000; includeSubDomains; preload` and submit at
https://hstspreload.org/.

### 2. Content-Security-Policy

- **Header:** `Content-Security-Policy`
- **Value:**

```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https://img.shields.io; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests
```

Rationale for each directive:

- `default-src 'self'`: block everything by default, only same-origin allowed
- `script-src 'self'`: our only JS is `/static/copy-code.js` - no inline scripts, no CDN
- `style-src 'self'`: audited 2026-05-13 - the rendered output contains zero `style="..."` attributes and zero `<style>` blocks. Flex ships all CSS via `<link>`; pygments code blocks use semantic classes (`class="highlight"`, `class="nt"`, etc.) styled from `/theme/pygments/monokai.min.css`. `'unsafe-inline'` is NOT needed.
- `img-src 'self' data: https://img.shields.io`: `data:` for any inline icons; shields.io for About page badges
- `font-src 'self'`: self-hosted Source Sans / Source Code Pro (PR #10)
- `object-src 'none'` + `frame-ancestors 'none'`: clickjacking prevention
- `upgrade-insecure-requests`: catch any accidental `http://` references

If the strict CSP breaks something, start in **report-only** mode:
change header name to `Content-Security-Policy-Report-Only` for a
week and watch the browser console / CF security events.

**Audit command to re-verify after theme changes:**

```bash
# If either of these prints anything, you need 'unsafe-inline' on
# style-src or you need to hoist the inline style into a stylesheet.
grep -rhE 'style="[^"]*"' output --include="*.html" | sort -u
grep -rl '<style' output --include="*.html"
```

### 3. X-Content-Type-Options

- **Header:** `X-Content-Type-Options`
- **Value:** `nosniff`

Blocks MIME-sniff attacks. No downside.

### 4. X-Frame-Options

- **Header:** `X-Frame-Options`
- **Value:** `DENY`

Belt-and-suspenders with the CSP `frame-ancestors 'none'` above.
Older browsers ignore CSP frame-ancestors; this covers them.

### 5. Referrer-Policy

- **Header:** `Referrer-Policy`
- **Value:** `strict-origin-when-cross-origin`

Sends the origin (not the path) on cross-origin requests, nothing
on HTTPS-to-HTTP downgrades, full referrer on same-origin. The
defaults-are-fine setting.

### 6. Permissions-Policy

- **Header:** `Permissions-Policy`
- **Value:** `accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()`

Denies access to device APIs this site never needs. Defensive
against hypothetical supply-chain script injection.

### 7. Cross-Origin-Opener-Policy

- **Header:** `Cross-Origin-Opener-Policy`
- **Value:** `same-origin`

Isolates the browsing context from cross-origin popups (Spectre
mitigation class).

## What NOT to add

- **`Expect-CT`**: deprecated since 2023. Chrome removed support.
- **`X-XSS-Protection`**: deprecated; modern browsers rely on CSP.
- **`Feature-Policy`**: renamed to Permissions-Policy (above).

## Verification

After adding the rule, re-test:

```bash
curl -sS https://rivassec.com/ -D - -o /dev/null | grep -iE "strict-transport|content-security|x-frame|x-content-type|referrer|permissions-policy|cross-origin"
```

Or paste the URL into https://securityheaders.com/.

## Rollout order (recommended)

1. Start with the zero-risk four: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`.
2. Then `Strict-Transport-Security` with `max-age=3600` for the first day to test; bump to 2 years once confirmed working.
3. Then `Content-Security-Policy` in **Report-Only** mode for a week; check Cloudflare Analytics -> Security Events for violations.
4. Flip CSP to enforcing mode.

If anything breaks, remove the offending header from the Transform
Rule; changes propagate in seconds.

## Why this doc lives in the repo

Headers are applied in the Cloudflare dashboard (out-of-band from
this repo), but the **policy decision** about which headers to use
and why belongs in version control alongside the rest of the site
config. If the CF account is lost, rebuilt, or handed off, this
doc is the authoritative source for what the site should carry.
