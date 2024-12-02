
import re

from sqlalchemy import Float, String, Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

# DocMatch is db v1.0
class DocMatch(Base):
    __tablename__ = 'docmatch'
    eprint_bibcode = Column(String, primary_key=True)
    pub_bibcode = Column(String, primary_key=True)
    confidence = Column(Float, primary_key=False)
    date = Column(DateTime, default=func.now())

    def __init__(self, source_bibcode, matched_bibcode, confidence, eprint_bibstems, date=None, source_bibcode_doctype=None):
        """

        :param source_bibcode:
        :param matched_bibcode:
        :param confidence:
        :param eprint_bibstems:
        :param date:
        :param source_bibcode_doctype:
        """
        self.init_eprint_regular_expressions(eprint_bibstems)
        self.eprint_bibcode = self.set_eprint_bibcode(source_bibcode, matched_bibcode, source_bibcode_doctype)
        self.pub_bibcode = self.set_pub_bibcode(self.eprint_bibcode, source_bibcode, matched_bibcode)
        self.confidence = confidence
        self.date = date

    def init_eprint_regular_expressions(self, eprint_bibstems):
        """
        init the regular expressions to identify the eprints

        :param eprint_bibstems:
        :return:
        """
        for bibstem in eprint_bibstems:
            if bibstem['name'] == 'arXiv':
                self.re_arXiv_eprint_bibstems = re.compile(bibstem['pattern'])
            elif bibstem['name'] == 'Earth Science':
                self.re_earth_science_eprint_bibstems = re.compile(bibstem['pattern'])

    def set_eprint_bibcode(self, source_bibcode, matched_bibcode, source_bibcode_doctype):
        """

        :param source_bibcode:
        :param matched_bibcode:
        :param source_bibcode_doctype:
        :return:
        """
        if source_bibcode_doctype:
            if source_bibcode_doctype == 'eprint':
                self.eprint_bibcode = source_bibcode
                return self.eprint_bibcode
            if source_bibcode_doctype == 'article':
                self.eprint_bibcode = matched_bibcode
                return self.eprint_bibcode

        # if no doctype provided, attempt to identify the type from bibcode
        if self.re_arXiv_eprint_bibstems.match(source_bibcode):
            self.eprint_bibcode = source_bibcode
            return self.eprint_bibcode
        if self.re_arXiv_eprint_bibstems.match(matched_bibcode):
            self.eprint_bibcode = matched_bibcode
            return self.eprint_bibcode
        if self.re_earth_science_eprint_bibstems.match(source_bibcode):
            self.eprint_bibcode = source_bibcode
            return self.eprint_bibcode
        if self.re_earth_science_eprint_bibstems.match(matched_bibcode):
            self.eprint_bibcode = matched_bibcode
            return self.eprint_bibcode

        # unable to detect eprint match
        self.eprint_bibcode = ''
        return self.eprint_bibcode

    def set_pub_bibcode(self, eprint_bibcode, source_bibcode, matched_bibcode):
        """

        :param eprint_bibcode:
        :param source_bibcode:
        :param matched_bibcode:
        :return:
        """
        if eprint_bibcode == source_bibcode:
            self.pub_bibcode = matched_bibcode
            return self.pub_bibcode
        if eprint_bibcode == matched_bibcode:
            self.pub_bibcode = source_bibcode
            return self.pub_bibcode
        self.pub_bibcode = ''
        return self.pub_bibcode

    def toJSON(self):
        """

        :return: values formatted as python dict
        """
        return {
            'eprint_bibcode': self.eprint_bibcode,
            'pub_bibcode': self.pub_bibcode,
            'confidence': self.confidence,
            'date' : self.date,
        }



class ConfidenceLookup(Base):
    __tablename__ = 'confidence_lookup'
    source = Column(String, primary_key=True)
    confidence = Column(Float, primary_key=False)

    def __init__(self, source, confidence):
        """

        :param source:
        :param confidence:
        """
        self.source = source
        self.confidence = confidence

    def toJSON(self):
        """

        :return: values formatted as python dict
        """
        return {
            'source': self.source,
            'confidence': self.confidence,
        }



class EPrintBibstemLookup(Base):
    __tablename__ = 'eprint_bibstem_lookup'
    name = Column(String, primary_key=True)
    pattern = Column(String, primary_key=False)

    def __init__(self, name, pattern):
        """

        :param name:
        :param pattern:
        """
        self.name = name
        self.pattern = pattern

    def toJSON(self):
        """

        :return: values formatted as python dict
        """
        return {
            'name': self.name,
            'pattern': self.pattern,
        }
