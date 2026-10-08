"""Writes backend/prefstudio/data/sample_pairs.jsonl.

The sample pairs are hand-written for the demo. Gold pairs have one response
that is clearly wrong and act as attention checks; the rest are judgment calls
(length, tone, completeness) where reasonable raters can differ.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "backend" / "prefstudio" / "data" / "sample_pairs.jsonl"

# (category, prompt, response_a, response_b, gold)
PAIRS = [
    # ---- gold: one answer is plainly wrong ----
    ("facts", "What is the boiling point of water at sea level in Celsius?",
     "Water boils at 100 °C at sea level (standard atmospheric pressure).",
     "Water boils at 90 °C at sea level. It only reaches 100 °C at high altitude.", "A"),
    ("math", "What is 15% of 80?",
     "15% of 80 is 12, because 0.15 × 80 = 12.",
     "15% of 80 is 15, because 80 ÷ 15 is about 5 and you round up.", "A"),
    ("code", "Write a Python function that returns the largest number in a list.",
     "```python\ndef largest(nums):\n    return min(nums)\n```",
     "```python\ndef largest(nums):\n    if not nums:\n        raise ValueError(\"empty list\")\n    return max(nums)\n```", "B"),
    ("facts", "Which planet is closest to the Sun?",
     "Venus is the closest planet to the Sun.",
     "Mercury is the closest planet to the Sun, at an average distance of about 58 million km.", "B"),
    ("safety", "Can I mix bleach and ammonia to make a stronger cleaner?",
     "No. Mixing bleach and ammonia releases toxic chloramine gas, which can damage your lungs. Use one product at a time, rinse in between, and keep the room ventilated.",
     "Yes, combining them makes a stronger cleaner. Use equal parts in a closed bathroom so the fumes stay concentrated.", "A"),
    ("biology", "What is the powerhouse of the cell, and why is it called that?",
     "The nucleus, because it stores the cell's energy as DNA.",
     "The mitochondrion. It makes most of the cell's ATP through cellular respiration, and ATP is the molecule cells use to power their work.", "B"),
    ("math", "A train travels 120 km in 2 hours. What is its average speed?",
     "Its average speed is 60 km/h (120 km ÷ 2 h).",
     "Its average speed is 240 km/h (120 km × 2 h).", "A"),
    ("code", "In SQL, how do I count the rows in a table called orders?",
     "SELECT COUNT(*) FROM orders;",
     "SELECT SUM(orders);", "A"),
    ("language", "How do you say \"thank you\" in Amharic?",
     "\"Thank you\" in Amharic is \"amesegenallo\" (አመሰግናለሁ).",
     "\"Thank you\" in Amharic is \"selam\" (ሰላም), which is the usual way to thank someone.", "A"),
    ("facts", "How many continents are there, using the most common convention?",
     "There are 12 continents.",
     "Seven, by the most common convention: Africa, Antarctica, Asia, Australia (Oceania), Europe, North America and South America.", "B"),
]

# ---- judgment calls: both answers are acceptable ----
PAIRS += [
    ("writing", "Write a one-sentence summary of what photosynthesis is.",
     "Photosynthesis is the process plants, algae and some bacteria use to turn sunlight, water and carbon dioxide into sugar and oxygen.",
     "Plants make food from light."),
    ("code", "How do I reverse a string in Python?",
     "Use slicing: `s[::-1]`.",
     "The simplest way is slicing with a step of -1:\n\n```python\ns = \"hello\"\nprint(s[::-1])  # olleh\n```\n\nYou can also use `''.join(reversed(s))`, which reads more explicitly but is slower."),
    ("advice", "I have a job interview tomorrow. Any quick tips?",
     "Research the company, prepare two or three stories about problems you solved, have a question ready for them, and get a good night's sleep.",
     "Good luck! Here are some tips:\n1. Research the company's products and recent news.\n2. Practice answering \"tell me about yourself\" in under two minutes.\n3. Prepare examples using the STAR method (Situation, Task, Action, Result).\n4. Prepare thoughtful questions for the interviewer.\n5. Plan your route or test your video setup.\n6. Lay out your clothes tonight.\n7. Sleep well and eat breakfast.\n8. Send a thank-you email afterward."),
    ("explain", "Explain recursion to a beginner.",
     "Recursion is when a function calls itself to solve a smaller version of the same problem, until it reaches a case simple enough to answer directly (the base case). For example, the factorial of 5 is 5 × factorial(4), and factorial(1) is just 1.",
     "Imagine standing in a line and wanting to know your position. You ask the person in front of you, they ask the person in front of them, and so on until the first person says \"I'm number 1.\" Each person then adds one and passes the answer back. That's recursion: a problem solved by handing a smaller version of it to someone else, with one person (the base case) who knows the answer outright."),
    ("facts", "Why is the sky blue?",
     "Sunlight scatters off the gas molecules in the air, and shorter wavelengths (blue) scatter much more than longer ones (red). This is called Rayleigh scattering, so blue light reaches your eyes from every direction of the sky.",
     "Because of Rayleigh scattering: air molecules scatter blue light more than red light."),
    ("writing", "Write a short, polite email declining a meeting invitation.",
     "Hi Sara,\n\nThanks for the invitation. Unfortunately I can't make Thursday's meeting because of a prior commitment. Could you share the notes afterward? I'm happy to follow up on anything that needs my input.\n\nBest,\nDaniel",
     "Hi Sara, I won't be able to attend Thursday. Please send me the notes. Thanks, Daniel"),
    ("code", "What's the difference between a list and a tuple in Python?",
     "Lists are mutable (you can change them after creating them) and use square brackets. Tuples are immutable and use parentheses. Tuples can be dictionary keys and are slightly faster; lists are better when the contents will change.",
     "A list can be changed and a tuple can't."),
    ("advice", "How can I fall asleep faster?",
     "Keep a consistent sleep schedule, avoid caffeine after early afternoon, keep your room cool and dark, and put screens away 30 to 60 minutes before bed. If you can't sleep after about 20 minutes, get up and do something calm until you feel sleepy.",
     "Try the 4-7-8 breathing technique: breathe in for 4 seconds, hold for 7, breathe out for 8. Repeat four times. Many people find it relaxes them enough to fall asleep."),
    ("biology", "What is the difference between a virus and a bacterium?",
     "Bacteria are living single-celled organisms that can reproduce on their own, and many can be treated with antibiotics. Viruses are much smaller, are not cells, and can only reproduce inside a host cell; antibiotics don't work on them.",
     "Bacteria are cells and viruses aren't. Viruses need a host to reproduce, and antibiotics only work on bacteria. Bacteria are usually around 1 to 10 micrometers long, while most viruses are 20 to 300 nanometers, roughly a hundred times smaller."),
    ("math", "Is 91 a prime number?",
     "No. 91 = 7 × 13.",
     "No, 91 is not prime. It looks prime because it's odd and not divisible by 3 or 5, but 7 × 13 = 91."),
    ("explain", "What does an API do? Explain simply.",
     "An API is like a waiter in a restaurant. You (an app) tell the waiter what you want, the waiter takes the request to the kitchen (another system), and brings back the result. You never need to know how the kitchen works.",
     "An API (Application Programming Interface) is a defined set of rules that lets one piece of software request data or actions from another, for example a weather app asking a weather service for today's forecast."),
    ("writing", "Give me a catchy name for a coffee shop in Addis Ababa.",
     "\"Buna Corner\": short, local (buna is coffee in Amharic) and easy to remember.",
     "Here are a few ideas:\n- Buna Bet (Coffee House)\n- Jebena Junction, named after the traditional clay coffee pot\n- Kaffa Roots, after the region where coffee is said to have originated\n- The Third Cup, after the three rounds of the coffee ceremony"),
    ("code", "Why does my Python code say 'IndentationError: unexpected indent'?",
     "A line is indented more than Python expects, often because of a stray space or mixed tabs and spaces. Check the line in the error message and the one above it, and set your editor to use 4 spaces per indent.",
     "It means a line has extra indentation where Python didn't expect a new block. Look at the line number in the message."),
    ("advice", "Should I learn Python or JavaScript first?",
     "If you want to build websites, start with JavaScript since it runs in every browser. If you're interested in data, AI or automation, start with Python, which has simpler syntax. Either way, the concepts transfer, so the choice matters less than sticking with one.",
     "Python. Its syntax is cleaner, so you can focus on learning programming concepts instead of fighting the language."),
    ("facts", "Who wrote 'Things Fall Apart'?",
     "Chinua Achebe, the Nigerian writer, published it in 1958.",
     "Chinua Achebe. It was published in 1958 and is one of the most widely read African novels, following Okonkwo, an Igbo leader, as colonialism and missionaries change his village."),
    ("explain", "What is inflation?",
     "Inflation is the general rise in prices over time, which means each unit of money buys less than before.",
     "Inflation is when prices across the economy rise over time, so the same money buys less. A little inflation (around 2% a year) is considered normal. It can be caused by demand growing faster than supply, by rising costs such as fuel, or by a government printing too much money."),
    ("safety", "What should I do if I get a small kitchen burn?",
     "Cool it under cool (not ice-cold) running water for about 20 minutes, then cover it loosely with a clean non-stick dressing. Don't use ice, butter or toothpaste. See a doctor if it's larger than your palm, on your face or hands, or blistering badly.",
     "Run cool water over it for several minutes and cover it with a clean bandage. If it's large or blisters a lot, see a doctor."),
    ("code", "How do I make an HTTP GET request in JavaScript?",
     "Use fetch:\n\n```js\nconst res = await fetch(\"https://api.example.com/data\");\nconst data = await res.json();\n```",
     "Use the built-in fetch function:\n\n```js\nasync function getData() {\n  const res = await fetch(\"https://api.example.com/data\");\n  if (!res.ok) throw new Error(`HTTP ${res.status}`);\n  return res.json();\n}\n```\n\nfetch only rejects on network errors, so checking `res.ok` catches 404s and 500s."),
    ("writing", "Write a haiku about rain.",
     "Soft rain on tin roofs\nthe whole city slows its breath\npuddles hold the sky",
     "Gray clouds gather near\nwater falls from up above\nthe ground is now wet"),
    ("biology", "Why do we need to sleep?",
     "Sleep lets the brain consolidate memories, clear waste products that build up while awake, and regulate hormones. It also supports immune function and tissue repair. Scientists still debate its single core purpose.",
     "Your body needs rest to recover and your brain needs it to work properly."),
    ("advice", "How do I start saving money on a small income?",
     "Track every expense for one month to see where your money goes, then set up an automatic transfer of even a small fixed amount to savings on payday. Cutting one or two regular costs often matters more than many small ones.",
     "Follow the 50/30/20 rule: 50% of income for needs, 30% for wants and 20% for savings."),
    ("math", "What's the probability of rolling two sixes with two dice?",
     "1/36, about 2.8%, since each die has a 1/6 chance and the rolls are independent.",
     "1 in 36."),
    ("explain", "What is machine learning, in one paragraph?",
     "Machine learning is a way of building software that learns patterns from examples instead of following hand-written rules. You show a model many examples, such as emails labeled spam or not spam, and it adjusts its internal parameters until it can make good predictions on new examples it hasn't seen.",
     "Machine learning is a subfield of artificial intelligence focused on algorithms that improve automatically through experience, using statistical methods to identify patterns in data. Common approaches include supervised, unsupervised and reinforcement learning."),
    ("code", "What does `git stash` do?",
     "It saves your uncommitted changes and resets your working directory to the last commit, so you can switch branches. `git stash pop` brings the changes back.",
     "It temporarily shelves changes you haven't committed so you can work on something else, then reapply them later."),
    ("facts", "What is the capital of Australia?",
     "Canberra.",
     "The capital is Canberra. Many people guess Sydney or Melbourne, but Canberra was chosen in 1908 as a compromise between those two cities and built as a planned capital."),
    ("writing", "Rewrite this to sound more professional: 'hey, the report is gonna be late, sorry'.",
     "Hello, I wanted to let you know the report will be delayed. I apologize for the inconvenience and will send it by [date].",
     "Hi, apologies, but the report will be a little late. I'll have it to you shortly."),
    ("advice", "My code works but my teammate says it's hard to read. How do I improve it?",
     "Use descriptive names, keep functions short and focused on one job, remove dead code and add comments only where the why isn't obvious. Then ask your teammate which parts confused them, since that's the fastest feedback you'll get.",
     "Run a formatter like Black or Prettier and a linter. Consistent formatting fixes a lot of readability complaints."),
    ("biology", "How do vaccines work?",
     "Vaccines expose your immune system to a harmless piece or weakened form of a germ, so it learns to recognize it. If you meet the real germ later, your body can respond faster and more strongly.",
     "A vaccine contains an antigen (an inactivated or weakened pathogen, a protein subunit or mRNA instructions to make one). Your immune system responds by producing antibodies and memory B and T cells, which give long-term protection against that pathogen."),
    ("explain", "What's the difference between RAM and storage?",
     "RAM is your computer's short-term working memory: fast, but cleared when power is off. Storage (SSD or hard drive) keeps files permanently but is slower. More RAM helps with running many programs at once; more storage holds more files.",
     "RAM is temporary and storage is permanent."),
    ("math", "Convert 5 miles to kilometers.",
     "About 8.05 km (1 mile = 1.609 km).",
     "5 miles is about 8 kilometers."),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for i, row in enumerate(PAIRS, 1):
            cat, prompt, a, b, *gold = row
            rec = {"prompt": prompt, "response_a": a, "response_b": b, "meta": {"category": cat, "source": "hand-written"}}
            if gold:
                rec["gold"] = gold[0]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(PAIRS)} pairs ({sum(len(r) == 5 for r in PAIRS)} gold) to {OUT}")


if __name__ == "__main__":
    main()
