import sqlite3, json

db = sqlite3.connect("messages.db")
cur = db.cursor()

rows = list(cur.execute("SELECT author, content FROM messages ORDER BY timestamp ASC"))

with open("dataset.jsonl", "w", encoding="utf-8") as out:
    for i in range(len(rows) - 1):
        author1, content1 = rows[i]
        author2, content2 = rows[i+1]

        if not content1.strip() or not content2.strip():
            continue

        sample = {
            "prompt": f"{author1}: {content1.strip()}",
            "response": f"{author2}: {content2.strip()}"
        }

        out.write(json.dumps(sample, ensure_ascii=False) + "\n")
