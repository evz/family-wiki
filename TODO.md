General improvements:
* Flesh out research question functions. Not really sure what it's actually doing right now.
* Flesh out wiki export. We don't have this at all yet

Javascript:
* Rewrite using react and typescript? At least use jQuery?

app.py:
* Don't default values inline. Make the app fail to startup if those values aren't set and add them to the example env file.
* Make class properties lowercase and snake case so we don't confuse them with constants
* The print statements can go. The log messages can go.

api_database.py
* in get_database_stats extraction_service is never initialized. 

extraction_service.py
* get_database_stats is just passing through the same method from the GenealogyRespository 

