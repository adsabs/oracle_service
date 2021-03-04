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

def get_confidence_score(scores):
    """

    :param scores: list of scores for [abstract, title, author, year]
    :return:
    """
    confidence = sum([1 for score in scores if score >= 0.8]) >= len(scores) - 1 or \
                 sum(scores[0:2]) >= 1.8
    if confidence:
        return 1

    confidence = sum(scores[0:2]) >= 1.5  and sum(scores[2:4]) >= 1   or \
                 sum(scores[0:2]) >= 1.35 and sum(scores[2:4]) == 1.5 or \
                 sum(scores[0:2]) >= 1.25 and sum(scores[2:4]) == 1.75
    if confidence:
        return 0.67

    confidence = (sum(scores[0:2]) >= 1.25 and sum(scores[2:4]) >= 1.5) or \
                 (sum(scores[0:2]) >= 1    and sum(scores[2:4]) >= 1.75)
    if confidence:
        return 0.5

    confidence = sum(scores[0:2]) >= 1 and sum(scores[2:4]) >= 1 and scores[2] != 0
    if confidence:
        return 0.33

    return 0

re_match_arXiv = re.compile(r'(\d\d\d\darXiv.*)')
def score_match(abstract, title, author, year, matched_docs):
    """

    :param abstract:
    :param title:
    :param author:
    :param year:
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

        scores = []
        if abstract.lower() != 'not available':
            scores.append(fuzz.token_set_ratio(abstract, match_abstract)/100.0)
        scores.append(fuzz.partial_ratio(title, match_title)/100.0)
        scores.append(get_author_score(author, match_author))
        scores.append(get_year_score(abs(int(match_year)-int(year))))

        confidence = get_confidence_score(scores)
        if confidence > 0:
            result = {'bibcode': match_bibcode, 'confidence': confidence,
                      'scores': {'abstract':scores[0], 'title': scores[1], 'author': scores[2], 'year': scores[3]}}
            results.append(result)

    # if multiple records are returned, push the one with highest score up
    return sorted(results,
                  key=lambda x: (x['confidence'],
                                 x['scores'].get('abstract') + x['scores'].get('title') + x['scores'].get('author'),
                                 x['scores'].get('year')), reverse=True)

def score_match_doi(doi, abstract, title, author, year, matched_docs):
    """

    :param doi:
    :param abstract:
    :param title:
    :param author:
    :param year:
    :param matched_docs:
    :return:
    """
    results = score_match(abstract, title, author, year, matched_docs)
    try:
        matched_doi = matched_docs[0].get('doi', [])[0]
        if matched_doi == doi:
            confidence = results[0].get('confidence', None)
            abstract_score = results[0].get('scores', {}).get('abstract', 0)
            # possibly the doi is wrong, so try similar query
            if confidence != 1 or abstract_score == 0:
                return []
            confidence = round(old_div((confidence + 1.0),2), 2)
            confidence = int(confidence) if float(confidence).is_integer() else confidence
            results[0].update({'confidence': confidence})
            results[0].get('scores', {}).update({'doi':1.0})
            return results
        results[0].get('scores', {}).update({'doi': 0.0})
    except:
        pass
    return results

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

    output = input.replace(' \n', '').replace('\n', '')
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