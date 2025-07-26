General improvements:
* Flesh out research question functions. Not really sure what it's actually doing right now.
* Flesh out wiki export. We don't have this at all yet

General workflow:
1. upload PDFs, one for each page
2. Extract text from each PDF and save it to DB
3. Concatenate all PDFs from one run, create corpus
  - RagService.load_pdf_text_files should be rewitten to handle rows from DB
    that are created in step 2. 
4. From here we can do a few different things:
  - Extract structured data about family mentioned in the corpus:
    - People and how they are related
      - Specific details like birth, death, baptism, occupations, marriages,
        places where these occurred. 
    - Places and how they relate to people and events
    - Events including the ones mentioned under people as well as family
      gatherings or immigrations / emmigrations.
  - Ask freeform questions about the corpus from the LLM
    - Should be able to ask in English or Dutch and receive answers in English
      or Dutch.
  - Generate ideas about further areas of research. 
    - Related to historical events
    - Related to the specific history of a place
    - Related to indistries or cultural movements
    - And other things that I can't think of

Style:
* Imports at the top of modules
* No route needs /api in front of it. 
* Sometimes we're using type hints and sometimes we arent't. Let's always do
  it.
* No hardcoded defaults in method signatures.
* What's a "service" vs. a "repository"?

Templates:
* use url_for for internal links

app.py:
* Don't default values inline. Make the app fail to startup if those values
  aren't set and add them to the example env file.
* Make class properties lowercase and snake case so we don't confuse them with
  constants
* The print statements can go. The log messages can go.
* The app should fail to start up if it doesn't have ollama env vars set

main index.html
* Need to rework this with links to the different parts of the site:
  - Extraction
  - Entity explorer
  - Corpora create/edit
  - Prompt create/edit

main.js
* The only thing we need in here are functions that poll for the status of
  delayed / celery jobs 

main.py
* Move the tools dashboard route here.
* Move the /api/jobs route here.
* Make the styling on the dashboard a little easier to follow. Each form should
  be more distinct

tools.py
* The dashboard here should probably just be the main index of the site.
* Better exception handling
* Separate gedcom, extraction and research routes into their own blueprints.
  - Once those are extracted, probably don't need this module anymore since the
    dashboard can just move to the main blueprint.

rag.py
* Still need an actual query interface. Looks like there's no way to actually
  start a query session?
* No global instance, please

rag_service.py:
* we should not have defaults hardcoded for OLLAMA stuff.
  - Seems like ollama_base_url should be class property that gets set on init.
* We should allow embedding model to be configurable
  - default in TextCorpus database model doesn't match default that we're
    sending to ollama in generate_embedding
  - Does it matter that the SourceText embedding default isn't the same as the
    TextCorpus embedding default?
* better exception handling
  - Like, lots better. Yikes. 
* We should be loading text file from the database since we'll be uploading
  that.
* generate_rag_response needs to be shorter.

ocr_processor.py:
* Needs to save results to DB. Let's make a table to store pages extracted from
  PDFs and then a corpus can just have foreign key relationships to the raw
  chunks.

models
* Get rid of dataclass models + tests
* Maybe we need a way to link the entities to the extraction run and the
  extraction run to the prompt that was used. This way we can keep track of how
  a prompt performed and delete the entities related to a particular prompt in
  the case where it did a lousy job
* Probably needs regression tests for classmethods and properties.

tasks.py
* better exception handling. No naked exceptions

genealogy_repository.py
* better exception handling

llm_genealogy_extractor.py:
* get rid of openai stuff
* default prompt should be in the DB not hardcoded.
* where is process_all_text used?

dutch_utils.py
* Lets not have private classmethods
* particle should be tussenvoegsel
* The gender detection needs to be a little smarter if we're going to use it.
  Can we do it with ollama?

commands.py:
* On second thought, we probably don't need these.

tests:
* duplicate fixtures

tests/test_models.py
* nix since this is for the dataclasses

tests/test_rag_api.py
* nix since it tests JSON api

tests/test_commands.py
* nix since we're nixing commands

tests/test_flask_app.py
* Not really sure why this exists. Seems to duplicate a lot of other tests or
  is for functionality we are factoring out.
  - In particular: 
    - commands.py
    - tools routes
* The only config test that seems worth keeping is the on that tests configs
  getting overridden by env vars

tests/test_dutch_utils.py
* particle should be tussenvoegsel


---

DB migrations
QuerySession needs to be removed
Need way of deleting corpus in UI
