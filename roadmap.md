# Roadmap, starting out
- C++ core
- Enable core to run Python extensions
- Database setup (?)

## Feature ideas
- ls shows 'foldername (git?) (env?) (size, rows, cols)' || v1 OK
- add different types of sorting/formatting to ls based on config / user input || OK
- add possibility for a config file so users could choose settings on/off etc || OK

- changes env automatically to correct one when entering a specific folder...
- ... or runs the folders content upon entering(safe commands only), saving time setting up... 
- ...could even run on startup on user defined mode (dev, prod, test?), saving time and effort opening things up
- running it in any new environment sets up all the same tools ready to use (or equivalents if not available).
- allow auto-save to git (needs some user setup)
- referencing 1st user story, the possibility for listing installs easily to the config.py

## Feature ideas (if AI enabled)
- Suggest fixes to bad commands
- AI features like answering questions based on context (folder, env)
- generate boilerplates/basecode on demand (based on context, new project? need db config?)

## User stories
- AS an user, i want my terminal toolset be the same no matter the place, easy setup

## MVP / Proof of Concept
- Core || OK
- Python extensions || OK
- config file || OK
- 1 simple feature for testing the wrapper, ls possibly || OK

## Next steps
- Something with databases, possibly ability to run SQL queries? or at least view tables?
- 