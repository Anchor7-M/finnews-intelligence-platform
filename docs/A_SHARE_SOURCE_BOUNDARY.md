# A-Share Source Boundary

Milestone 1B does not scrape Shanghai Stock Exchange, Shenzhen Stock Exchange,
CNINFO, CSRC, PBOC, or other A-share websites.

Network integration for A-share sources requires a future engineering review of
an official documented feed or API, acceptable automated-use evidence, clear
rate limits, storage permissions, and a source-review record. This project does
not perform undocumented endpoint discovery, search-result scraping, browser
automation, login bypass, CAPTCHA bypass, paywall bypass, or linked-page
scraping.

The current safe A-share path is user-supplied JSON or CSV announcement import
through the local import adapters. Those imports remain metadata-only and use
synthetic or user-provided records rather than copied live announcements.

This boundary is an engineering policy for this repository and is not legal
advice. A future task may review specific official A-share sources if the user
provides or authorizes official documentation and usage-policy evidence.
