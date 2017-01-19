#!/usr/bin/python3.5

#Author:        Sasan Bahadaran
#Date:          12/16/16
#Organization:  Commerce Data Service
#Description:   This is a bot script for getting Census data from the Census
#Bureau API's and writing it to Wikidata.

import pywikibot, json, os, requests, argparse, logging, time, json, sys
from pywikibot.data import api


def get_census_values(api_url, get_var, for_var):
    try:
        payload = {'get': get_var, 'for': for_var, 'key': os.environ['CENSUS']}
        r = requests.get(api_url, params=payload)
        return r.json()
    except requests.exceptions.RequestException as e:
        logging.error(e)
        sys.exit(1)
    except IOError as err:
        logging.error(err)

def find_wiki_items(sparql_query, item_key):
    try:
        sparql_url = 'https://query.wikidata.org/sparql'
        payload = {'query': sparql.replace("XXX", '\"'+item_key+'\"', 1),\
            'format': 'JSON'}
        r = requests.get(sparql_url, params = payload)
        return r.json()
    except requests.exceptions.RequestException as e:
        logging.error(e)
        sys.exit(1)

#SPARQL Queries do not work on test site
def find_test_wiki_items(site, item_title):
    params = {'action': 'wbsearchentities',
              'format': 'json',
              'language': 'en',
              'type': 'item',
              'search': item_title}
    request = api.Request(site = site, **params)
    return request.submit()

def get_claims(item):
    try:
        item_dict = item.get(force=True)
        if statement in item.claims:
            claims = item_dict['claims'][statement]
            if len(claims) > 0:
                return claims
            else:
                return None
        else:
            return None
    except:
        raise

def check_claim(claim, val, qualifiers):
    try:
        #0 - claim matches
        #1 - remove claim
        #2 - skip claim
        claim_status = 0
        p_in_time = qualifiers[0][0]
        det_method = qualifiers[1][0]
        logging.info('Entry Value: {}'.format(claim.getTarget().amount))
        if p_in_time in claim.qualifiers:
            logging.info('Entry Year: {}'.format(claim.qualifiers[p_in_time][0].getTarget().year))
            if claim.qualifiers[p_in_time][0].getTarget().year == qualifiers[0][1][1]:
                logging.info('claim val: {}, val: {}'.format(claim.getTarget().amount, val))
                if claim.getTarget().amount == val:
                    if det_method in claim.qualifiers:
                        if claim.qualifiers[det_method][0].getTarget().id != qualifiers[1][1][1]:
                            logging.info('Qualifier {} value incorrect'.format(qualifiers[1][0]))
                            claim_status = 1
                    else:
                        logging.info('Qualifier determination method missing')
                        claim_status = 1
                else:
                    logging.info('Statement claim value incorrect')
                    claim_status = 1
            else:
                logging.info('value should be skipped')
                claim_status = 2
        else:
            logging.info('Qualifier point in time missing')
            claim_status = 1
        logging.info('Status of Claim: {}'.format(claim_status))
        return claim_status
    except:
        raise

def check_references(claim, references):
    source_claims = claim.getSources()
    if len(source_claims) != 1:
        logging.info('Incorrect number of references')
        return False
    else:
        if len(source_claims[0]) != len(references):
            logging.info('Incorrect number of items in reference')
            return False
        else:
            for k, v in source_claims[0].items():
                if k in references:
                    prop_type = references[k][0]
                    source_val = None
                    if prop_type == 'id':
                        source_val = v[0].getTarget().id
                    elif prop_type == 'url':
                        source_val = v[0].getTarget()
                    if source_val != references[k][1]:
                        logging.info('Value incorrect for key: {}'.format(k))
                        return False
                else:
                    logging.info('Wrong item contained in reference')
                    return False
    return True

def remove_claim(claim, prop):
    try:
        item.removeClaims(claim)
        logging.info('Claim removed')
        return True
    except:
        return False

def create_claim(prop, prop_val, summary):
    newclaim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(prop_val)
    newclaim.setTarget(wb_quant)
    item.addClaim(newclaim, bot = True, summary = summary)
    logging.info('New claim created')
    return newclaim

def create_qualifiers(claim, qualifiers):
    for q in qualifiers:
        qualifier = pywikibot.Claim(repo, q[0])
        if q[1][0] == 'time':
            trgt_item = pywikibot.WbTime(q[1][1])
        elif q[1][0] == 'item':
            trgt_item = pywikibot.ItemPage(repo, q[1][1])
        qualifier.setTarget(trgt_item)
        claim.addQualifier(qualifier)
        logging.info('Qualifier: {} added'.format(q[0]))
    return True

def create_references(claim, references):
    try:
        source_claim_list = []
        for k, v in references.items():
            source_claim = pywikibot.Claim(repo, k, isReference=True)
            trgt_item = None
            if v[0] == 'id':
                trgt_item = pywikibot.ItemPage(repo, v[1])
            elif v[0] == 'url':
                trgt_item = v[1]
            source_claim.setTarget(trgt_item)
            source_claim_list.append(source_claim)
        claim.addSources(source_claim_list)
        logging.info('References added')
        return True
    except:
        return False

