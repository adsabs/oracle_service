
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

    re_eprint_bibstems = re.compile(r'^(\d\d\d\d(?:arXiv|acc.phys|adap.org|alg.geom|ao.sci|astro.ph|atom.ph|bayes.an|chao.dyn|chem.ph|cmp.lg|comp.gas|cond.mat|cs|dg.ga|funct.an|gr.qc|hep.ex|hep.lat|hep.ph|hep.th|math|math.ph|mtrl.th|nlin|nucl.ex|nucl.th|patt.sol|physics|plasm.ph|q.alg|q.bio|quant.ph|solv.int|supr.con))')

    def __init__(self, source_bibcode, matched_bibcode, confidence, date=None, source_bibcode_doctype=None):
        """

        :param source_bibcode:
        :param matched_bibcode:
        :param confidence:
        :param date:
        """
        self.eprint_bibcode = self.set_eprint_bibcode(source_bibcode, matched_bibcode, source_bibcode_doctype)
        self.pub_bibcode = self.set_pub_bibcode(self.eprint_bibcode, source_bibcode, matched_bibcode)
        self.confidence = confidence
        self.date = date

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
        if self.re_eprint_bibstems.match(source_bibcode):
            self.eprint_bibcode = source_bibcode
            return self.eprint_bibcode
        if self.re_eprint_bibstems.match(matched_bibcode):
            self.eprint_bibcode = matched_bibcode
            return self.eprint_bibcode

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
