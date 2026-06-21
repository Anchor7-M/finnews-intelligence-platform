# Source Policy

Milestone 0 uses local synthetic fixtures only. No live URL fetching is implemented.

Future priority:

1. User-supplied JSON/CSV exports.
2. Publisher RSS/Atom feeds after terms review.
3. Official exchange, regulator, or company announcement feeds/APIs after terms review.
4. No-key public research metadata sources when terms and limits permit use.

Future source configs must include source name, type, base URL, terms URL, enabled flag defaulting false, content-storage policy, timeout, maximum response size, bounded retries, rate limit, user agent, and provenance requirements.

Do not implement paywall bypass, login/CAPTCHA bypass, search-result scraping, undocumented endpoints, aggressive crawling, full-text republication, paid News API plans, or paid model APIs.
