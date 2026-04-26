import chromadb

CHROMA_PATH = "chroma_db"

client = chromadb.PersistentClient(path=CHROMA_PATH)


def inspect_all_collections():
    collections = client.list_collections()

    if not collections:
        print("❌ No collections found in DB.")
        return

    print(f"📦 Found {len(collections)} collections\n")

    for col in collections:
        name = col.name
        print("=" * 60)
        print(f"📂 Collection: {name}")

        collection = client.get_collection(name=name)
        total = collection.count()
        print(f"Total items: {total}\n")

        if total == 0:
            print("⚠️ Empty collection\n")
            continue

        # ⚠️ WARNING: loads everything into memory
        results = collection.get()

        ids = results.get("ids", [])
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])
        embeds = results.get("embeddings", [])

        for i in range(len(ids)):
            print(f"--- Item {i+1}/{total} ---")
            print("ID:", ids[i])

            # Document (truncate if too long)
            doc = docs[i]
            if doc and len(doc) > 300:
                doc = doc[:300] + "... [truncated]"
            print("Document:", doc)

            print("Metadata:", metas[i])

            if embeds:
                print("Embedding length:", len(embeds[i]))

            print()

        print("\n")


if __name__ == "__main__":
    inspect_all_collections()