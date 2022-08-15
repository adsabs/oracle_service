from __future__ import division
from builtins import chr
from builtins import map
from builtins import zip
from builtins import range
from past.utils import old_div

import sys
import re

from fuzzywuzzy import fuzz
import lxml.html
import unidecode

from flask import current_app

from oraclesrv.utils import get_a_record, add_a_record
from oraclesrv.models import DocMatch
from oraclesrv.keras_model import KerasModel

confidence_model = KerasModel()

DOI_CONFIDENCE_SCORE = 1

re_match_collaboration = re.compile(r'([Cc]ollaboration[s\s]*)')
def count_matching_authors(ref_authors, ads_authors):
    """

    :param ref_authors:
    :param ads_authors:
    :return:
    """
    missing_in_ref, missing_in_ads, matching_authors, first_author_missing = 0, 0, 0, False

    try:
        ref_authors = ref_authors.split(';')
        ref_authors_lastname = [a.split(",")[0].strip() for a in ref_authors]
        ref_authors_firstinitial = [a.split(",")[1].strip()[0] for a in ref_authors]
        ref_authors_norm = [last+', '+ first for last,first in zip(ref_authors_lastname,ref_authors_firstinitial)]

        for author in ads_authors:
            if author in ref_authors_norm:
                matching_authors += 1
            else:
                missing_in_ref += 1

        for author in ref_authors_norm:
            if author not in ads_authors:
                missing_in_ads += 1

        first_author_missing = ads_authors[0] not in ref_authors_norm
    except:
        pass

    return (missing_in_ref, missing_in_ads, matching_authors, first_author_missing)

def get_author_score(ref_authors, ads_authors):
    """

    :param ref_authors:
    :param ads_authors:
    :return:
    """
    # note that ref_authors is a string, and we need to have at least one name to match it to
    # ads_authors with is a list, that should contain at least one name
    if len(ref_authors) == 0 or len(ads_authors) == 0:
        return 0

    # if there is collabration, consider the that only and return score for the first author only
    if re_match_collaboration.findall(ref_authors) and re_match_collaboration.findall(';'.join(ads_authors)):
        return 0.3

    (missing_in_ref, missing_in_ads, matching_authors, first_author_missing
     ) = count_matching_authors(ref_authors, ads_authors)

    # if the first author is missing, apply the factor by which matching authors are discounted
    if first_author_missing:
        matching_authors *= 0.3

    score = (matching_authors - abs(missing_in_ref - missing_in_ads)) / float(len(ads_authors))

    return round(max(0, min(1, score)),2)

def get_year_score(diff):
    """

    :param diff:
    :return:
    """
    if diff <= 1:
        return 1
    if diff <= 2:
        return 0.75
    if diff <= 3:
        return 0.5
    if diff <= 4:
        return 0.25
    return 0

re_match_arXiv = re.compile(r'(\d\d\d\darXiv.*)')
def get_matches(source_bibcode, abstract, title, author, year, doi, matched_docs):
    """

    :param source_bibcode:
    :param abstract:
    :param title:
    :param author:
    :param year:
    :param doi:
    :param matched_docs:
    :return:
    """
    results = []
    for doc in matched_docs:
        match_bibcode = doc.get('bibcode', '')
        match_abstract = doc.get('abstract', '')
        match_title = strip_latex_html(' '.join(doc.get('title', [])))
        match_author = doc.get('author_norm', [])
        match_year = doc.get('year', None)
        match_doi = doc.get('doi', [])
        match_identifier = doc.get('identifier', [])

        if abstract.lower() != 'not available':
            scores = [
                fuzz.token_set_ratio(abstract, match_abstract) / 100.0,
                fuzz.partial_ratio(title, match_title) / 100.0,
                get_author_score(author, match_author),
                get_year_score(abs(int(match_year) - int(year)))
            ]
            confidence = confidence_model.predict(scores)
        else:
            scores = [
                0,
                fuzz.partial_ratio(title, match_title) / 100.0,
                get_author_score(author, match_author),
                get_year_score(abs(int(match_year) - int(year)))
            ]
            # not many records with no abstract, hence not possible to train a network for when there are only
            # three scores, the best approach is to take the sum of weighted similarity scores for the three scores
            # with the author weighted more importantly
            confidence = round(scores[1] * 0.3 + scores[1] * 0.4 + scores[2] * 0.3, 2)

        # even if confidence is very low, but doi matches, move it through
        if confidence < 0.01 and doi not in match_doi:
            continue
        # see if either of these bibcodes have already been matched
        prev_match = get_a_record(source_bibcode, match_bibcode)
        if prev_match:
            prev_bibcodes = [prev_match['source_bibcode'], prev_match['matched_bibcode']]
            # if prev record is the current match and the bibcode has changed in the meantime
            if prev_match['source_bibcode'] in match_identifier or prev_match['matched_bibcode'] in match_identifier:
                prev_bibcodes += match_identifier

            # current confidence is without the doi score, hence if the prev match was saved with doi score take it out
            prev_confidence = prev_match['confidence'] if prev_match['confidence'] < DOI_CONFIDENCE_SCORE else \
                              prev_match['confidence'] - DOI_CONFIDENCE_SCORE

            # is it the same record being matched again
            if source_bibcode in prev_bibcodes and match_bibcode in prev_bibcodes and abs(prev_confidence - confidence) < 0.1:
                # return the confidence that is recorded in db
                confidence = prev_confidence

            # if there was a match, see if the confidence is higher then the current match
            # if yes, ignore current match
            elif (match_bibcode in prev_bibcodes or source_bibcode in prev_bibcodes) and prev_confidence > confidence:
                continue

        results.append({'source_bibcode': source_bibcode, 'matched_bibcode': match_bibcode,
                        'confidence': confidence, 'matched': int(confidence > 0.5),
                        'scores': {'abstract':scores[0], 'title': scores[1], 'author': scores[2], 'year': scores[3]}})

    if len(results) == 0:
        return []

    if len(results) == 1:
        if results[0]['matched']:
            add_a_record(DocMatch(results[0]['source_bibcode'], results[0]['matched_bibcode'], results[0]['confidence']))
        return results

    # if multiple records are returned, make sure highest is at the top, then remove any records that have confidence difference with the largest > 0.5
    results = sorted(results, key=lambda x: x['confidence'], reverse=True)
    results = [results[0]] + [result for result in results[1:] if (results[0]['confidence'] - result['confidence']) < 0.5]
    return results

