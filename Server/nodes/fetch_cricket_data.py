from datasets import load_dataset
import re

# -----------------------
# Load datasets
# -----------------------
ds1 = load_dataset("catyung/cricket-qa-dataset", split="train")
ds2 = load_dataset("deeprai08/cricket-info", split="train")

# -----------------------
# Parse ds2
# -----------------------
def parse(row):
    q = re.search(r"Human:.*?generate an answer for (.+?)\n", row["text"])
    a = re.search(r"Assistant:\n(.+)", row["text"])

    return {
        "Question": q.group(1).strip() if q else "",
        "Answer": a.group(1).strip() if a else ""
    }

ds2 = ds2.map(parse)

# -----------------------
# Chunking
# -----------------------
CHUNK_SIZE = 10

def make_chunks(dataset, chunk_size):
    chunks = []

    for i in range(0, len(dataset), chunk_size):
        chunk = dataset.select(
            range(i, min(i + chunk_size, len(dataset)))
        )
        chunks.append(chunk)

    return chunks

ds1_chunks = make_chunks(ds1, CHUNK_SIZE)
ds2_chunks = make_chunks(ds2, CHUNK_SIZE)

# -----------------------
# Stats
# -----------------------
print("\n===== CHUNK SUMMARY =====")

print(f"\nDS1 Total Rows: {len(ds1)}")
print(f"DS1 Total Chunks: {len(ds1_chunks)}")

print(f"\nDS2 Total Rows: {len(ds2)}")
print(f"DS2 Total Chunks: {len(ds2_chunks)}")

# -----------------------
# Print top 10 chunks
# -----------------------
def print_top_chunks(chunks, name, top_n=10):

    print(f"\n\n==============================")
    print(f"TOP {top_n} CHUNKS FROM {name}")
    print(f"==============================")

    for chunk_idx, chunk in enumerate(chunks[:top_n]):

        print(f"\n\n===== CHUNK {chunk_idx} =====")

        for row_idx in range(len(chunk)):

            row = chunk[row_idx]

            print(f"\n--- Row {row_idx + 1} ---")

            for k, v in row.items():
                print(f"{k}: {v}")

# -----------------------
# Print
# -----------------------
print_top_chunks(ds1_chunks, "DS1")
print_top_chunks(ds2_chunks, "DS2")