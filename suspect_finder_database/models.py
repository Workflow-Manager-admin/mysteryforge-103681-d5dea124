"""
Database models for Suspect Finder.
Defines Case, Suspect, Clue, Twist, and Solution tables using SQLAlchemy ORM.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    JSON
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# PUBLIC_INTERFACE
class Case(Base):
    """Represents a mystery case."""
    __tablename__ = 'cases'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    crime_scene = Column(Text, nullable=False)

    # One-to-many relations
    suspects = relationship("Suspect", back_populates="case", cascade="all, delete")
    clues = relationship("Clue", back_populates="case", cascade="all, delete")
    twists = relationship("Twist", back_populates="case", cascade="all, delete")
    solution = relationship("Solution", uselist=False, back_populates="case", cascade="all, delete")

# PUBLIC_INTERFACE
class Suspect(Base):
    """A suspect for a given case, with attributes for gameplay."""
    __tablename__ = 'suspects'

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    attributes = Column(JSON, nullable=True)  # Arbitrary attributes (personality, motive, etc.)

    case = relationship("Case", back_populates="suspects")

# PUBLIC_INTERFACE
class Clue(Base):
    """A clue related to a specific case."""
    __tablename__ = 'clues'

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    clue_type = Column(String(64), nullable=False)  # e.g. physical, alibi, conversation
    description = Column(Text, nullable=False)

    case = relationship("Case", back_populates="clues")

# PUBLIC_INTERFACE
class Twist(Base):
    """A twist/contradiction related to a case, enhances gameplay."""
    __tablename__ = 'twists'

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    description = Column(Text, nullable=False)

    case = relationship("Case", back_populates="twists")

# PUBLIC_INTERFACE
class Solution(Base):
    """The solution record for a case."""
    __tablename__ = 'solutions'

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id'), unique=True)
    summary = Column(Text, nullable=False)
    how_solved = Column(Text, nullable=True)

    case = relationship("Case", back_populates="solution")
