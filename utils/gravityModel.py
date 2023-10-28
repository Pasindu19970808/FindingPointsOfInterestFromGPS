import pandas as pd
import numpy as np
from geopandas import GeoDataFrame
from ast import literal_eval
from collections import Counter
from shapely.geometry import Point
from geopy import distance
from scipy.spatial.distance import cdist

class POIgdf:
    def __init__(self,poi_gdf:GeoDataFrame,
                 poi_type_col_name,
                 activity_type_col_name,
                 poi_point_col_name,
                 split_stop_point:bool = True,
                 stop_point_lat = None,
                 stop_point_long = None,
                 stop_point_col_name = None):
        
        #POI GeoDataFrame can have the Split Point split into lat and long or be sent in as shapely Point
        
        self.split_stop_point = split_stop_point
        if self.split_stop_point == True:
            assert stop_point_lat != None,"stop_point_lat is required if split_stop_point is True"
            assert stop_point_long != None,"stop_point_long is required if split_stop_point is True"
            self.stop_point_lat = stop_point_lat
            self.stop_point_long = stop_point_long

        assert poi_type_col_name in poi_gdf.columns, KeyError(f"{poi_type_col_name} not in column names of poi_gdf")
        self.stop_point_col_name = stop_point_col_name if stop_point_col_name != None else  poi_gdf.geometry.name

        self.activity_type_col_name = activity_type_col_name
        self.poi_type_col_name = poi_type_col_name

        assert poi_point_col_name in poi_gdf.columns,KeyError(f"{poi_point_col_name} not in column names of poi_gdf")
        self.poi_point_col_name = poi_point_col_name

        
        if self.split_stop_point:
            self.poi_gdf = self._split_stop_point(poi_gdf)
    def _split_stop_point(self,poi_gdf):
        poi_gdf[self.stop_point_lat] = poi_gdf[self.stop_point_col_name].apply(lambda x: x.y)
        poi_gdf[self.stop_point_long] = poi_gdf[self.stop_point_col_name].apply(lambda x: x.x)
        return poi_gdf
    

class activityMapper:
    def __init__(self,file_path):
        activity_map_df = pd.read_csv(file_path)
        assert "POI Type" in activity_map_df.columns.tolist(),"Missing POI Type Column"
        assert "Activity" in activity_map_df.columns.tolist(),"Missing Activity Column"
        self.activity_map_df = activity_map_df
        self.activity_types = activity_map_df['Activity'].tolist()
        self.poi_types = activity_map_df['POI Type'].tolist()
        self.poitype__activity_map_dict = dict(zip(activity_map_df['POI Type'],activity_map_df['Activity']))

    def reset_POI_types(self,poi_gdf_obj:POIgdf,drop_empty_poi_types = True):
        #Remove some POI Types that are not useful and too general (e.g. Establishment, Point of Interest)
        gdf = poi_gdf_obj.poi_gdf.copy()
        reset_types = lambda x: str([i for i in literal_eval(x) if i in self.activity_map_df['POI Type'].tolist()])
        gdf[poi_gdf_obj.poi_type_col_name] = gdf[poi_gdf_obj.poi_type_col_name].apply(reset_types)
        if drop_empty_poi_types:
            gdf = gdf.loc[gdf[poi_gdf_obj.poi_type_col_name] != '[]']
        poi_gdf_obj.poi_gdf = gdf.reset_index(drop = True)
        return poi_gdf_obj
    
    def add_activity_types(self,poi_gdf_obj:POIgdf):
        gdf = poi_gdf_obj.poi_gdf.copy()
        gdf[poi_gdf_obj.activity_type_col_name] = np.nan
        find_activity = lambda x : str(list(set(self.poitype__activity_map_dict[i] for i in literal_eval(x))))
        gdf[poi_gdf_obj.activity_type_col_name] = gdf[poi_gdf_obj.poi_type_col_name].apply(find_activity)
        poi_gdf_obj.poi_gdf = gdf
        return poi_gdf_obj

    
    