def add_full_claim(statement, metric_val, qualifiers, references, summary):
    try:
        newclaim = create_claim(statement, metric_val, summary)
        create_qualifiers(newclaim, qualifiers)
        create_references(newclaim, references)
        logging.info('Full claim addition complete')
    except:
        raise

def loadConfig(data_file):
    #global api_url, get_var, for_var, summary, statement, references, qualifiers
    try:
        with open(data_file) as df:
            jsondata = json.load(df)
            print(json.dumps(jsondata, indent=4))
            return jsondata
    except:
        raise

def getKeyVals(wiki_lookup_key, val):
    val_key = ''
    for item in wiki_lookup_key['api_cols']:
        val_key += val[item]
    key = wiki_lookup_key['beg_val']+val_key+wiki_lookup_key['end_val']
    print(key)
    return key

#def processClaim():

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    data = []

    #logging configuration
    logging.basicConfig(
                        filename='logs/censusbot-log-'+time.strftime('%Y%m%d'),
                        level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s -%(message)s',
                        datefmt='%Y%m%d %H:%M:%S'
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
                        '-m',
                        '--mode',
                        required=True,
                        type=str,
                        choices=['t', 'p'],
    )
    args = parser.parse_args()
    logging.info("--SCRIPT ARGUMENTS--------------")
    if args.mode == 't':
        logging.info('-- Mode set to: TEST')
    elif args.mode == 'p':
        logging.info('-- Mode set to: PROD')
    logging.info("-- [JOB START]  ----------------")

    # requests_log = logging.getLogger("requests.packages.urllib3")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

    if args.mode == 't':
        site = pywikibot.Site('test', 'wikidata')
        data_file = os.path.join(scriptpath, "data", "data_test.json")
    else:
        site = pywikibot.Site('wikidata', 'wikidata')
        data_file = os.path.join(scriptpath, "data", "data.json")

    data = loadConfig(data_file)
    repo = site.data_repository()
    if data:
        for api_item in data:
            if api_item['enabled']:
                api_url = api_item['api_url']
                logging.info('[api_url]: {}'.format(api_url))
                logging.info('[Expected response]: {}'.format(api_item['response']))
                get_var = api_item['get']
                logging.info('[get_var]: {}'.format(get_var))
                for_var = api_item['for']
                logging.info('[for_var]: {}'.format(for_var))
                summary = api_item['summary']
                logging.info('[summary]: {}'.format(summary))
                #add condition to ignore sparql parameter if test mode
                sparql = api_item['sparql']
                logging.info('[sparql]: {}'.format(sparql))
                for item in api_item['items']:
                    wiki_lookup_key = item['wiki_lookup_key']
                    logging.info('[wiki_lookup_key]: {}'.format(wiki_lookup_key))
                    api_value_column = item['api_value_column']
                    logging.info('[api_value_column]: {}'.format(api_value_column))
                    statement = item['statement']
                    logging.info('[statement]: {}'.format(statement))
                    content = item['content']
                    references = content['references']
                    logging.info('[references]: {}'.format(references))
                    qualifiers = content.get('qualifiers')
                    logging.info('[qualifiers]: {}'.format(qualifiers))

                    #need to use different method (find_test_wiki_items) when
                    #passing test flag since SPARQL queries do not work for test

                    #process each item
                    metric_values = get_census_values(api_url, get_var, for_var)
                    for val in metric_values[1:]:
                        key = getKeyVals(wiki_lookup_key, val)
                        metric_val = int(val[api_value_column])
                        logging.info('Metric: {}[{}] - Value: {}'.format(val[1].split(',')[0], key, metric_val))
                        search_results = find_wiki_items(sparql, key)
                        #if only single search result
                        results_cnt = len(search_results['results']['bindings'])
                        if results_cnt == 1:
                            item_url = search_results['results']['bindings'][0]['wd']['value']
                            item_id = pywikibot.ItemPage(repo, item_url.split('/')[-1])
                            logging.info('Item ID: {}'.format(item_id))
                        #     claims = get_claims(item_id)
                        #     claim_present = False
                        #     if claims:
                        #         for claim in claims:
                        #             claim_status = check_claim(claim, val, qualifiers)
                        #             if claim_status == 0:
                        #                 source = check_references(claim, references)
                        #                 if not source:
                        #                     remove_claim(claim, statement)
                        #                 else:
                        #                     claim_present = True
                        #             elif claim_status == 1:
                        #                 remove_claim(claim, statement)
                        #     if not claim_present:
                        #         add_full_claim(statement, metric_val, qualifiers, references, summary)
                        # elif results_cnt == 0:
                        #     logging.info('0 wiki items found')
                        #     #create method for adding new page for item
                        # elif results_cnt > 1:
                        #     logging.info('more than 1 wiki item found')
            else:
                logging.info('Config item not enabled')
    else:
        logging.error('Data file did not load any claims to iterate over')
