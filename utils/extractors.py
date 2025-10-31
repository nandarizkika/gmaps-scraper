"""
Utility functions for extracting data from Google Maps
"""
import re
from typing import Optional, Tuple


def extract_coordinates_from_link(link: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract latitude and longitude from Google Maps link
    
    Args:
        link: Google Maps URL
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found
    """
    try:
        # Pattern 1: !8m2!3d[latitude]!4d[longitude]
        pattern1 = r'!8m2!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'
        match = re.search(pattern1, link)
        
        if match and len(match.groups()) == 2:
            latitude = float(match.group(1))
            longitude = float(match.group(2))
            return latitude, longitude
        
        # Pattern 2: @[latitude],[longitude]
        pattern2 = r'@(-?\d+\.\d+),(-?\d+\.\d+)'
        match = re.search(pattern2, link)
        
        if match and len(match.groups()) == 2:
            latitude = float(match.group(1))
            longitude = float(match.group(2))
            return latitude, longitude
        
        return None, None
        
    except Exception as e:
        print(f"Error extracting coordinates: {e}")
        return None, None


def parse_address(address: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse Indonesian address into components
    
    Args:
        address: Full address string
        
    Returns:
        Tuple of (subdistrict, district, city, province, zip_code)
    """
    if not address:
        return None, None, None, None, None
    
    subdistrict = None
    district = None
    city = None
    province = None
    zip_code = None
    
    try:
        # Extract ZIP code (5 digits)
        zip_match = re.search(r'\b\d{5}\b', address)
        if zip_match:
            zip_code = zip_match.group(0)
        
        # Extract province (extended list)
        provinces = [
            'DKI Jakarta', 'Daerah Khusus Ibukota Jakarta',
            'Jawa Barat', 'Jawa Tengah', 'Jawa Timur',
            'Banten', 'Yogyakarta', 'D.I. Yogyakarta',
            'Sumatera Utara', 'Sumatera Selatan', 'Sumatera Barat',
            'Riau', 'Kepulauan Riau', 'Jambi', 'Bengkulu', 
            'Lampung', 'Bangka Belitung', 'Aceh',
            'Kalimantan Timur', 'Kalimantan Selatan', 'Kalimantan Barat',
            'Kalimantan Tengah', 'Kalimantan Utara',
            'Sulawesi Selatan', 'Sulawesi Utara', 'Sulawesi Tengah',
            'Sulawesi Tenggara', 'Sulawesi Barat', 'Gorontalo',
            'Bali', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur',
            'Papua', 'Papua Barat', 'Papua Selatan', 'Papua Tengah',
            'Maluku', 'Maluku Utara'
        ]
        
        # Sort by length (longest first) to match specific names before generic ones
        provinces.sort(key=len, reverse=True)
        
        for prov in provinces:
            if prov.lower() in address.lower():
                province = prov
                break
        
        # Extract city (Kota/Kabupaten)
        city_patterns = [
            r'(?:Kota|Kab\.|Kabupaten)\s+([^,\n]+?)(?:,|\n|$)',
            r'(?:Jakarta|Bandung|Surabaya|Medan|Semarang|Makassar|Palembang|Tangerang|Depok|Bekasi|Bogor)\s+(?:Selatan|Utara|Barat|Timur|Pusat|Kota)?'
        ]
        
        for pattern in city_patterns:
            city_match = re.search(pattern, address, re.IGNORECASE)
            if city_match:
                if city_match.lastindex:
                    city = city_match.group(1).strip()
                else:
                    city = city_match.group(0).strip()
                break
        
        # If no city found, try common city names
        if not city:
            cities = [
                'Jakarta Selatan', 'Jakarta Pusat', 'Jakarta Utara', 
                'Jakarta Barat', 'Jakarta Timur', 'Bandung', 'Surabaya', 
                'Medan', 'Semarang', 'Tangerang', 'Bekasi', 'Depok',
                'Bogor', 'Makassar', 'Palembang', 'Batam'
            ]
            for c in cities:
                if c.lower() in address.lower():
                    city = c
                    break
        
        # Extract district (Kecamatan)
        district_patterns = [
            r'(?:Kecamatan|Kec\.)\s+([^,\n]+?)(?:,|\n|$)',
            r'(?:Kec\.?)\s+([A-Z][a-zA-Z\s]+?)(?:,|\n|$)'
        ]
        
        for pattern in district_patterns:
            district_match = re.search(pattern, address, re.IGNORECASE)
            if district_match:
                district = district_match.group(1).strip()
                break
        
        # Extract subdistrict/kelurahan (before district/kecamatan)
        subdistrict_patterns = [
            r'(?:Kelurahan|Kel\.)\s+([^,\n]+?)(?:,|\n|$)',
            r'(?:Desa)\s+([^,\n]+?)(?:,|\n|$)'
        ]
        
        for pattern in subdistrict_patterns:
            subdist_match = re.search(pattern, address, re.IGNORECASE)
            if subdist_match:
                subdistrict = subdist_match.group(1).strip()
                break
        
        # If no explicit subdistrict marker, try to infer from address structure
        # Indonesian address format: Street, Subdistrict, District, City, Province, ZIP
        if not subdistrict:
            # Split by comma and try to identify parts
            parts = [p.strip() for p in address.split(',')]
            
            # Filter out parts that are definitely not subdistrict
            potential_subdistrict = []
            for i, part in enumerate(parts):
                # Skip if it's a known city or province
                if city and city.lower() in part.lower():
                    continue
                if province and province.lower() in part.lower():
                    continue
                # Skip if it contains "Kota" or "Kabupaten" 
                if re.search(r'\b(Kota|Kabupaten|Kab\.)\b', part, re.IGNORECASE):
                    continue
                # Skip if it's just a ZIP code
                if re.match(r'^\d{5}$', part.strip()):
                    continue
                # Skip if it looks like a street address (starts with Jl., Jalan, etc)
                if re.match(r'^(Jl\.?|Jalan|Gang|Gg\.)', part.strip(), re.IGNORECASE):
                    continue
                # Skip if it contains "Kecamatan" (that's district)
                if re.search(r'\b(Kecamatan|Kec\.)\b', part, re.IGNORECASE):
                    continue
                # If it's a place name (no numbers, reasonable length)
                if len(part) > 3 and not re.search(r'\d{2,}', part):
                    potential_subdistrict.append(part)
            
            # The first potential subdistrict is usually the right one
            # (after street address, before district)
            if potential_subdistrict and len(potential_subdistrict) > 0:
                # If we have district, subdistrict should be before it in the address
                if district:
                    for ps in potential_subdistrict:
                        if address.index(ps) < address.index(district):
                            subdistrict = ps
                            break
                if not subdistrict:
                    subdistrict = potential_subdistrict[0]
        
    except Exception as e:
        print(f"Error parsing address: {e}")
    
    return subdistrict, district, city, province, zip_code


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text"""
    if not text:
        return None
    return text.strip().replace('\n', ' ').replace('\r', '')


def parse_rating(rating_text: Optional[str]) -> Optional[float]:
    """Extract rating from text"""
    if not rating_text:
        return None
    try:
        match = re.search(r'(\d+\.?\d*)', rating_text)
        if match:
            return float(match.group(1))
    except:
        pass
    return None


def parse_reviews_count(reviews_text: Optional[str]) -> Optional[int]:
    """Extract review count from text"""
    if not reviews_text:
        return None
    try:
        # Remove commas and extract number
        number_text = re.sub(r'[^\d]', '', reviews_text)
        if number_text:
            return int(number_text)
    except:
        pass
    return None