class gravityModel:
    def __init__(self,activityMapper_obj:activityMapper,poi_gdf_obj:POIgdf):
        assert isinstance(activityMapper_obj,activityMapper),"activityMapper_obj should be of activityMapper Type"
        assert isinstance(poi_gdf_obj,POIgdf),"poi_gdf_obj should be of POIgdf Type"
        
        self.activityMapper = activityMapper_obj
        self.poi_gdf = poi_gdf_obj

        self.counts_df = self.__getActivityCounts()
        self.distance_df = self.__closestDistanceToPOI()
    def calculate_probability(self,method = 'newton_gravity'):
        if method == 'newton_gravity':
            results = self.__calculate_activity_probability_original(self.counts_df,self.distance_df)
        return results
    def __obtainActivityDict(self):
        cols = [self.poi_gdf.stop_point_col_name]
        cols.extend(list(set(self.activityMapper.activity_types)))
        activity_df_dict = {k:[] for k in cols}
        return activity_df_dict

    def __getActivityCounts(self):
        gdf = self.poi_gdf.poi_gdf.copy()
        activity_df_dict = self.__obtainActivityDict()

        for k,grp in gdf.groupby([self.poi_gdf.stop_point_lat,self.poi_gdf.stop_point_long]):

            activity_df_dict[self.poi_gdf.stop_point_col_name].append(Point(k[1],k[0]))
            activity_list = map(lambda x: literal_eval(x),grp[self.poi_gdf.activity_type_col_name])
            flat_activity_list = [activity for sublist in activity_list for activity in sublist]

            count_dict = dict(Counter(flat_activity_list))

            for activity in list(set(self.activityMapper.activity_types)):
                if activity in count_dict.keys():
                    activity_df_dict[activity].append(count_dict[activity])
                else:
                    activity_df_dict[activity].append(0)
        counts_df = GeoDataFrame(data = activity_df_dict,geometry=self.poi_gdf.stop_point_col_name)
        return counts_df
    
    def __distanceCalculation(self,ref_point,poi_points):
        distance_func = lambda x,y:distance.distance(x,y).meters
        distance_array = cdist(ref_point,poi_points,metric=distance_func)[0]
        #gets the minimum distance
        min_distance = distance_array[np.argmin(distance_array)]
        return min_distance
    
    
    def __closestDistanceToPOI(self):
        #get the closest distance to each activity item
        gdf = self.poi_gdf.poi_gdf.copy()
        activity_df_dict = self.__obtainActivityDict()
        activity_types = pd.Series(self.activityMapper.activity_types).unique().tolist()
        #list(set(self.activityMapper.activity_types))

        for k,grp in gdf.groupby([self.poi_gdf.stop_point_lat,self.poi_gdf.stop_point_long]):
            activity_df_dict[self.poi_gdf.stop_point_col_name].append(Point(k[1],k[0])) #Adding Long Lat
            for activity in activity_types:
                points_list = []
                for record in grp.to_dict(orient = 'records'):
                    if activity in literal_eval(record[self.poi_gdf.activity_type_col_name]):
                        point = record[self.poi_gdf.poi_point_col_name]
                        points_list.append((point.y,point.x))
                if len(points_list) >= 1:
                    #Checks if any of the POIs sorrounding the Stop Point are having the activity of interest
                    #Adding Lat Long
                    ref_point = np.array([(k[0],k[1])])
                    poi_points = np.array(points_list)
                    min_distance = self.__distanceCalculation(ref_point,poi_points)
                    activity_df_dict[activity].append(min_distance)
                else:
                    activity_df_dict[activity].append(10000000)
        distance_df = GeoDataFrame(data = activity_df_dict,geometry=self.poi_gdf.stop_point_col_name)
        return distance_df
    def __calculate_activity_probability_original(self,counts_df:GeoDataFrame,distance_df:GeoDataFrame):
        #turn to numpy arrays and get only the activiy columns

        counts = counts_df.to_numpy()[:,1:]
        distances = distance_df.to_numpy()[:,1:]
        distances_squared = distances**2
        probability = counts/distances_squared
        result_df = self.counts_df.copy()
        result_df.iloc[:,1:] = probability
        return result_df



    




        

