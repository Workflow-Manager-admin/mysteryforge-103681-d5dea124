# Suspect Finder Database

This container provides the database structure and migration logic for the 'Suspect Finder' application. It is intended to be used by the `suspect_finder_backend` FastAPI application.

## Features

- Manages Crime Cases, Suspects, Clues, Twists, and Solutions
- Uses SQLAlchemy ORM
- Alembic-powered migrations
- Suitable for use as a backend service DB

## Structure

- **models.py**: SQLAlchemy models for Cases, Suspects, Clues, Twists, Solutions
- **db.py**: SQLAlchemy session configuration
- **alembic/**: Migration environment, scripts

## Getting Started

1. Adjust database settings in the `.env` file in the root.
2. Run migrations with Alembic to create schema.

## Alembic Commands

- `alembic upgrade head` &mdash; apply all migrations
- `alembic revision --autogenerate -m "message"` &mdash; generate a new migration (after model change)

## Model Overview

- **Case**: Title, description, crime_scene, solution, one-to-many to Suspect, Clue, Twist
- **Suspect**: Name, description, attributes, belongs to a Case
- **Clue**: Description, type, belongs to a Case
- **Twist**: Description, belongs to a Case
- **Solution**: Summary, how-it-was-solved, belongs to a Case

---
