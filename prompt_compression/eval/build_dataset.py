"""Builds eval/classifier_dataset.jsonl plus a fixed dev/test split.

Every example is hand-written. All personal data, keys and card numbers are
fake (example.com domains, 555 phone numbers, published test card numbers,
the AWS documentation example key) so the file is safe to commit.

Labeling guide (also in README.md):
  sensitive       personal data, credentials, secrets, health, financial or
                  private legal information about a real-seeming person/org
  critical        instructions/constraints, code, numbers, identifiers or facts
                  whose alteration would change the correct answer
  non_sensitive   ordinary descriptive content: background, narrative, general
                  discussion; safe to compress with standard settings
  less_important  greetings, filler, repetition, chit-chat, redundant context

hard_negative=True marks examples built to look like another class, e.g. a
number that is not sensitive or an instruction phrased like small talk.

Run:  python -m prompt_compression.eval.build_dataset
"""

import json
import random
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
SEED = 13
# Per class: this many go to dev, the rest to the held-out test set.
DEV_PER_CLASS = 18

# (text, hard_negative)
SENSITIVE = [
    ("My email is jane.doe@example.com and my phone is +1 555 013 2287, please update my account.", False),
    ("Here is my card for the booking: 4111 1111 1111 1111, exp 08/29, CVV 123.", False),
    ("Login for the staging box is admin / P@ssw0rd!2024, don't share it.", False),
    ("export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE and AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", False),
    ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA7bq3examplekeymaterial\n-----END RSA PRIVATE KEY-----", False),
    ("My SSN is 123-45-6789, can you check if the form is filled correctly?", False),
    ("I was diagnosed with type 2 diabetes last month and I'm on metformin 500mg twice a day.", False),
    ("My therapist thinks my panic attacks are linked to the divorce. How do I tell my boss I need leave?", False),
    ("Patient John Carter, DOB 1979-04-12, MRN 448812, presented with chest pain and elevated troponin.", False),
    ("Our bank account is IBAN DE89 3704 0044 0532 0130 00, please wire the deposit there.", False),
    ("My salary is $86,000 and I still owe $23,400 on my credit cards. Should I file for bankruptcy?", False),
    ("I'm being sued by my former landlord for unpaid rent, case number 2024-CV-01873. What are my options?", False),
    ("Use this token for the API: ghp_1A2b3C4d5E6f7G8h9I0jK1lM2nO3pQ4rS5tU", False),
    ("OPENAI_API_KEY=" + "sk-" + "proj-" + "abc123DEF456ghi789JKL012mno345PQR678stu", False),  # split so secret scanners skip this synthetic key
    ("The database URL is postgres://app_user:s3cr3tPass@10.0.4.12:5432/payroll", False),
    ("Passport number X1234567, issued in Ottawa, expires 2031. Is that valid for travel to Japan?", False),
    ("My HIV test came back positive and I don't know how to tell my partner.", False),
    ("Hi! Quick one, my wife is pregnant but we haven't told anyone yet, any tips for hiding morning sickness at work?", True),
    ("lol so my credit score dropped to 540 after I missed three mortgage payments, kinda embarrassing", True),
    ("Our CEO is under internal investigation for harassment; draft a note to the board that keeps it confidential.", False),
    ("Here is the employee's home address: 42 Elm Street, Springfield, IL 62704. Send the contract there.", False),
    ("My daughter Emma Li (born 3 March 2015) has an allergy to penicillin, add that to the school form.", False),
    ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U", False),
    ("Slack webhook: https://hooks.slack.com/services/[SLACK_WORKSPACE_ID]/[SLACK_CHANNEL_ID]/[SLACK_TOKEN]", False),
    ("I've been drinking every night and my liver enzymes were high on the last blood test. Am I an alcoholic?", False),
    ("Our Q3 numbers before the public announcement: revenue $41.2M, a 12% miss. Keep this internal until earnings day.", False),
    ("My green card application was denied and my immigration lawyer says I may be deported.", False),
    ("Here's the root password for the router, it's tiger-lily-9921. Can you write the config?", False),
    ("Customer record: Maria Gonzalez, maria.g@example.org, 555-0199, account 00123987, balance overdue.", False),
    ("Thanks again! Oh and my PIN for the card is 4821 in case you need it for the test.", True),
    ("I'm on antidepressants (sertraline 100mg) and want to know if I can drink at the wedding.", False),
    ("Settlement terms between us and Acme are $2.5M plus an NDA; summarize them for our lawyer only.", False),
    ("My tax return shows $142,350 AGI and I claimed my mother as a dependent, is that allowed?", False),
    ("-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ\n-----END OPENSSH PRIVATE KEY-----", False),
    ("The Stripe live key is sk_live_[STRIPE_KEY_PLACEHOLDER], rotate it after the demo.", False),
    ("I had an abortion two years ago and I'm worried it will affect my fertility.", False),
    ("National ID 1985-0312-4471 belongs to the applicant, please verify against the registry.", False),
    ("Can you remember that my mom's maiden name is Kowalski? It's my security question answer.", True),
    ("hey hey :) my new login is mark.b@example.net with password Sunflower#77, can u test it", True),
    ("My son was arrested last night for possession; what should we say at the bail hearing?", False),
    ("Wire $9,800 from account 2201-5567-8890 to the vendor; keep it under the reporting limit.", False),
    ("Medical history: asthma since childhood, two hospitalizations in 2022, currently on Symbicort.", False),
    ("My routing number is 021000021 and account number 123456789012, set up direct deposit.", False),
    ("Employee review: Raj Patel is on a performance improvement plan and may be terminated in March.", False),
    ("My boyfriend checks my phone and threatened me last week; how can I get a restraining order quietly?", False),
    ("Please store my MasterCard 5555 5555 5555 4444 for future orders.", False),
    ("The client's DNA test results show a BRCA1 mutation; draft a referral letter to genetics.", False),
    ("My student loans total $68k and I'm three months behind on payments to Navient.", False),
    ("client_secret: 8f3b2c1d-4e5f-6a7b-8c9d-0e1f2a3b4c5d for the OAuth app, don't paste it in the wiki", False),
    ("Lol my blood pressure was 170/110 at the clinic today, doc wants me on meds", True),
    ("Our merger with Globex is not public yet; the price is $34 per share. Draft the internal memo.", False),
    ("Call me at (555) 867-5309 after 6pm, that's my personal cell.", False),
    ("My partner and I are going through IVF, round three, and the cost is draining our savings.", False),
    ("I was fired for a DUI and need to explain the gap on my resume without mentioning it.", False),
    ("Here's my driver's license: D1234-56789-01234, state CA, can you fill the rental form?", False),
]