def get_doi_match(source_bibcode, abstract, title, author, year, doi, matched_docs):
    """

    :param source_bibcode:
    :param abstract:
    :param title:
    :param author:
    :param year:
    :param doi:
    :param matched_docs:
    :return:
    """
    results = get_matches(source_bibcode, abstract, title, author, year, doi, matched_docs)
    # need to have a high confidence, otherwise the doi was wrong
    if len(results) == 1:
        # add doi score of 1. keep significant digits fixed.
        results[0]['confidence'] = float('%.7g' % (DOI_CONFIDENCE_SCORE + results[0]['confidence']))
        results[0].get('scores', {}).update({'doi': 1.0})
        return results
    return []

def get_illegal_char_regex():
    """
    Returns an re object to find unicode characters illegal in XML

    :return:
    """
    illegal_unichrs = [ (0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x84), (0x86, 0x9F),
        (0xD800, 0xDFFF), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF),
        (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
        (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
        (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
        (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
        (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
        (0x10FFFE, 0x10FFFF) ]
    illegal_ranges = ["%s-%s" % (chr(low), chr(high))
        for (low, high) in illegal_unichrs
        if low < sys.maxunicode]
    return re.compile(u'[%s]' % u''.join(illegal_ranges))
ILLEGALCHARSREGEX = get_illegal_char_regex()

ILLEGAL_XML = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
              u'|' + \
              u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
              (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
               chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
               chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
              )
def remove_control_chars(input, strict=False):
    """

    :param input:
    :param strict:
    :return:
    """
    input = re.sub(ILLEGAL_XML, "", input)
    if not strict:
        # map all whitespace to single blank
        input = re.sub(r'\s+', ' ', input)
    # now remove control characters
    input = re.sub(r"[\x01-\x08\x0B-\x1F\x7F]", "", input)
    return input

re_latex_math = re.compile(r'(\$[^$]*\$)')
re_html_entity = re.compile(r'(<SUB>.*</SUB|<SUP>.*</SUP>)', re.IGNORECASE)
re_escape = re.compile(r'(\\\s*\w+|\\\s*\W+)\b')
def strip_latex_html(input):
    """

    :param input:
    :return:
    """
    output = re_latex_math.sub('', input)
    output = re_html_entity.sub('', output)
    output = re_escape.sub('', output)
    return output

def clean_data(input):
    """

    :param input:
    :return:
    """
    # check if there are invalid unicode characters
    if ILLEGALCHARSREGEX.search(input):
        # strip illegal stuff but keep newlines
        current_app.logger.error('Illegal unicode character in found %s' %input)
        input = remove_control_chars(input).strip()

    output = input.replace(' \n', '').replace('\n', '').replace(' <P/>', '').rstrip('\\')
    output = output.strip().replace('"', '')

    # remove any latex or html tags
    output = strip_latex_html(output)

    return output

def sub_entity(match):
    """

    :param match:
    :return:
    """
    unicode_dict = current_app.config['ORACLE_SERVICE_UNICODE_CONVERSION']

    key = match.group(1)
    if unicode_dict.get(key, None) is not None:
        result = eval("u'\\u%04x'" % unicode_dict[key])
        return result
    return None


RE_ENTITY = re.compile(r'&([^#][^; ]+?);')
def to_unicode(input):
    """

    :param input:
    :return:
    """
    retstr = RE_ENTITY.sub(sub_entity, input)
    return retstr


CONTROL_CHAR_RE = re.compile(r'[%s]' % re.escape(''.join(map(chr, list(range(0,32)) + list(range(127,160))))))
def remove_control_chars_author(input):
    """

    :param input:
    :return:
    """
    return CONTROL_CHAR_RE.sub('', input)

def encode_author(author):
    """

    :param author:
    :return:
    """
    author = lxml.html.fromstring(author).text
    if isinstance(author, str):
        return unidecode.unidecode(remove_control_chars_author(to_unicode(author)))
    return author

RE_INITIAL = re.compile(r'\. *(?!,)')
def format_author(author):
    """

    :param author:
    :return:
    """
    author = RE_INITIAL.sub('. ', author)
    # Strip potentially disastrous semicolons.
    return author.strip().strip(';')