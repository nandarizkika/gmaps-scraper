"""
Data models for Google Maps Scraper

This module contains data structures:
- Place: Represents a scraped business/location
- SearchTask: Represents a search query
"""

from .place import Place, SearchTask

__all__ = ['Place', 'SearchTask']