CRITICAL = [
    ("Return the answer as JSON with exactly these keys: id, name, price. Do not add any other fields.", False),
    ("def apply_discount(price, pct):\n    if pct > 50:\n        raise ValueError('discount too large')\n    return round(price * (1 - pct / 100), 2)", False),
    ("Convert 72 degrees Fahrenheit to Celsius and round to one decimal place.", False),
    ("The order ID is ORD-2024-88731 and the SKU is BLK-4410-XL; check whether both match the invoice.", False),
    ("SELECT customer_id, SUM(amount) FROM payments WHERE created_at >= '2024-01-01' GROUP BY customer_id HAVING SUM(amount) > 1000;", False),
    ("The flight departs at 06:45 from Gate B22 and boarding closes 20 minutes earlier. When must I be at the gate?", False),
    ("Translate the following into French but keep product names like PowerEdge R760 unchanged.", False),
    ("Answer only with 'yes' or 'no'. Is 1,021 a prime number?", False),
    ("Never mention competitor brands in the reply, and keep the response under 80 words.", False),
    ("Fix the bug: the loop `for i in range(1, len(items))` skips the first element.", False),
    ("The API rate limit is 600 requests per minute per key, with a burst of 50. Calculate the max requests in 90 seconds.", False),
    ("Dosage rule: children under 12 get 5 mg/kg, max 250 mg per dose, every 8 hours. A 30 kg child needs how much?", False),
    ("Use Python 3.11 and only the standard library; no third-party packages.", False),
    ("Version 4.2.1 introduced the regression; version 4.1.9 is the last good build. Bisect between them.", False),
    ("Step 1: unzip the archive. Step 2: run make install. Step 3: restart the service. Do not skip step 2.", False),
    ("The contract term is 36 months starting 2025-02-01 with a 90-day notice period. When is the last day to cancel?", False),
    ("Write a regex that matches US ZIP codes in the form 12345 or 12345-6789.", False),
    ("const total = items.reduce((sum, item) => sum + item.qty * item.price, 0);\nconsole.log(total.toFixed(2));", False),
    ("Error: TypeError: Cannot read properties of undefined (reading 'map') at Dashboard.jsx:57. What causes this?", False),
    ("The tolerance is +/- 0.05 mm on a 12.70 mm shaft. Is a part measuring 12.76 mm within spec?", False),
    ("Sort the list [42, 7, 19, 7, 3] in descending order and remove duplicates.", False),
    ("Thanks! Now make it shorter, max 3 bullet points, and keep the exact figures.", True),
    ("hey quick thing, from now on reply only in Spanish ok? :)", True),
    ("lol ok cool, but pls keep the function signature exactly the same or the tests break", True),
    ("Haha sure, but remember the deadline is Friday 17:00 CET, not Thursday.", True),
    ("Use the EPSG:4326 coordinate system; the point is lat 48.8584, lon 2.2945.", False),
    ("kubectl scale deployment api-gateway --replicas=6 -n production", False),
    ("The tax rate is 7.25% state plus 1.5% county. Compute the total on a $1,240 purchase.", False),
    ("Make sure the output CSV uses semicolons as separators and UTF-8 with BOM encoding.", False),
    ("HTTP 429 means we hit the limit; retry with exponential backoff starting at 500 ms, max 5 retries.", False),
    ("Rename the column `cust_nm` to `customer_name` in all migrations, but not in the legacy view.", False),
    ("The capital of Australia is Canberra, not Sydney; correct the quiz answer key accordingly.", False),
    ("If the input list is empty, return None instead of raising an exception.", False),
    ("Water boils at 100 C at sea level but at about 70 C on the summit of Everest. Explain why.", False),
    ("Grade the essay using this rubric: thesis 30%, evidence 40%, style 20%, grammar 10%.", False),
    ("Compare the two files and list only lines that differ; ignore whitespace changes.", False),
    ("The meeting is in room 4.17 on floor 4, building C, at 14:30 UTC.", False),
    ("Calculate compound interest on $10,000 at 4.5% annually for 7 years.", False),
    ("git rebase -i HEAD~3 then squash the last two commits into the first one.", False),
    ("Respond in exactly three sentences, the second of which must be a question.", False),
    ("Patch CVE-2024-3094 by pinning xz-utils to 5.4.6 and rebuilding the image.", False),
    ("The answer must cite section 4.3(b) of the policy, not section 4.2.", False),
    ("ok ty! one more: change the color to #1A73E8 and the font size to 14px", True),
    ("Remember: the user's tier is 'gold', so apply the 15% discount, not the 10% one.", False),
    ("Parse the timestamp 2024-11-05T23:59:59+05:30 and convert it to UTC.", False),
    ("Given f(x) = 3x^2 - 2x + 1, compute f'(4).", False),
    ("Set max_tokens to 512, temperature to 0, and stop on the sequence '###'.", False),
    ("The pallet weighs 1,180 kg and the forklift limit is 1,200 kg. Can it lift a 25 kg box on top too?", False),
    ("np.where(arr > 0, arr, 0) should replace negatives with zero; why does it return a tuple here?", False),
    ("Hi there! Could you keep the reply in plain text, no markdown at all? Thanks!", True),
    ("Include the ticket number JIRA-4521 in the commit message title.", False),
    ("The train leaves Platform 9 at 10:10 and arrives at 12:55; how long is the trip?", False),
    ("Only use data from the attached table; do not use outside knowledge.", False),
    ("Swap the arguments: it should be copy(dst, src), not copy(src, dst).", False),
    ("The ISBN is 978-0-306-40615-7; verify the check digit.", False),
]

