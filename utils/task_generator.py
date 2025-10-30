"""
Utility for generating search tasks from keywords and locations
"""
import pandas as pd
from typing import List
from models.place import SearchTask


class TaskGenerator:
    """Generate search tasks from keywords and locations"""
    
    @staticmethod
    def generate_tasks(
        keywords: List[str],
        locations: List[str],
        max_results_per_task: int = 1000
    ) -> List[SearchTask]:
        """
        Generate search tasks from keywords and locations
        
        Args:
            keywords: List of search keywords (e.g., ["warung kelontong", "minimarket"])
            locations: List of locations (e.g., ["Kebayoran Baru", "Cilandak"])
            max_results_per_task: Maximum results to collect per task
            
        Returns:
            List of SearchTask objects
        """
        tasks = []
        
        for keyword in keywords:
            for location in locations:
                task = SearchTask(
                    keyword=keyword,
                    location=location,
                    max_results=max_results_per_task
                )
                tasks.append(task)
        
        return tasks
    
    @staticmethod
    def generate_from_dataframe(
        keywords_df: pd.DataFrame,
        locations_df: pd.DataFrame,
        max_results_per_task: int = 1000
    ) -> List[SearchTask]:
        """
        Generate tasks from DataFrames (for Streamlit app)
        
        Supports flexible location columns:
        - Option 1: subdistrict, district, city (most specific)
        - Option 2: district, city
        - Option 3: location (single column)
        
        Args:
            keywords_df: DataFrame with 'keyword' column
            locations_df: DataFrame with location columns
            max_results_per_task: Maximum results per task
            
        Returns:
            List of SearchTask objects
        """
        tasks = []
        keywords = keywords_df['keyword'].tolist()
        
        for keyword in keywords:
            for _, row in locations_df.iterrows():
                # Build location string based on available columns
                location_parts = []
                
                subdistrict = str(row.get('subdistrict', '')).strip() if 'subdistrict' in row else ''
                district = str(row.get('district', '')).strip() if 'district' in row else ''
                city = str(row.get('city', '')).strip() if 'city' in row else ''
                
                # Add parts that exist and are not empty
                if subdistrict and subdistrict.lower() != 'nan':
                    location_parts.append(subdistrict)
                if district and district.lower() != 'nan':
                    location_parts.append(district)
                if city and city.lower() != 'nan':
                    location_parts.append(city)
                
                # If no parts, check for single 'location' column
                if not location_parts and 'location' in row:
                    location = str(row['location']).strip()
                else:
                    location = ", ".join(location_parts)
                
                task = SearchTask(
                    keyword=keyword,
                    location=location,
                    subdistrict=subdistrict if subdistrict.lower() != 'nan' else '',
                    district=district if district.lower() != 'nan' else '',
                    city=city if city.lower() != 'nan' else '',
                    max_results=max_results_per_task
                )
                tasks.append(task)
        
        return tasks
    
    @staticmethod
    def generate_district_tasks(
        keywords: List[str],
        city: str,
        districts: List[str],
        max_results_per_task: int = 1000
    ) -> List[SearchTask]:
        """
        Generate tasks for districts in a city
        
        Args:
            keywords: List of keywords to search
            city: City name (e.g., "Jakarta Selatan")
            districts: List of district names (e.g., ["Kebayoran Baru", "Cilandak"])
            max_results_per_task: Maximum results per task
            
        Returns:
            List of SearchTask objects
        """
        tasks = []
        
        for keyword in keywords:
            for district in districts:
                location = f"{district}, {city}"
                task = SearchTask(
                    keyword=keyword,
                    location=location,
                    district=district,
                    city=city,
                    max_results=max_results_per_task
                )
                tasks.append(task)
        
        return tasks
    
    @staticmethod
    def generate_subdistrict_tasks(
        keywords: List[str],
        city: str,
        district: str,
        subdistricts: List[str],
        max_results_per_task: int = 1000
    ) -> List[SearchTask]:
        """
        Generate tasks for subdistricts (kelurahan) in a district
        
        Args:
            keywords: List of keywords to search
            city: City name (e.g., "Jakarta Selatan")
            district: District name (e.g., "Kebayoran Baru")
            subdistricts: List of subdistrict names (e.g., ["Gunung", "Melawai"])
            max_results_per_task: Maximum results per task
            
        Returns:
            List of SearchTask objects
        """
        tasks = []
        
        for keyword in keywords:
            for subdistrict in subdistricts:
                location = f"{subdistrict}, {district}, {city}"
                task = SearchTask(
                    keyword=keyword,
                    location=location,
                    subdistrict=subdistrict,
                    district=district,
                    city=city,
                    max_results=max_results_per_task
                )
                tasks.append(task)
        
        return tasks


# Predefined district lists
JAKARTA_SELATAN_DISTRICTS = [
    "Kebayoran Baru", "Kebayoran Lama", "Pesanggrahan",
    "Cilandak", "Pasar Minggu", "Jagakarsa",
    "Mampang Prapatan", "Pancoran", "Tebet", "Setiabudi"
]

JAKARTA_PUSAT_DISTRICTS = [
    "Tanah Abang", "Menteng", "Senen", "Johar Baru",
    "Cempaka Putih", "Kemayoran", "Sawah Besar", "Gambir"
]

JAKARTA_UTARA_DISTRICTS = [
    "Penjaringan", "Pademangan", "Tanjung Priok",
    "Koja", "Kelapa Gading", "Cilincing"
]

JAKARTA_TIMUR_DISTRICTS = [
    "Matraman", "Pulo Gadung", "Jatinegara", "Cakung",
    "Duren Sawit", "Kramat Jati", "Makasar", "Pasar Rebo",
    "Ciracas", "Cipayung"
]

JAKARTA_BARAT_DISTRICTS = [
    "Tambora", "Taman Sari", "Cengkareng", "Grogol Petamburan",
    "Kebon Jeruk", "Kalideres", "Palmerah", "Kembangan"
]

# Subdistrict lists
KEBAYORAN_BARU_SUBDISTRICTS = [
    "Gunung", "Melawai", "Kramat Pela", "Selong", "Rawa Barat",
    "Senayan", "Cipete Selatan", "Pulo", "Petogogan", "Gandaria Selatan"
]

KEBAYORAN_LAMA_SUBDISTRICTS = [
    "Grogol Utara", "Grogol Selatan", "Cipulir",
    "Kebayoran Lama Utara", "Kebayoran Lama Selatan", "Pondok Pinang"
]

CILANDAK_SUBDISTRICTS = [
    "Cilandak Barat", "Lebak Bulus", "Pondok Labu",
    "Cipete Utara", "Gandaria Utara"
]

PANCORAN_SUBDISTRICTS = [
    "Pancoran", "Kalibata", "Rawa Jati",
    "Duren Tiga", "Cikoko", "Pengadegan"
]

TEBET_SUBDISTRICTS = [
    "Tebet Timur", "Tebet Barat", "Menteng Dalam",
    "Kebon Baru", "Bukit Duri", "Manggarai", "Manggarai Selatan"
]