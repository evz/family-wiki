General improvements:
* Make sure imports are at the top of modules and not within functions or class bodies
* Make sure we doing error handling correctly across the entire app
* Flesh out research question functions. Not really sure what it's actually doing right now.
* Flesh out wiki export. We don't have this at all yet
yet

Extraction improvements:
* Remove code to run scripts on their own (argparse, if __name__ == "__main__", etc)
  - ocr_processor.py
  - genealogy_model_benchmark.py
  - llm_genealogy_extractor.py
    - the latter two also need to use the logger instead of print statements
* LLMGenealogyExtractor
  - get rid of create_genealogy_prompt since we're wanting to use the file or a prompt stored in the DB
  - lets use the flask config to default the values for the args in the initializer instead of hardcoded strings
  - Remove OpenAI related stuff
  - Since we know we're using ollama, it seems like we can make some assumptions about how the interactions with the remote LLM service will go. Do we really need to be so defensive in extract_from_chunk for instance?
