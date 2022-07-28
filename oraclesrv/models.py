
from sqlalchemy import Float, String, Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

# DocMatch is db v1.0
class DocMatch(Base):
    __tablename__ = 'docmatch'
    source_bibcode = Column(String, primary_key=True)
    matched_bibcode = Column(String, primary_key=True)
    confidence = Column(Float)
    date = Column(DateTime, default=func.now())

    def __init__(self, source_bibcode, matched_bibcode, confidence, date):
        """

        :param source_bibcode:
        :param matched_bibcode:
        :param confidence:
        :param date:
        """
        self.source_bibcode = source_bibcode
        self.matched_bibcode = matched_bibcode
        self.confidence = confidence
        self.date = date

    def toJSON(self):
        """

        :return: values formatted as python dict
        """
        return {
            'source_bibcode': self.source_bibcode,
            'matched_bibcode': self.matched_bibcode,
            'confidence': self.confidence,
            'date' : self.date,
        }
