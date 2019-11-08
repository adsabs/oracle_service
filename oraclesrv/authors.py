import editdistance
import re


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
        # otherwise if ref_authors are firstname lastname,...
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

    normalizer = float(len(ads_authors))

    # if the first author is missing, apply the factor by which matching authors are discounted
    if first_author_missing:
        matching_authors *= 0.3

    if normalizer != 0:
        score = (matching_authors - missing_in_ads) / normalizer
    else:
        score = 0

    return max(0, min(1, score))

