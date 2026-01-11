![1768121785650](image/ui-enhancements/1768121785650.png)# UI Enhancements Brainstorm

This document captures rationale and a prioritized list of UI enhancements to make the expert-matching experience feel premium, intentional, and outcome-focused.

## Rationale (what we are optimizing)

- Trust: Users need confidence that results are expert, current, and actionable.
- Speed to outcome: Reduce clicks to preferences, contact, and booking.
- Clarity: Expose name, role, practice, availability, and location up front.
- Differentiation: Avoid generic RAG UI patterns; feel like a premium talent concierge.

## Visual Direction

- Brand name: "SP / Expert Matcher" (already set) as the anchor.
- Tone: Confident, concierge-like, enterprise but friendly.
- Layout: Strong hero, focused search, and concise result cards.

## Typography (font choices)

- Title font: "Fraunces" or "IBM Plex Serif" for the hero and key headings.
- Body font: "IBM Plex Sans" or "Space Grotesk" for crisp readability.
- Numbers: "IBM Plex Mono" for availability rate and metadata to feel precise.
- Pairing rule: Serif for the brand and headings, sans for body and controls.

## Color System (make it memorable, not generic)

- Base background: warm off-white (#F7F4EE).
- Primary ink: deep graphite (#1D1E20).
- Accent: confident green (#1E7D5C) for availability and actions.
- Secondary accent: muted gold (#C6A86B) for emphasis and awards.
- Cards: soft sand (#FFF9EF) with subtle shadow.
- States:
  - Success: green (#1E7D5C)
  - Warning: amber (#C6902B)
  - Info: blue (#1F5E8A)

## Interaction and Clicks (reduce friction)

- Single search bar with smart chips (Location, Practice, Role, Availability).
- One-click "Book" button on each expert card.
- Secondary action: "Ask for intro" (email prefill).
- "Save expert" toggle for quick shortlist.
- Sticky right rail: "Shortlist (2)" with compare button.

## Result Cards (what to show first)

- Name (bold), Role (bold), Practice, Location.
- Availability as a clear meter (0.0 - 1.0) with label.
- Top 3 skills as pill tags.
- Booking URL as a prominent link.
- "Why this match" short line based on query intent.

## Search Guidance (messages and examples)

- Search placeholder: "Find an expert for sales, client meetings, or RFPs".
- Examples tailored to expert sourcing:
  - "Find a Palantir Foundry expert for a sales demo in Toulouse"
  - "Need a data architect for an AWS migration workshop"
  - "Find a senior AI expert for a client presentation next week"
- Empty state message: "No perfect match yet. Try a broader skill or location."

## Expert Profile View

- Profile header with name, role, practice, and location.
- Availability trend (if available) or current level only.
- Experience highlights as bullets with logos if possible.
- "Best for" section to set expectations (sales demo, RFP, interview).

## Navigation and Pages

- About page: "How we match you with the right expert".
  - Explain data source, freshness, and matching logic.
  - CTA: "Start a search".
- Contact page: "Need a fast intro?"
  - CTA buttons: "Request an expert" and "Book a call".
  - Include a short form for urgent requests.
- Footer: data usage, privacy, and update cadence.

## Microcopy (make it expert-first)

- "Expert Matcher" instead of "Chat with your data".
- "Find support" instead of "Ask a question".
- "Availability" instead of "Sollicitation".
- "Booking URL" label on links.
- "Top matches" instead of "Search results".

## Feature Ideas (next wave)

- Filters: Location, Practice, Role, Availability range, Seniority.
- Sort: Match score, Availability, Practice fit.
- Explainability: "Matched because: AWS + Airbus + Sales demo".
- Share: Generate a short expert profile link.
- Team mode: Build and share an expert shortlist.
