import sys
import editdistance
import re

from fuzzywuzzy import fuzz
import lxml.html
import unidecode

from flask import current_app

def count_matching_authors(ref_authors, ads_authors):
    """
    returns statistics on the authors matching between ref_authors
    and ads_authors.

    ads_authors is supposed to a list of ADS-normalized author strings.
    ref_authors must be a string, where we try to assume as little as
    possible about the format.  Full first names will kill this function,
    though.

    What's returned is a tuple of (missing_in_ref,
        missing_in_ads, matching_authors, first_author_missing).

    No initials verification takes place here, case is folded, everything
    is supposed to have been dumbed down to ASCII by ADS conventions.

    :param ref_authors:
    :param ads_authors:
    :return:
    """
    missing_in_ref, missing_in_ads, matching_authors, first_author_missing = 0, 0, 0, False

    try:
        ads_authors_lastname = [a.split(",")[0].strip() for a in ads_authors]
        # if the ref_authors are lastname, firstname;...
        if ';' in ref_authors:
            ref_authors_lastname = [a.split(',')[0].strip() for a in ref_authors.split(";")]
        # else if there is only one author
        elif ref_authors.count(",") == 1:
            ref_authors_lastname = [ref_authors.split(',')[0].strip()]
        # finally if ref_authors are firstname lastname,...
        else:
            ref_authors_lastname = [a.split()[-1].strip() for a in ref_authors.split(",")]

        ads_first_author = ads_authors_lastname[0]
        first_author_missing = ads_first_author not in ref_authors

        different = []
        for ads_auth in ads_authors_lastname:
            if ads_auth in ref_authors or (
                            " " in ads_auth and ads_auth.split()[-1] in ref_authors):
                matching_authors += 1
            else:
                # see if there is actually no match (check for misspelling here)
                # difference of <30% is indication of misspelling
                misspelled = False
                for ref_auth in ref_authors_lastname:
                    N_max = max(len(ads_auth), len(ref_auth))
                    distance = (N_max - float(editdistance.eval(ads_auth, ref_auth))) / N_max
                    if distance > 0.7:
                        different.append(ref_auth)
                        misspelled = True
                        break
                if not misspelled:
                    missing_in_ref += 1

        # Now try to figure out if the reference has additional authors
        # (we assume ADS author lists are complete)
        ads_authors_lastname_pattern = "|".join(ads_authors_lastname)

        # just to be on the safe side, nuke some RE characters that sometimes
        # sneak into ADS author lists (really, the respective records should
        # be fixed)
        ads_authors_lastname_pattern = re.sub("[()]", "", ads_authors_lastname_pattern)

        wordsNotInADS = re.findall(r"\w+", re.sub(ads_authors_lastname_pattern, "", '; '.join(ref_authors_lastname)))
        # remove recognized misspelled authors
        wordsNotInADS = [word for word in wordsNotInADS if word not in different]
        missing_in_ads = len(wordsNotInADS)
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
        return
    (missing_in_ref, missing_in_ads, matching_authors, first_author_missing
     ) = count_matching_authors(ref_authors, ads_authors)

    # if the first author is missing, apply the factor by which matching authors are discounted
    if first_author_missing:
        matching_authors *= 0.3

    score = (matching_authors - abs(missing_in_ref - missing_in_ads)) / float(len(ads_authors))

    return max(0, min(1, score))

def passing_score(scores):
    """

    :param scores:
    :return:
    """
    return sum([1 for score in scores if score >= 0.8]) >= len(scores) - 1

def score_match(abstract, title, author, year, doctype, matched_docs):
    """

    :param abstract:
    :param title:
    :param author:
    :param matched_doc:
    :return:
    """
    doctype_matching_eprint = ['article', 'inproceedings', 'inbook']

    results = []
    for doc in matched_docs:
        match_abstract = doc.get('abstract', '')
        match_title = ' '.join(doc.get('title', []))
        match_author = doc.get('author_norm', [])
        match_year = doc.get('year', None)
        match_doctype = doc.get('doctype', None)

        if (match_doctype == 'eprint' and doctype in doctype_matching_eprint) or ((match_doctype in doctype_matching_eprint and doctype == 'eprint')):
            scores = []
            if abstract.lower() != 'not available':
                scores.append(fuzz.token_set_ratio(abstract, match_abstract)/100.0)
            scores.append(fuzz.partial_ratio(title, match_title)/100.0)
            scores.append(get_author_score(author, match_author))
            scores.append(1 if year and abs(int(match_year)-int(year)) <= 1 else 0)

            if passing_score(scores):
                if len(scores) == 4:
                    results.append({'bibcode': doc.get('bibcode', ''),
                                    'scores': {'abstract':scores[0], 'title': scores[1], 'author': scores[2], 'year': scores[3]}})
                elif len(scores) == 3:
                    results.append({'bibcode': doc.get('bibcode', ''),
                                    'scores': {'title': scores[0], 'author': scores[1], 'year': scores[2]}})

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
    illegal_ranges = ["%s-%s" % (unichr(low), unichr(high))
        for (low, high) in illegal_unichrs
        if low < sys.maxunicode]
    return re.compile(u'[%s]' % u''.join(illegal_ranges))
ILLEGALCHARSREGEX = get_illegal_char_regex()

ILLEGAL_XML = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
              u'|' + \
              u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
              (unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
               unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
               unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
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

    input = input.replace(' \n', '\n').split('\n')

    # this is for abstract
    # if paragraphs so we need to make sure that we keep this information.
    output = ''.join([l.strip() and l.strip() + ' ' or '<P />' for l in input])
    output = output.strip().replace('"', '').replace('$', '').decode('utf_8')

    return output

def sub_entity(mat):
    """

    :param mat:
    :return:
    """
    unicode_dict = current_app.config['ORACLE_SERVICE_UNICODE_CONVERSION']

    key = mat.group(1)
    if unicode_dict.get(key, None) is not None:
        result = eval("u'\\u%04x'" % unicode_dict[key])
        return result
    return None


RE_ENTITY = re.compile('&([^#][^; ]+?);')
def to_unicode(input):
    """

    :param input:
    :return:
    """
    retstr = RE_ENTITY.sub(sub_entity, input)
    return retstr


CONTROL_CHAR_RE = re.compile('[%s]' % re.escape(''.join(map(unichr, range(0,32) + range(127,160)))))
def remove_control_chars(input):
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
    if isinstance(author, unicode):
        return unidecode.unidecode(remove_control_chars(to_unicode(author)))
    return author

RE_INITIAL = re.compile('\. *(?!,)')
def format_author(author):
    """

    :param author:
    :return:
    """
    author = RE_INITIAL.sub('. ', author)
    # Strip potentially disastrous semicolons.
    return author.strip().strip(';')
