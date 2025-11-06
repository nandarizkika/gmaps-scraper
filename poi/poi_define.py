import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from geopy.distance import geodesic
import folium
from folium.plugins import MarkerCluster
import matplotlib.pyplot as plt
from tqdm import tqdm
from scipy.spatial.distance import cdist

class POIDetector:
    def __init__(self, df, lat_col='latitude', lon_col='longitude'):
        """
        Initialize POI Detector
        
        Parameters:
        - df: DataFrame with merchant data
        - lat_col: Column name for latitude
        - lon_col: Column name for longitude
        """
        self.df = df.copy()
        self.lat_col = lat_col
        self.lon_col = lon_col
        self.pois = None
        
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance in meters between two points"""
        return geodesic((lat1, lon1), (lat2, lon2)).meters
    
    def find_dense_centers(self, min_merchants=30, search_radius=100):
        """
        Find potential POI centers based on density
        
        Parameters:
        - min_merchants: Minimum merchants to consider as potential center
        - search_radius: Initial search radius for density
        """
        potential_centers = []
        
        
        for idx, row in tqdm(self.df.iterrows(), total=len(self.df), desc="Finding dense areas"):
            lat, lon = row[self.lat_col], row[self.lon_col]
            
            
            distances = self.df.apply(
                lambda r: self.haversine_distance(lat, lon, r[self.lat_col], r[self.lon_col]), 
                axis=1
            )
            
            
            nearby_count = (distances <= search_radius).sum()
            
            if nearby_count >= min_merchants:
                potential_centers.append({
                    'lat': lat,
                    'lon': lon,
                    'density': nearby_count,
                    'merchant_idx': idx
                })
        
        return pd.DataFrame(potential_centers)
    
    def detect_pois_density_based(self, radius_meters=250, min_merchants=30, method='density_peaks'):
        """
        Detect POIs based on density with strict radius constraint from center
        
        Parameters:
        - radius_meters: Maximum distance from POI center (strict constraint)
        - min_merchants: Minimum number of merchants in POI
        - method: 'density_peaks' or 'kmeans_refined'
        """
        print(f"\nDetecting POIs with radius={radius_meters}m, min_merchants={min_merchants}")
        
        
        self.df['poi_cluster'] = -1
        self.df['distance_to_center'] = np.nan
        
        if method == 'density_peaks':
            pois_list = self._detect_density_peaks(radius_meters, min_merchants)
        else:
            pois_list = self._detect_kmeans_refined(radius_meters, min_merchants)
        
        self.pois = pd.DataFrame(pois_list)
        
        
        print(f"\nPOI Detection Results:")
        print(f"- Radius: {radius_meters} meters (strict from center)")
        print(f"- Min merchants: {min_merchants}")
        print(f"- Total POIs found: {len(self.pois)}")
        print(f"- Total merchants in POIs: {len(self.df[self.df['poi_cluster'] != -1])}")
        print(f"- Merchants not in POIs: {len(self.df[self.df['poi_cluster'] == -1])}")
        
        if len(self.pois) > 0:
            print(f"\nPOI Details:")
            for _, poi in self.pois.iterrows():
                print(f"  {poi['poi_id']}: {poi['merchant_count']} merchants, "
                      f"max distance: {poi['max_distance']:.0f}m")
        
        return self.pois
    
    def _detect_density_peaks(self, radius_meters, min_merchants):
        """Detect POIs using density peak finding"""
        pois_list = []
        assigned_merchants = set()
        
        
        density_scores = []
        for idx, row in self.df.iterrows():
            if idx not in assigned_merchants:
                lat, lon = row[self.lat_col], row[self.lon_col]
                
                
                distances = self.df.apply(
                    lambda r: self.haversine_distance(lat, lon, r[self.lat_col], r[self.lon_col]), 
                    axis=1
                )
                
                nearby_mask = (distances <= radius_meters) & (~self.df.index.isin(assigned_merchants))
                nearby_count = nearby_mask.sum()
                
                if nearby_count >= min_merchants:
                    density_scores.append({
                        'idx': idx,
                        'lat': lat,
                        'lon': lon,
                        'density': nearby_count,
                        'nearby_indices': self.df[nearby_mask].index.tolist()
                    })
        
        
        density_scores = sorted(density_scores, key=lambda x: x['density'], reverse=True)
        
        poi_id = 0
        for center_candidate in density_scores:
            available_indices = [idx for idx in center_candidate['nearby_indices'] 
                               if idx not in assigned_merchants]
            
            if len(available_indices) >= min_merchants:
                
                poi_merchants = self.df.loc[available_indices]
                
                
                center_lat = poi_merchants[self.lat_col].mean()
                center_lon = poi_merchants[self.lon_col].mean()
                
                
                distances_from_center = poi_merchants.apply(
                    lambda r: self.haversine_distance(
                        center_lat, center_lon, 
                        r[self.lat_col], r[self.lon_col]
                    ), axis=1
                )
                
                
                within_radius = distances_from_center <= radius_meters
                final_merchants = poi_merchants[within_radius]
                
                if len(final_merchants) >= min_merchants:
                    
                    center_lat = final_merchants[self.lat_col].mean()
                    center_lon = final_merchants[self.lon_col].mean()
                    
                    
                    final_distances = final_merchants.apply(
                        lambda r: self.haversine_distance(
                            center_lat, center_lon,
                            r[self.lat_col], r[self.lon_col]
                        ), axis=1
                    )
                    
                    
                    self.df.loc[final_merchants.index, 'poi_cluster'] = poi_id
                    self.df.loc[final_merchants.index, 'distance_to_center'] = final_distances
                    
                    
                    poi_info = {
                        'poi_id': f'POI_{poi_id:03d}',
                        'center_lat': center_lat,
                        'center_lon': center_lon,
                        'merchant_count': len(final_merchants),
                        'max_distance': final_distances.max(),
                        'avg_distance': final_distances.mean(),
                        'min_distance': final_distances.min(),
                        'radius_meters': radius_meters,
                        'min_merchants': min_merchants
                    }
                    
                    
                    if 'subdistrict' in final_merchants.columns:
                        mode_val = final_merchants['subdistrict'].mode()
                        poi_info['subdistrict'] = mode_val.iloc[0] if not mode_val.empty else ''
                    if 'district' in final_merchants.columns:
                                            mode_val = final_merchants['district'].mode()
                                            poi_info['district'] = mode_val.iloc[0] if not mode_val.empty else ''
                    if 'city' in final_merchants.columns:
                        mode_val = final_merchants['city'].mode()
                        poi_info['city'] = mode_val.iloc[0] if not mode_val.empty else ''
                    
                    pois_list.append(poi_info)
                    assigned_merchants.update(final_merchants.index.tolist())
                    poi_id += 1
                            
        return pois_list
    
    def _detect_kmeans_refined(self, radius_meters, min_merchants):
        """Detect POIs using KMeans followed by radius refinement"""
        pois_list = []
        
        
        estimated_clusters = max(1, len(self.df) // (min_merchants * 2))
        
        
        coords = self.df[[self.lat_col, self.lon_col]].values
        kmeans = KMeans(n_clusters=min(estimated_clusters, len(self.df) // min_merchants), 
                       random_state=42, n_init=10)
        kmeans.fit(coords)
        
        
        poi_id = 0
        for cluster_id in range(kmeans.n_clusters):
            cluster_mask = kmeans.labels_ == cluster_id
            cluster_merchants = self.df[cluster_mask]
            
            if len(cluster_merchants) >= min_merchants:
                
                center_lat, center_lon = kmeans.cluster_centers_[cluster_id]
                
                
                distances = self.df.apply(
                    lambda r: self.haversine_distance(
                        center_lat, center_lon,
                        r[self.lat_col], r[self.lon_col]
                    ), axis=1
                )
                
                within_radius = (distances <= radius_meters) & (self.df['poi_cluster'] == -1)
                poi_merchants = self.df[within_radius]
                
                if len(poi_merchants) >= min_merchants:
                    
                    center_lat = poi_merchants[self.lat_col].mean()
                    center_lon = poi_merchants[self.lon_col].mean()
                    
                    
                    final_distances = poi_merchants.apply(
                        lambda r: self.haversine_distance(
                            center_lat, center_lon,
                            r[self.lat_col], r[self.lon_col]
                        ), axis=1
                    )
                    
                    
                    final_mask = final_distances <= radius_meters
                    final_merchants = poi_merchants[final_mask]
                    
                    if len(final_merchants) >= min_merchants:
                        self.df.loc[final_merchants.index, 'poi_cluster'] = poi_id
                        self.df.loc[final_merchants.index, 'distance_to_center'] = final_distances[final_mask]
                        
                        poi_info = {
                            'poi_id': f'POI_{poi_id:03d}',
                            'center_lat': center_lat,
                            'center_lon': center_lon,
                            'merchant_count': len(final_merchants),
                            'max_distance': final_distances[final_mask].max(),
                            'avg_distance': final_distances[final_mask].mean(),
                            'min_distance': final_distances[final_mask].min(),
                            'radius_meters': radius_meters,
                            'min_merchants': min_merchants
                        }
                        
                        
                        if 'subdistrict' in final_merchants.columns:
                            mode_val = final_merchants['subdistrict'].mode()
                            poi_info['subdistrict'] = mode_val.iloc[0] if not mode_val.empty else ''
                        if 'district' in final_merchants.columns:
                            mode_val = final_merchants['district'].mode()
                            poi_info['district'] = mode_val.iloc[0] if not mode_val.empty else ''
                        if 'city' in final_merchants.columns:
                            mode_val = final_merchants['city'].mode()
                            poi_info['city'] = mode_val.iloc[0] if not mode_val.empty else ''
                        
                        pois_list.append(poi_info)
                        poi_id += 1
        
        return pois_list
    
    def visualize_pois(self, save_path='poi_map.html', show_radius=True):
        """Create interactive map visualization of POIs"""
        if self.pois is None or len(self.pois) == 0:
            print("No POIs detected yet. Run detect_pois first.")
            return
        
        
        center_lat = self.df[self.lat_col].mean()
        center_lon = self.df[self.lon_col].mean()
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
        
        
        for _, poi in self.pois.iterrows():
            
            folium.Marker(
                [poi['center_lat'], poi['center_lon']],
                popup=f"""
                <b>{poi['poi_id']}</b><br>
                Merchants: {poi['merchant_count']}<br>
                Max distance: {poi['max_distance']:.0f}m<br>
                Avg distance: {poi['avg_distance']:.0f}m<br>
                Radius: {poi['radius_meters']}m
                """,
                icon=folium.Icon(color='red', icon='star', prefix='fa'),
                tooltip=f"{poi['poi_id']}: {poi['merchant_count']} merchants"
            ).add_to(m)
            
            if show_radius:
                
                folium.Circle(
                    [poi['center_lat'], poi['center_lon']],
                    radius=poi['radius_meters'],
                    color='red',
                    weight=2,
                    fill=True,
                    fillOpacity=0.1,
                    popup=f"{poi['poi_id']} boundary ({poi['radius_meters']}m radius)"
                ).add_to(m)
        
        
        for _, merchant in self.df.iterrows():
            if merchant['poi_cluster'] != -1:
                color = 'blue'
                poi_label = f"POI_{merchant['poi_cluster']:03d}"
                distance_label = f"Distance: {merchant['distance_to_center']:.0f}m"
            else:
                color = 'gray'
                poi_label = 'No POI'
                distance_label = ''
            
            folium.CircleMarker(
                [merchant[self.lat_col], merchant[self.lon_col]],
                radius=3,
                popup=f"Merchant<br>{poi_label}<br>{distance_label}",
                color=color,
                fill=True,
                fillOpacity=0.7,
                weight=1
            ).add_to(m)
        
        
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; z-index:9999; font-size:14px;
                    border:2px solid grey; border-radius: 5px; padding: 10px">
        <p style="margin: 0;"><b>Legend</b></p>
        <p style="margin: 5px;">⭐ POI Center</p>
        <p style="margin: 5px;">🔵 Merchant in POI</p>
        <p style="margin: 5px;">⚫ Merchant not in POI</p>
        <p style="margin: 5px;">⭕ POI Radius</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        m.save(save_path)
        print(f"Map saved to {save_path}")
        
        return m
    
    def get_statistics(self):
        """Get detailed statistics about POIs"""
        if self.pois is None or len(self.pois) == 0:
            print("No POIs detected yet. Run detect_pois first.")
            return pd.Series()
        
        stats = {
            'total_pois': len(self.pois),
            'total_merchants_in_pois': len(self.df[self.df['poi_cluster'] != -1]),
            'total_merchants_outside_pois': len(self.df[self.df['poi_cluster'] == -1]),
            'coverage_percentage': (len(self.df[self.df['poi_cluster'] != -1]) / len(self.df)) * 100,
            'avg_merchants_per_poi': self.pois['merchant_count'].mean(),
            'std_merchants_per_poi': self.pois['merchant_count'].std(),
            'min_merchants_in_poi': self.pois['merchant_count'].min(),
            'max_merchants_in_poi': self.pois['merchant_count'].max(),
            'avg_max_distance': self.pois['max_distance'].mean(),
            'avg_avg_distance': self.pois['avg_distance'].mean(),
        }
        
        
        if 'city' in self.pois.columns:
            city_dist = self.pois['city'].value_counts().to_dict()
            stats['poi_distribution_by_city'] = city_dist
        
        return pd.Series(stats)
    
    def validate_pois(self):
        """Validate that all merchants in POIs are within specified radius"""
        if self.pois is None:
            print("No POIs detected yet.")
            return
        
        print("\nValidating POI constraints...")
        all_valid = True
        
        for _, poi in self.pois.iterrows():
            poi_id = int(poi['poi_id'].split('_')[1])
            merchants_in_poi = self.df[self.df['poi_cluster'] == poi_id]
            
            
            distances = merchants_in_poi.apply(
                lambda r: self.haversine_distance(
                    poi['center_lat'], poi['center_lon'],
                    r[self.lat_col], r[self.lon_col]
                ), axis=1
            )
            
            max_dist = distances.max()
            if max_dist > poi['radius_meters']:
                print(f"⚠️  {poi['poi_id']}: Max distance {max_dist:.0f}m exceeds radius {poi['radius_meters']}m")
                all_valid = False
            else:
                print(f"✓ {poi['poi_id']}: All {len(merchants_in_poi)} merchants within {poi['radius_meters']}m (max: {max_dist:.0f}m)")
        
        if all_valid:
            print("\n✅ All POIs valid - all merchants within specified radius from center")
        else:
            print("\n⚠️  Some POIs have validation issues")
        
        return all_valid


def optimize_poi_parameters(df, radius_list=[100, 200, 250, 300], 
                           min_merchants_list=[20, 30, 40, 50]):
    """
    Test different parameter combinations to find optimal settings
    """
    results = []
    
    for radius in radius_list:
        for min_merchants in min_merchants_list:
            print(f"\n{'='*50}")
            print(f"Testing: radius={radius}m, min_merchants={min_merchants}")
            
            detector = POIDetector(df)
            pois = detector.detect_pois_density_based(
                radius_meters=radius, 
                min_merchants=min_merchants,
                method='kmeans_refined'
            )
            
            if len(pois) > 0:
                stats = detector.get_statistics()
                is_valid = detector.validate_pois()
                
                results.append({
                    'radius': radius,
                    'min_merchants': min_merchants,
                    'num_pois': len(pois),
                    'merchants_in_pois': stats['total_merchants_in_pois'],
                    'coverage_pct': stats['coverage_percentage'],
                    'avg_merchants_per_poi': stats['avg_merchants_per_poi'],
                    'valid': is_valid
                })
            else:
                results.append({
                    'radius': radius,
                    'min_merchants': min_merchants,
                    'num_pois': 0,
                    'merchants_in_pois': 0,
                    'coverage_pct': 0,
                    'avg_merchants_per_poi': 0,
                    'valid': True
                })
    
    results_df = pd.DataFrame(results)

    
    print("\n" + "="*80)
    print("OPTIMIZATION RESULTS SUMMARY")
    print("="*80)
    print(results_df.to_string())
    
    return results_df