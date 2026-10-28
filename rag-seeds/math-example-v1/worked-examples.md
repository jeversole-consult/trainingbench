# Worked examples — common grade-school math word problem patterns

Five worked solutions demonstrating the strategy guide applied to
representative problem shapes. These examples are original (not
drawn from any benchmark dataset).

---

## Example 1 — Simple addition

**Problem:** A classroom has 18 markers and the teacher buys 24
more. How many markers are there now?

**Given:** 18 markers (starting), 24 markers (new)
**Asked:** total markers now
**Keyword:** "and ... more" → addition

**Steps:**
```
total = starting + new
total = 18 + 24
total = 42
```

**Answer:** 42 markers

---

## Example 2 — Multi-step subtraction then division

**Problem:** Maria has $50. She spends $14 on lunch and splits the
rest equally among her 3 nephews. How much does each nephew get?

**Given:** $50 starting, $14 spent, 3 nephews
**Asked:** amount per nephew
**Keywords:** "the rest" → subtraction; "splits ... equally among" → division

**Steps:**
```
remaining = starting - spent
remaining = 50 - 14 = 36

per nephew = remaining / count
per nephew = 36 / 3 = 12
```

**Answer:** $12 each

**Check:** 3 × $12 = $36. $36 + $14 = $50. ✓

---

## Example 3 — Rate × time with unit conversion

**Problem:** A train travels at 45 miles per hour. How far does it
go in 90 minutes?

**Given:** rate = 45 mph, time = 90 minutes
**Asked:** distance
**Keywords:** "per hour" (rate), "in 90 minutes" (time)

**Unit alert:** rate is per *hour* but time is in *minutes*.
Convert first.

**Steps:**
```
time_hours = 90 / 60 = 1.5

distance = rate × time
distance = 45 × 1.5 = 67.5
```

**Answer:** 67.5 miles

---

## Example 4 — Percent / fraction of a total

**Problem:** A survey of 200 people shows 35% prefer coffee. How
many people prefer coffee?

**Given:** total = 200, fraction = 35%
**Asked:** count who prefer coffee
**Keyword:** "35% of" → multiplication by 0.35

**Steps:**
```
preferring = total × fraction
preferring = 200 × 0.35
preferring = 70
```

**Answer:** 70 people

---

## Example 5 — Multi-step with intermediate quantity

**Problem:** Jordan works 5 days a week. He works 8 hours Monday
through Thursday but only 4 hours on Friday. His wage is $20 per
hour. How much does he earn in a week?

**Given:** 4 days × 8 hours, 1 day × 4 hours, $20/hour wage
**Asked:** weekly earnings
**Keywords:** multi-step — compute hours first, then dollars

**Steps:**
```
# Intermediate: total hours worked
regular_hours = 4 days × 8 hours = 32 hours
friday_hours = 1 × 4 = 4 hours
total_hours = 32 + 4 = 36 hours

# Final: earnings
earnings = total_hours × hourly_wage
earnings = 36 × $20 = $720
```

**Answer:** $720

**Check:** split a different way — $20 × 8 = $160/day for 4 days
= $640. $20 × 4 = $80 on Friday. $640 + $80 = $720. ✓

---

## Pattern summary

| Pattern | Signal | Operation |
|---|---|---|
| Combining quantities | "total", "altogether", "and" | addition |
| Taking away | "left", "remain", "spent" | subtraction |
| Equal groups | "per", "each", "× as many" | multiplication |
| Splitting equally | "shared equally", "per person" | division |
| Fraction / percent | "half of", "N% of" | multiplication by decimal |
| Multi-step | more than one of the above | sequence of operations with named intermediates |