NON_SENSITIVE = [
    ("The city park was renovated last year and now has a larger playground and a walking trail along the river.", False),
    ("Many people enjoy hiking in autumn because the weather is cooler and the leaves change color.", False),
    ("Our team discussed general password hygiene in today's training, such as using a password manager.", True),
    ("In NLP, a 'token' is a unit of text such as a word or sub-word that a model processes.", True),
    ("I read about 3 books last month and enjoyed the mystery novel the most.", True),
    ("The bakery on the corner sells sourdough bread and croissants every morning.", False),
    ("The history of the printing press shows how information spread faster across Europe in the 1500s.", False),
    ("Coffee is grown in many tropical regions, including Brazil, Colombia, Ethiopia, and Vietnam.", False),
    ("The article describes how remote work changed commuting patterns in large cities.", False),
    ("Our company newsletter this month covers the new cafeteria menu and the summer volunteering event.", False),
    ("Photosynthesis lets plants turn sunlight, water and carbon dioxide into sugar and oxygen.", False),
    ("The museum's new exhibit features impressionist paintings on loan from several European galleries.", False),
    ("Blog draft: five reasons why indoor plants can make a small apartment feel more welcoming.", False),
    ("The football match ended in a draw after both teams scored in the second half.", False),
    ("Electric cars are becoming more common, and charging stations are appearing in shopping centers.", False),
    ("The novel follows a young sailor who travels across the Pacific and learns about different cultures.", False),
    ("Healthy eating often includes more vegetables, whole grains and fewer processed foods.", True),
    ("The conference had about 200 attendees and sessions on design, marketing and product strategy.", True),
    ("Our product team is exploring ways to make the onboarding experience smoother for new users.", False),
    ("Jazz developed in New Orleans in the early twentieth century, blending blues and ragtime.", False),
    ("The town holds a farmers market every Saturday where local growers sell fruit and cheese.", False),
    ("This report summarizes general customer feedback, which was mostly positive about delivery speed.", False),
    ("Bananas are one of the most popular fruits worldwide and are rich in potassium.", False),
    ("The weather in Lisbon is usually mild in spring, with occasional rain showers.", False),
    ("Our office moved to a building with more natural light and a rooftop terrace.", False),
    ("Learning a second language can help with travel and with understanding other cultures.", False),
    ("The documentary explores how coral reefs are affected by rising ocean temperatures.", False),
    ("Cybersecurity awareness month encourages people to learn about phishing and safe browsing.", True),
    ("The bank on Main Street has a nice old facade that architecture students like to photograph.", True),
    ("Volunteers cleaned up the beach and collected several bags of plastic waste.", False),
    ("Chess is a strategy game that has been played for centuries in many parts of the world.", False),
    ("A typical sprint in our team lasts two weeks, followed by a short retrospective meeting.", True),
    ("Some hospitals have started using robots to deliver supplies between departments.", True),
    ("The bookstore added a reading corner with comfortable chairs and a small coffee bar.", False),
    ("The movie received good reviews for its soundtrack and cinematography.", False),
    ("Many startups use cloud services so they do not have to maintain their own servers.", False),
    ("Spring cleaning is a tradition in many households after the long winter months.", False),
    ("The lecture covered the basic ideas of supply and demand in a market economy.", False),
    ("Our neighborhood has a lot of cyclists, especially on weekends when the roads are quieter.", False),
    ("The garden has tomatoes, basil and a few sunflowers that grow taller every week.", False),
    ("Mountains in the region attract skiers in winter and hikers during the summer months.", False),
    ("People often keep a journal to reflect on their day and organize their thoughts.", False),
    ("The company picnic will include games, food trucks and live music for families.", False),
    ("Our support team answered a wide range of questions about shipping and returns this week.", False),
    ("Public libraries offer free access to books, newspapers and sometimes workshops.", False),
    ("The podcast episode was about how ancient Romans built their roads and aqueducts.", False),
    ("Customers liked the new packaging because it is easier to recycle.", False),
    ("Some legal systems use juries while others rely mainly on professional judges.", True),
    ("The tech blog compared different note-taking apps and their general features.", False),
    ("Meditation is a practice many people use to reduce stress and improve focus.", True),
    ("The river flows through three countries before reaching the sea.", False),
    ("The school organized a science fair where students showed projects on renewable energy.", False),
    ("Most smartphones today have cameras good enough for everyday photography.", False),
    ("A good team meeting usually has a clear agenda and ends with agreed next steps.", False),
    ("The city's old train station was turned into a market hall with small food stalls.", False),
]

