from os.path import expanduser
from time import strftime
from typing import Any, TypedDict
import mariadb
import pywikibot as pwb
import requests


DEBUG = False # bool; print some info to the console if True
BIN_SIZE = 1000000 # int
TICK_STEP = 10 # int; in million QIDs

WIKIPAGE = 'User:MisterSynergy/itemstats'
EDIT_SUMMARY = 'update statistics (weekly job via Toolforge) #msynbot #unapproved'


class ReportDict(TypedDict):
    timestamp : str
    newestitem : int
    binsize : int
    binsizeFormatted : str
    dataGray : str
    dataWhite : str
    dataBlue : str
    dataRed : str
    dataBlack : str
    sumGray : int
    sumWhite : int
    sumBlue : int
    sumRed : int
    sumBlack : int
    legend : str


class WikidataReplica:
    def __init__(self):
        self.replica = mariadb.connect(
            host='wikidatawiki.analytics.db.svc.wikimedia.cloud',
            database='wikidatawiki_p',
            default_file=f'{expanduser("~")}/replica.my.cnf'
        )
        self.cursor = self.replica.cursor(dictionary=True)


    def __enter__(self):
        return self.cursor


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.replica.close()


def query_mediawiki(query:str) -> list[dict[str, Any]]:  # only simple queries here
    with WikidataReplica() as db_cursor:
        db_cursor.execute(query)
        result = db_cursor.fetchall()

    return result


def write_to_wikipage(fulldata:ReportDict) -> None:
    filename = f'{expanduser("~")}/pywikibot_tasks/itemstats/itemstats.txt'
    with open(filename, mode='r', encoding='utf8') as file_handle:
        wikitext = file_handle.read()

    site = pwb.Site(code='wikidata', fam='wikidata')
    site.login()

    page = pwb.Page(site, WIKIPAGE)
    page.text = wikitext.format(**fulldata)
    page.save(
        summary=EDIT_SUMMARY,
        watch='nochange',
        minor=True,
        quiet=True
    )


def query_wdqs(query:str) -> list[dict[str, dict[str, str]]]:  # only simple queries here
    response = requests.post(
        url='https://query.wikidata.org/sparql',
        data={
            'query' : query
        },
        headers={
            'Accept' : 'application/sparql-results+json',
            'User-Agent': f'{requests.utils.default_headers()["User-Agent"]} (Wikidata' \
                           ' bot by User:MisterSynergy; mailto:mister.synergy@yahoo.com)'
        }
    )

    payload = response.json()

    return payload.get('results', {}).get('bindings', [])


def get_newest_item_id() -> int:
    response = requests.post(
        'https://www.wikidata.org/w/api.php',
        params={
            'action' : 'query',
            'list' : 'recentchanges',
            'rctype' : 'new',
            'rclimit' : '1',
            'rcnamespace' : '0',
            'format': 'json'
        }
    ).json()
    newest_item_numeric = int(
        response.get('query', {}).get('recentchanges', [])[0].get('title', '')[1:]
    )

    return newest_item_numeric


def get_query1_results() -> tuple[dict[int, int], int]:
    query1 = f"""SELECT ?bin (COUNT(*) AS ?cnt) WHERE {{
  ?item wikibase:statements 0 .
  BIND(CEIL(xsd:integer(SUBSTR(STR(?item),33)) / {BIN_SIZE}) AS ?bin) .
}} GROUP BY ?bin ORDER BY ASC(?bin)"""
    query_result_1 = query_wdqs(query1)

    data1 = {}
    for row in query_result_1:
        data1[int(row.get('bin', {}).get('value', ''))] = int(row.get('cnt', {}).get('value', '0'))
    sum_data1 = sum( [ data1[i] for i in data1 ] )

    return data1, sum_data1


# older version of the second query; not in use any longer, can be removed from this file
# mistake was: this also includes redirected pages in Lexeme namespace
def get_query2_results_wdqs() -> tuple[dict[int, int], int]:
    query2 = f"""SELECT ?bin (COUNT(*) AS ?cnt) WHERE {{
  ?item owl:sameAs [] .
  BIND(CEIL(xsd:integer(SUBSTR(STR(?item),33)) / {BIN_SIZE}) AS ?bin) .
}} GROUP BY ?bin ORDER BY ASC(?bin)"""
    query_result_2 = query_wdqs(query2)

    data2 = {}
    for row in query_result_2:
        data2[int(row.get('bin', {}).get('value', ''))] = int(row.get('cnt', {}).get('value', '0'))
    sum_data2 = sum( [ data2[i] for i in data2 ] )

    return data2, sum_data2


def get_query2_results() -> tuple[dict[int, int], int]:
    query2_result = query_mediawiki(f"""SELECT
  CEILING(SUBSTRING(page_title FROM 2) / {BIN_SIZE}) AS bin,
  COUNT(*) AS cnt
FROM
  page
WHERE
  page_namespace=0
  AND page_is_redirect=1
GROUP BY
  bin
ORDER BY
  bin ASC""")
    
    data2 = {}
    for row in query2_result:
        data2[int( row.get('bin', 0.0) )] = int( row.get('cnt', 0) )
    sum_data2 = sum( [ data2[i] for i in data2 ] )

    return data2, sum_data2


