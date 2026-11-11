# NammaMove landing prototype

An independently editable, local-only marketing design. No deployment, new dependencies, API integration, analytics, credentials, or location access. Synthetic journeys are visibly labelled. This does not advance production acceptance.

From the repository root, run `node apps/landing/server.mjs`, then open http://127.0.0.1:4173. Override the port with `LANDING_PORT` if necessary. The server serves only this directory, rejects hidden paths, and binds to loopback.

- [index.html](index.html): copy, sections and schematic map.
- [styles.css](styles.css): responsive layout and brand tokens.
- [app.js](app.js): local journey choices, direction swap and mobile navigation.
- [assets](assets): unchanged motion and liquid-type modules from the installed taste skill.

Edit the files and refresh the preview. Route times and stop names are independently authored fictional UI content, not routing results. The street map is an authored schematic, not licensed geographic data. There are no stock photos, testimonials, waitlist submissions, fares or app store claims. Fonts load from Google Fonts with local system fallbacks. No mobile environment variables are read or served.