LESS_IMPORTANT = [
    ("Hi there! Hope you're having a great day.", False),
    ("Thanks so much, you're the best!", False),
    ("Good morning :) how's it going?", False),
    ("Ok cool, sounds good.", False),
    ("Haha, that's funny.", False),
    ("Just to repeat what I said above, as mentioned before, like I said earlier, the same thing again.", False),
    ("Hope you had a great weekend! 2 days off felt like 20 minutes lol", True),
    ("Hello hello! It's me again, back with more questions, haha.", False),
    ("Sorry for the long message, I tend to ramble a bit, bear with me.", False),
    ("Anyway, whatever, it doesn't really matter much.", False),
    ("Thank you in advance for your time and help, I really appreciate it!", False),
    ("Lol yeah, totally agree with you.", False),
    ("Cheers, have a nice evening!", False),
    ("Um, so, like, I was just thinking, you know, kind of.", False),
    ("As we already discussed in the previous messages, and as I mentioned a few times already.", False),
    ("Wow, nice! Love it!", False),
    ("Hey! Long time no see, how have you been?", False),
    ("Ok ok, got it, thanks.", False),
    ("Great, perfect, awesome, thank you!", False),
    ("I hope this message finds you well.", False),
    ("No worries at all, take your time!", False),
    ("Hmm, interesting, let me think about that for a second.", False),
    ("Have a lovely day and talk soon!", False),
    ("Yes yes, exactly what I was saying, exactly that.", False),
    ("By the way, it's raining here again, typical Monday lol.", False),
    ("Anyway, enough small talk from me.", False),
    ("Thanks for the quick reply, much appreciated as always.", False),
    ("Sorry, I keep repeating myself, it's been a long day.", False),
    ("Morning! Coffee first, questions later :)", False),
    ("Nice one, that made me laugh.", False),
    ("Hope your team is doing well too! Say hi to everyone for me.", False),
    ("Just following up on my previous message, again, as mentioned.", False),
    ("Happy Friday!! Almost weekend time.", False),
    ("Ahh I see, okay okay.", False),
    ("Please and thank you, kind regards, best wishes.", False),
    ("I was going to say something but I forgot what it was, haha.", False),
    ("You're awesome, seriously, thanks a million.", False),
    ("Alright, talk later, bye for now!", False),
    ("It's been a crazy week, 5 meetings a day, you know how it is.", True),
    ("Fun fact, I had 3 coffees already today, lol.", True),
    ("Hey, sorry to bother you again, I know you're busy, really sorry.", False),
    ("Okay so as I said, same as before, nothing new really.", False),
    ("Lovely, thank you, have a good one!", False),
    ("Gotcha, makes sense, thanks!", False),
    ("Hi! I'm Sam, nice to meet you :)", True),
    ("Thanks, that's all for now, really appreciate the help, have a great day ahead!", False),
    ("Hope your holidays were relaxing and fun!", False),
    ("Hah, my cat just walked across the keyboard, ignore that.", False),
    ("Sure thing, no problem at all.", False),
    ("Just saying hi before the meeting, nothing urgent!", False),
    ("Kind regards and best wishes to you and your family.", False),
    ("Lol I typed that wrong, my bad, ignore the typo.", False),
    ("Yeah, I guess, maybe, we'll see.", False),
    ("Hello! Thanks for being so patient with me.", False),
    ("Ok that's it from me, see ya!", False),
]

CLASSES = {
    "sensitive": SENSITIVE,
    "critical": CRITICAL,
    "non_sensitive": NON_SENSITIVE,
    "less_important": LESS_IMPORTANT,
}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    rng = random.Random(SEED)
    all_rows, dev_rows, test_rows = [], [], []

    for label, examples in CLASSES.items():
        rows = [
            {"id": f"{label}-{index:03d}", "text": text, "label": label, "hard_negative": hard}
            for index, (text, hard) in enumerate(examples, start=1)
        ]
        all_rows.extend(rows)
        shuffled = rows[:]
        rng.shuffle(shuffled)
        dev_rows.extend(shuffled[:DEV_PER_CLASS])
        test_rows.extend(shuffled[DEV_PER_CLASS:])

    _write_jsonl(EVAL_DIR / "classifier_dataset.jsonl", all_rows)
    _write_jsonl(EVAL_DIR / "classifier_dev.jsonl", dev_rows)
    _write_jsonl(EVAL_DIR / "classifier_test.jsonl", test_rows)

    for label, examples in CLASSES.items():
        print(f"{label:15s} total={len(examples)}")
    print(f"total={len(all_rows)} dev={len(dev_rows)} test={len(test_rows)}")


if __name__ == "__main__":
    main()
