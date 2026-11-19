# (text, pause_after, speed, gain_db)
# Facts checked (Nov 2026) against Britannica ("Great Molasses Flood") and Smithsonian Magazine ("Why the Boston
# Molasses Disaster Was So Deadly", 2016, citing historian Stephen Puleo and the 2016 Harvard fluid-dynamics study):
# 15 Jan 1919, ~12:30 pm, Commercial Street, North End waterfront; tank 50+ ft tall, 90 ft wide, built hastily in 1915,
# leaked and rumbled from the start; owners repainted it brown to hide the leaks (Puleo); 2.3 million gallons released;
# wave reported 15-40 ft high, ~35 mph; 21 dead, ~150 injured; cold air thickened the molasses (>=4x viscosity),
# hampering rescue; USIA blamed anarchist sabotage, a 1925 ruling found the tank unsound; city reportedly smelled of
# molasses for years. Rivets "like gunfire" and the bent elevated-railway girders are witness/press accounts -> hedged.
PHRASES = [
    ("January, nineteen nineteen. Boston, just after noon.", 0.3, 0.93, 0),
    ("By the harbour stands a giant steel tank...", 0.15, 0.96, 0),
    ("fifty feet tall, holding over two million gallons", 0.15, 0.96, 0),
    ("of molasses.", 0.5, 0.86, -1.0),
    ("It has leaked since the day it was built.", 0.25, 0.95, 0),
    ("So the owners painted it brown... to hide the streaks.", 0.55, 0.9, -0.5),
    ("Witnesses hear rivets popping like gunfire.", 0.2, 1.0, 0.5),
    ("The tank tears open.", 0.5, 0.9, 1.0),
    ("A wave of syrup, reportedly up to forty feet high,", 0.15, 0.98, 0.5),
    ("rolls through the streets at thirty-five miles an hour.", 0.25, 1.0, 0.5),
    ("It crushes buildings and bends an elevated railway.", 0.35, 0.98, 0),
    ("Twenty-one people never come home.", 0.55, 0.85, -1.5),
    ("In the freezing air, it sets like glue around the rescuers.", 0.35, 0.96, 0),
    ("The company blamed saboteurs. A court blamed the tank.", 0.4, 0.97, 0),
    ("For years, locals said the streets still smelled sweet.", 0.45, 0.88, -1.0),
    ("So tell me...", 0.3, 0.9, -0.5),
    ("could you outrun a wave of syrup?", 0.9, 0.88, -1.0),
]
