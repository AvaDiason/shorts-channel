# (text, pause_after, speed, gain_db)
# Facts checked against Smithsonian Magazine and History.com (Nov 2026): found 4-5 Dec 1872 by the Dei Gratia
# ~400 mi east of the Azores; ~6 months of food and water aboard; only lifeboat missing; crew belongings left;
# last log entry 25 Nov 1872 within sight of Santa Maria, Azores. Crew count differs between sources (7 vs 8),
# so the script avoids giving a total. Trailing rope is hedged ("it's said").
PHRASES = [
    ("December, eighteen seventy-two.", 0.3, 0.92, 0),
    ("A crew spots a ship drifting in the middle of the Atlantic...", 0.25, 0.94, 0),
    ("with no one at the wheel.", 0.5, 0.86, -0.5),
    ("They row over. They call out.", 0.4, 0.95, 0),
    ("Nothing.", 0.6, 0.85, -1.0),
    ("On board, there's six months of food and water.", 0.2, 0.97, 0),
    ("The crew's belongings, still in their quarters.", 0.3, 0.95, 0),
    ("But every single person is gone.", 0.45, 0.86, 1.0),
    ("The captain. His wife. Their two-year-old daughter. And the crew.", 0.45, 0.9, 0),
    ("The only lifeboat? Missing.", 0.35, 0.92, 0.5),
    ("A rope, it's said, trailed from the ship... into the sea.", 0.5, 0.9, 0),
    ("The last log entry was written ten days earlier, near the Azores...", 0.2, 0.95, 0),
    ("hundreds of miles away.", 0.3, 0.9, 0),
    ("It gave no hint of trouble.", 0.45, 0.88, 0),
    ("Not one of them was ever seen again.", 0.6, 0.86, 0.5),
    ("So tell me...", 0.3, 0.9, -0.5),
    ("what makes a whole family abandon a perfectly good ship?", 0.9, 0.88, -1.0),
]
