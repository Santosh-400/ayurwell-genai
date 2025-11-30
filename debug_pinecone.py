import sys
print(f"Python executable: {sys.executable}")
try:
    import pinecone
    print(f"Pinecone module: {pinecone}")
    print(f"Pinecone version: {getattr(pinecone, '__version__', 'unknown')}")
    from pinecone import Pinecone, ServerlessSpec
    print("Import Pinecone class successful")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
