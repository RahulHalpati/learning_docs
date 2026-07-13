# 07 · Loops

> **Level:** Beginner · **Prerequisites:** [06 · Control flow](06_control_flow.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Computers shine at repetition. **Loops** let you run the same code many times — over every item in a list, until a goal is reached, ten thousand times without blinking. This is where programs start to feel powerful.

## Concept: the `for` loop

- **What:** a `for` loop runs its body once for each item in a sequence.
- **Why:** "do this for every X" is one of the most common things in programming.

```python
for fruit in ["apple", "pear", "plum"]:
    print(f"I like {fruit}")
```

Output:

```text
I like apple
I like pear
I like plum
```

Read it as: *"for each `fruit` in this list, run the body."* The variable `fruit` takes each value in turn. We cover lists fully in Section 02; for now, a `[...]` list is just "several values in order."

## Concept: `range()`

To loop a specific number of times, use `range()`:

```python
for i in range(5):          # 0, 1, 2, 3, 4  (starts at 0, stops BEFORE 5)
    print(i, end=" ")
print()

for i in range(1, 6):       # 1, 2, 3, 4, 5  (start, stop)
    print(i, end=" ")
print()

for i in range(0, 10, 2):   # 0, 2, 4, 6, 8  (start, stop, step)
    print(i, end=" ")
print()
```

Output:

```text
0 1 2 3 4 
1 2 3 4 5 
0 2 4 6 8 
```

- `range(n)` → `0` up to **but not including** `n`.
- `range(start, stop)` and `range(start, stop, step)` give you control.
- Like slicing, the stop is **exclusive** — `range(1, 6)` ends at `5`.

## Concept: accumulating a result

A loop often builds up an answer in a variable declared *before* the loop:

```python
total = 0
for i in range(1, 6):       # 1..5
    total += i              # add each number to the running total
print("sum 1..5 =", total)
```

Output (verified):

```text
sum 1..5 = 15
```

This "initialise outside, update inside" pattern (a running total, a counter, a longest-so-far) appears constantly.

## Concept: the `while` loop

- **What:** repeat *as long as* a condition stays `True`.
- **Why:** use it when you don't know in advance how many iterations you need — "keep going until X."

```python
n = 1
count = 0
while n < 100:
    n *= 2          # double n
    count += 1      # count how many doublings
print(f"{count} doublings to reach {n}")
```

Output (verified):

```text
7 doublings to reach 128
```

> ⚠️ **Infinite loops:** a `while` whose condition never becomes `False` runs forever. Make sure something inside the body moves you toward the exit (here, `n` grows). If you get stuck in one, press **Ctrl-C** to interrupt.

### `for` vs `while` — which to use?

- Known set of items or a fixed count → **`for`** (cleaner, no manual counter).
- "Until some condition" with an unknown number of steps → **`while`**.

## Concept: `break` and `continue`

- `break` exits the loop immediately.
- `continue` skips the rest of *this* iteration and moves to the next.

```python
for i in range(10):
    if i == 3:
        continue        # skip printing 3
    if i == 6:
        break           # stop entirely at 6
    print(i, end=" ")
print()
```

Output (verified):

```text
0 1 2 4 5 
```

`3` is skipped (`continue`), and the loop stops before `6` (`break`), so `6`–`9` never print.

## Concept: looping with an index — `enumerate`

When you need both the position and the value, `enumerate` beats a manual counter:

```python
for index, fruit in enumerate(["apple", "pear", "plum"]):
    print(f"{index}: {fruit}")
```

Output:

```text
0: apple
1: pear
2: plum
```

> 🧠 **Avoid** `for i in range(len(items)): items[i]`. It's clunky and error-prone. Loop the items directly, or use `enumerate` when you also need the index.

## Concept: `else` on a loop (Python's quirky bonus)

A loop can have an `else` that runs **only if the loop finished without hitting `break`**. It's perfect for search-and-report:

```python
target = 7
for n in [2, 4, 6, 8]:
    if n == target:
        print("found it")
        break
else:
    print("not found")     # runs because no break happened
```

Output:

```text
not found
```

This reads awkwardly at first; just remember *"else = the loop completed without breaking."*

## Worked example: a number-guessing checker

A small loop that scores guesses against a secret. (No `input()` here so it's reproducible.)

```python
# guess.py — report how each guess relates to the secret.

secret = 42
guesses = [10, 60, 42, 99]

attempts = 0
for guess in guesses:
    attempts += 1
    if guess == secret:
        print(f"Attempt {attempts}: {guess} -> correct! 🎉")
        break
    elif guess < secret:
        print(f"Attempt {attempts}: {guess} -> too low")
    else:
        print(f"Attempt {attempts}: {guess} -> too high")
else:
    print("Ran out of guesses.")
```

Output (verified):

```text
Attempt 1: 10 -> too low
Attempt 2: 60 -> too high
Attempt 3: 42 -> correct! 🎉
```

The loop `break`s on the correct guess, so the `else` ("ran out") doesn't run.

## Common mistakes

**Mistake: an accidental infinite loop**
```python
n = 5
while n > 0:
    print(n)       # n never changes -> prints 5 forever
```
**Why:** nothing decreases `n`. Add `n -= 1` in the body. (Press Ctrl-C to escape a runaway loop.)

**Mistake: modifying a list while looping over it**
```python
nums = [1, 2, 3, 4]
for x in nums:
    if x % 2 == 0:
        nums.remove(x)     # changing the list mid-iteration skips items!
print(nums)                # [1, 3] here, but the logic is fragile
```
**Why:** removing items shifts indices under the loop. Instead, build a *new* list (a comprehension — Section 02) or iterate over a copy (`for x in nums[:]`).

**Mistake: off-by-one with `range`**
```python
for i in range(1, 5):   # 1,2,3,4 — NOT 5
    print(i)
```
**Why:** stop is exclusive. To include 5, write `range(1, 6)`.

## Practice

**Exercise:** Print the [FizzBuzz](https://en.wikipedia.org/wiki/Fizz_buzz) sequence for 1–15: print `"Fizz"` for multiples of 3, `"Buzz"` for multiples of 5, `"FizzBuzz"` for multiples of both, otherwise the number.

*Hint:* check the "both" case first.

<details><summary>Solution</summary>

```python
for n in range(1, 16):
    if n % 15 == 0:          # multiple of both 3 and 5
        print("FizzBuzz")
    elif n % 3 == 0:
        print("Fizz")
    elif n % 5 == 0:
        print("Buzz")
    else:
        print(n)
```

Output:

```text
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

Checking `n % 15 == 0` first handles the "both" case before the individual ones can claim it.
</details>

## Recap & next

- ✅ Looped over items with `for`, and a fixed count with `range()`.
- ✅ Repeated until a condition with `while` (and how to avoid infinite loops).
- ✅ Controlled flow inside loops with `break` and `continue`.
- ✅ Got index + value cleanly with `enumerate`.
- ✅ Met the loop `else` clause.
- Self-check: write a loop that sums only the even numbers from 1 to 10.

🎉 **You've finished Section 01.** You can now write real, interactive, branching, repeating programs.

→ Next: **[Section 02 · Data structures](../02_data_structures/README.md)**
