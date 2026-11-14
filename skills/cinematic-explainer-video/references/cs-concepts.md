# CS concept mode

For classic, surprising computer science ideas (TrueTime, attention, hashing, consensus, compression…). Pedagogy
ideas are adapted from [CourseToShortsSkills](https://github.com/arav31/CourseToShortsSkills) (ideas only),
[code-to-reels](https://github.com/BusyBee3333/code-to-reels) (MIT), [Code2Video](https://github.com/showlab/Code2Video)
(MIT) and [raft-visualizer](https://github.com/Raminshiraz/raft-visualizer) (the simulate-then-render pattern).

## 1. One short = one claim

Write a planning card in `PLAN.json` before anything else:

```json
{
  "slug": "bloom-filters", "series_part": "3/6",
  "title": "The filter that's allowed to lie",
  "hook": "How does a browser check a billion bad links without storing them?",
  "hook_type": "everyday-puzzle",
  "claim": "A Bloom filter answers 'definitely not' or 'maybe' by lighting a few bits per item.",
  "worked_example": {"setup": "16 lamps, 3 hashes; add cat, dog",
                     "steps": ["cat -> 2,7,11", "dog -> 4,7,13", "owl -> 2,4,13: all lit"],
                     "result": "owl is a false positive"},
  "key_moment": "owl's three lamps are already lit",
  "naive_first": "store every link in a list",
  "twist": "false positives; but one dark lamp is always a certain no",
  "scale": "about 10 bits per item for 1% false positives",
  "misconception": "it can never say yes for sure",
  "recurring_object": "a row of lamps",
  "plants": "next episode's question",
  "facts": ["f-0001", "f-0002"]
}
```

- **The claim is one sentence.** If it needs "and", it's two shorts.
- **The worked example is computed in code** (`checks/examples.py`), and the narration says the same numbers.
- **The key moment is the frame people would screenshot.** Build the film backwards from it.

## 2. Beat sheet (CS variant of the 7 beats, 60–80 s)

| Beat | ≈ s | Job | The world |
| --- | --- | --- | --- |
| 1 Hook | 0–4 | A specific gap on frame 0 | The hero object already lit; title line |
| 2 Stakes | 4–12 | A famous person, **or** a failure story, **or** an impossible number | Archive photo or document over a slowly moving world |
| 3 The naive way breaks | 12–22 | Show the obvious solution failing physically (hash mod N: add a server, every key moves) | Objects scatter; one colour flip |
| 4 Mechanism | 22–42 | Name the parts first, then run the worked example one step per phrase. Add one "predict" pause ("which lamp lights next?") | The recurring object; one operation per sentence |
| 5 Twist | 42–54 | The concept's **failure mode or trade-off**, re-run on the same object (false positive, split vote, collision) | The same object re-routes; amber marks the truth |
| 6 Scale | 54–63 | True numbers from the ledger; where it runs today | Camera pulls back to the field or rack wall |
| 7 Payoff + plant | 63–70 | Answer the hook in one line, return to frame 1's picture, plant the next episode's question | Matches frame 0 so the loop is seamless; hold 3–4 s |

## 3. Hook types that fit CS

Pick one per episode and vary them across a series. Check every fact before use.

| Type | Template | Example |
| --- | --- | --- |
| Everyday puzzle | "How does X do Y without Z?" | "How do two datacenters agree on time without one shared clock?" |
| Impossible number | "<number>. Here's how." | "In 1986, internet throughput fell a thousandfold overnight." |
| Failure story | "In <year>, <system> broke because…" | a leap-second outage; a missile clock drift |
| Wrong intuition | "You think X. Actually Y." | "Adding servers can make a cache worse." |
| Contradiction | "A <thing> that's allowed to <bad property>." | "A filter that's allowed to lie." |
| You used it today | "You used this N times before breakfast." | compression in every image you opened |
| Origin legend | "Designed in 20 minutes in a café." | Dijkstra's shortest path |

Give partial knowledge plus one precise gap, then **answer that exact question at the end**, out loud and in the
picture. No vague teases.

## 4. Simulate, then render the trace

For any algorithm (Raft, Dijkstra, TCP, GC, Bloom filters, LZ77), don't hand-animate the states:

1. Write a small, **seeded** simulator in Python or JS (`checks/sim.py`) that runs the real algorithm on the worked
   example and asserts its invariants (one leader per term, distances only decrease, no false negatives).
2. Export the state over time as JSON: `[{t, kind, ...state}]`, with `t` taken from word anchors in `timeline.json`.
3. Inject it into `world.html`. `render(t)` reads the latest event at or before `t` plus a `ramp()` for the
   transition. The picture then cannot disagree with the algorithm, and the numbers in the voice come from the same
   run.
4. Export `window.__world.events = [{t, kind}]`, so `check_film.py` and the critic can measure the time between
   meaningful changes (target ≤ 3 s on average, never more than 6 s).

**Every motion is an operation** (hash, compare, route, mark, evict). Camera drift, fog and LED blink are
atmosphere, not explanation. Encode state with brightness and thickness, and keep amber for the answer. Avoid
Manim-style rainbow state colours.

## 5. Visual vocabulary for the Three.js world

Each entry reuses template pieces: **panel** (glass panel, flip, tint), **thread** (tube, radius = weight),
**pulse** (wavefront disc), **field** (instanced thousands), **wall** (rack LEDs), **label/counter** sprites,
**floor** reflector. Numbers and history marked *verify* must be checked at the primary source first.

| Concept | Recurring object | Key moment | Twist (failure mode) | Scale beat |
| --- | --- | --- | --- | --- |
| TrueTime / Spanner | a hall of clocks, each with a glowing uncertainty band | two commits' bands overlap; the system waits the band out, then lights the second | widen the band (GPS drops out): every commit waits longer | ε of a few ms (*verify*, Corbett et al. OSDI 2012) |
| Attention | glass word panels + amber threads (thickness = weight) | "it" sends threads; the thickest lands on the right noun | change one word, threads re-route | layers × heads × tokens as the field |
| Consistent hashing | a ring of light on the floor; servers are pillars; keys are beads | a bead drops and slides clockwise to the first pillar | naive `mod N` first: add a server, every bead jumps; on the ring only one arc moves | virtual nodes split each pillar (*verify* Karger 1997) |
| Bloom filter | a row of dark lamps | "cat" passes through three hash prisms, three lamps light | "owl" finds its lamps already lit: a false "maybe"; one dark lamp is always a certain no | ~10 bits per item for 1% false positives |
| Raft | five pillars with countdown rings; the leader glows and pulses heartbeats | leader goes dark, rings count down at random speeds, first empty ring wins the vote | split vote 2–2: timers re-randomise | 150–300 ms timeouts (*verify*, Ongaro 2014) |
| Public-key / Diffie–Hellman | paint mixing: public yellow, each side adds a secret colour | both final colours match; the eavesdropper's pot is muddy | un-mixing is the hard part: a counter spinning through billions of tries | 1976 / RSA 1977 (*verify*) |
| TCP congestion control | a glowing pipe; the window is the number of packets allowed on it | the sawtooth: +1 per round trip, halve on loss; the camera pulls back to reveal it | slow start doubling; many flows converging to fair shares | the 1986 congestion collapse (*verify*, Jacobson 1988) |
| Garbage collection | objects hanging from root pillars by reference threads | a pulse marks everything reachable; the rest dissolves to dust | a cycle nobody reaches still dies (why reference counting leaks) | McCarthy, LISP, 1960 (*verify*) |
| Compression (LZ77) | a line of letter panels | a repeat becomes a thread pointing back; the sentence physically shrinks | random noise: no threads, the file even grows | behind ZIP, PNG, gzip |
| Hash table | a wall of numbered lockers; a hash prism | a key flies straight to locker #417, while a ghost key walks past every locker | collision: a chain grows; resize to a wall twice as big | O(1) average lookups |
| Merkle tree | a tree of sealed panels; the root seal glows | tamper with one leaf: the change climbs to the root, which turns red | prove one leaf with only log₂ n sibling hashes | Git, Bitcoin, certificate logs |
| Dijkstra | a city of lamp nodes and road threads; light floods from the source | a tentative label drops from 9 to 7 when a shorter road appears | a negative road breaks the greedy order | designed in ~20 min, 1956 (*verify*) |
| B-tree | a building of floors with wide sorted shelves; a lift | 3 floors to find one row among millions; counter "disk reads: 3" | a full shelf splits and pushes a key up | fan-out in the hundreds |
| Lamport clocks | three vertical light timelines with message threads | a message carrying 7 arrives at a process reading 3: it jumps to 8 | concurrent events get numbers that don't mean cause | Lamport 1978 |
| Byzantine generals | generals as pillars; a traitor's threads change colour mid-flight | with 3 generals the loyal ones can't tell who lied; with 4 they can | n ≥ 3f + 1 on a sliding counter | Lamport, Shostak, Pease 1982 |
| Floating point | a ruler whose ticks double their spacing each power of two | 0.1 lands between ticks and snaps; 0.1 + 0.2 lands on 0.30000000000000004 | accumulated drift in a timer (*verify* the Patriot GAO report) | ~15–17 significant digits |

## 6. Series

1. **Map the topic:** concepts, each with a one-line claim, its prerequisites and its visual mechanism. Drop
   anything without a strong mechanism.
2. **Order by prerequisites:** representations before operations, naive before clever, intuition before formalism.
3. **One idea per episode,** and each must stand alone for someone arriving from the feed.
4. **Thread it:** one shared world (hall, palette, accent meaning) across the series, a new recurring object per
   episode, and **each episode's last line plants the next one's question**. Callbacks reuse earlier objects (the
   hash prism returns in Bloom filters and consistent hashing).
5. **5–8 episodes per arc.** Examples:
   - *Time in distributed systems:* clocks drift → Lamport clocks → TrueTime → consistent hashing → Raft →
     Byzantine generals.
   - *How data gets small and fast:* hashing → hash tables → Bloom filters → B-trees → LZ77 → Huffman.
   - *Why the internet doesn't collapse:* packets → TCP handshake → 1986 collapse → the sawtooth → DNS → CDNs.
   - *Trust without meeting:* hash functions → Merkle trees → Diffie–Hellman paint → RSA padlocks → certificates.
6. **Title:** "<Series> · Part i/N: <title>". No two episodes share a worked example. Vary one knob per episode
   (camera language, fog colour, object shape) so it doesn't look templated.