def get_query3_results() -> dict[int, int]:
    query3_result = query_mediawiki(f"""SELECT
  CEILING(SUBSTRING(page_title FROM 2) / {BIN_SIZE}) AS bin,
  COUNT(*) AS cnt
FROM
  page
WHERE
  page_namespace=0
GROUP BY
  bin
ORDER BY
  bin ASC""")

    data3 = {}
    for row in query3_result:
        data3[ int( row.get('bin', 0.0) ) ] = int( row.get('cnt', 0) )
#    sum_data3 = sum( [ data3[i] for i in data3 ] ) # currently not needed

    return data3


def get_query4_results() -> tuple[dict[int, int], int]:
    query4_result = query_mediawiki(f"""SELECT
  CEILING(SUBSTRING(log_title FROM 2) / {BIN_SIZE}) AS bin,
  COUNT(DISTINCT log_title) AS cnt
FROM
  logging
WHERE
  log_namespace=0
  AND log_type=\'delete\'
  AND log_action=\'delete\'
  AND log_title NOT IN (
    SELECT
      page_title
    FROM
      page
    WHERE
      page_namespace=0
  )
GROUP BY
  bin
HAVING
  bin>0
ORDER BY
  bin ASC""")

    data4 = {}
    for row in query4_result:
        data4[ int( row.get('bin', 0.0) ) ] = int( row.get('cnt', 0) )
    sum_data4 = sum( [ data4[i] for i in data4 ] )

    return data4, sum_data4


def pad(data:dict[int, int], target_length:int) -> dict[int, int]:
    if len(data) < target_length:
        add_missing = target_length - len(data)
        while add_missing > 0:
            data[max(data.keys())+1] = 0
            add_missing -= 1

    return data


def compute_query5_results(data1:dict[int, int], data2:dict[int, int], \
                           data3:dict[int, int]) -> tuple[dict[int, int], int]:
    data5 = {}
    for i in data1:
        data5[i] = data3[i] - data1[i] - data2[i]
    sum_data5 = sum( [data5[i] for i in data5] )

    return data5, sum_data5


def compute_query6_results(data1:dict[int, int], data3:dict[int, int], \
                           data4:dict[int, int], max_id:int) -> tuple[dict[int, int], int]:
    data6 = {}
    for i in data1:
        data6[i] = BIN_SIZE - data3[i] - data4[i]
    data6[ list(data6.keys())[-1] ] -= BIN_SIZE - max_id%BIN_SIZE
    sum_data6 = sum( [data6[i] for i in data6] )

    return data6, sum_data6


def get_ticks(data1:dict[int, int]) -> list[str]:
    ticks = []
    for i in range(0, len(data1)):
        if (i+1)%TICK_STEP == 0:
            ticks.append(f'Q{int((i+1)*BIN_SIZE/1000000)}M')
        else:
            ticks.append('')

    return ticks


def debug_print(data1:dict[int, int], data2:dict[int, int], data3:dict[int, int], \
                data4:dict[int, int]) -> None:
    if not DEBUG: # for debugging only
        return

    with open('./debug_log.txt', mode='w', encoding='utf8') as file_handle:
        file_handle.write(f'len(data1)={len(data1)}\n')
        file_handle.write(f'len(data2)={len(data2)}\n')
        file_handle.write(f'len(data3)={len(data3)}\n')
        file_handle.write(f'len(data4)={len(data4)}\n')
        file_handle.write(f'data1={data1}\n')
        file_handle.write(f'data2={data2}\n')
        file_handle.write(f'data3={data3}\n')
        file_handle.write(f'data4={data4}\n')


def main() -> None:
    #### basic setup
    timestmp = strftime('%-d %B %Y, ~%-H:%M (UTC)')

    #### use SPARQL for query1 and query2
    data1, sum_data1 = get_query1_results() # zero statements per bin
    data2, sum_data2 = get_query2_results() # redirects per bin

    #### request latest created item from API
    newest_item_numeric = get_newest_item_id()

    #### query MediaWiki database for query3 and query4
    data3 = get_query3_results() # item pages per bin
    data4, sum_data4 = get_query4_results() # deleted items per bin

    #### temporary workaround
    # TODO: dictionaries sometimes have different lengths; why?
    data3 = pad(data3, len(data1))
    data4 = pad(data4, len(data1))

    debug_print(data1, data2, data3, data4)

    #### compute data5 and data6 based on previous results
    data5, sum_data5 = compute_query5_results(data1, data2, data3) # items with statements per bin
    data6, sum_data6 = compute_query6_results(data1, data3, data4, newest_item_numeric) # skipped

    #### compute legend for diagram
    ticks = get_ticks(data1)

    #### output
    write_to_wikipage({
        'timestamp' : timestmp,
        'newestitem' : newest_item_numeric,
        'binsize' : BIN_SIZE,
        'binsizeFormatted' : f'{BIN_SIZE:,}',
        'dataGray' : ':'.join([ str( data1[i] ) for i in data1 ]),
        'dataWhite' : ':'.join([ str( data5[i] ) for i in data5 ]),
        'dataBlue' : ':'.join([ str( data2[i] ) for i in data2 ]),
        'dataRed' : ':'.join([ str( data4[i] ) for i in data4 ]),
        'dataBlack' : ':'.join([ str( data6[i] ) for i in data6 ]),
        'sumGray' : sum_data1,
        'sumWhite' : sum_data5,
        'sumBlue' : sum_data2,
        'sumRed' : sum_data4,
        'sumBlack' : sum_data6,
        'legend' : ':'.join(ticks)
    })


if __name__=='__main__':
    main()
