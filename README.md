# itemstats
## High level description
This is a Wikidata bot that produces a breakdown of Q-identifiers (Q-IDs) in [Wikidata](https://www.wikidata.org/) by type:
* Data items with claims
* Data items without claims
* Deleted data items
* Redirects data items
* Omitted Q-IDs

The report helps the Wikidata community to spot issues to pick up.

Currently, the report can be read at [User:MisterSynergy/itemstats](https://www.wikidata.org/wiki/User:MisterSynergy/itemstats).

## Technical requirements
The bot is currently scheduled to run weekly on [Toolforge](https://wikitech.wikimedia.org/wiki/Portal:Toolforge) from within the `msynbot` tool account. It depends on the [shared pywikibot files](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Pywikibot#Using_the_shared_Pywikibot_files_(recommended_setup)) and is running in a Kubernetes environment using Python 3.9.2.

## Credits
The idea for this report is from [User:Succu](https://www.wikidata.org/wiki/User:Succu) who maintained a similar report some years ago. No code from that implementation was re-used in this project.