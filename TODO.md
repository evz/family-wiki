Use better approach for chunking with additional columns on chunks table:

trigram index
soundex index
tsvector index

process incoming query:
  - clean text the same way we're cleaning text chunks
  - create embeddings
  - Lookup soundex codes

Use CTE from chatgpt to find relevant chunks based on processed query
pull in neighboring chunks and eliminate duplicates before sending to LLM
