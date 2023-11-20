import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial.distance import cdist
from geopy import distance
from .uuid import UUIDCollection
from .googleRequests import googleRequests
from geopandas import GeoDataFrame
from shapely.geometry import Point


class stopCollection:
    def __init__(self,
                 data:UUIDCollection,
                 min_distance,
                 stop_point_num):
        assert isinstance(data,UUIDCollection),TypeError("Invalid type for uuid_collection. Should be of UUIDCollection type")
        self.uuids = data
        self.min_distance = min_distance
        self.stop_point_num = stop_point_num


        stops_gdf = self._extract_stops(self.uuids.uuid_collection)
        self.filtered_stops = self._collect_points_far_from_each_other(stops_gdf)
        # self.filtered_stops = filtered_stops.iloc[:self.stop_point_num,:]
        # self.all_stops = stops_gdf

        
    def _extract_stops(self,data):
        ### THIS is where we go from individual daily trajectories and stop points to ###
        ### A full dataframe having all the stop points in one###
        stops_list = []
        for uuid in data:
            for date,stop_points in data[uuid].mpd_stop_points.items():
                #remove the stop_points which are of the same lat_long
                if stop_points.shape[0] > 0:
                    #add in uuid
                    stop_points[self.uuids.unique_col] = [uuid]*stop_points.shape[0]
                    stops_list.append(stop_points)
        
        stops_gdf = pd.concat(stops_list,axis = 0)
        stops_gdf = stops_gdf.drop_duplicates(subset=[stops_gdf.geometry.name])
        stops_gdf.reset_index(drop = True,inplace = True)
        return stops_gdf

    def _distance_calculation(self,points):
        #makes a square distance matric between each point
        #uses the geodesic distance
        distance_func = lambda x,y:distance.distance(x,y).meters
        #put in the first point
        selected_points_idx = [0]
        selected_points = [points[0]]
        points = points[1:]
        #need to align with indexing of the stops dataframe from which points is made. Hence i + 1 is used
        points = [(i+1,j) for i,j in enumerate(points)]
        while len(selected_points) < self.stop_point_num:
            distance_array = cdist(np.array([points[0][1]]),np.array(selected_points),metric=distance_func)[0]
            min_distance = distance_array[np.argmin(distance_array)]
            if min_distance >= self.min_distance:
                selected_points.append(points[0][1])
                selected_points_idx.append(points[0][0])
            points = points[1:]
            if len(points) == 1:
                break
            
        return selected_points_idx

    def _filter_points(self,distance_matrix,min_distance):
        #as each point should be min_distance or above from other points,
        #this filters the matrix to find the indices where each point is far from the other points
        bool_matrix = np.zeros(shape = distance_matrix.shape,dtype=np.bool)
        bool_matrix[np.where(distance_matrix >= min_distance)] = True
        filtered_idx = np.where(bool_matrix.sum(axis = 1) == distance_matrix.shape[0] - 1)[0]
        return filtered_idx

    
    def _collect_points_far_from_each_other(self,stops_gdf):
        #collects lat,long
        all_points = [(i.y,i.x) for i in stops_gdf[stops_gdf.geometry.name]]
        self.all_points = all_points
        if len(all_points) <= self.stop_point_num:
            filtered_stops = stops_gdf
        else:
            print("Starting to Filter points based on minimum distance between points")
            filtered_idx = self._distance_calculation(all_points)
            print("Finished obtaining points based on minimum distance")
            filtered_stops = stops_gdf.iloc[filtered_idx,:]

        # distance_matrix = self._distance_calculation(all_points)
        # filtered_idx = self._filter_points(distance_matrix,min_distance)
        # filtered_stops = stops_gdf.iloc[filtered_idx,:]
        return filtered_stops
    
class placeOfInterest:
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.placeType = None
        self.name = None
        self.place_id = None
    

class stopPoint:
    def __init__(self,radius,geometry:Point,start_time,end_time,duration_s,uuid,**kwargs):
        self.radius = radius
        self.lat = geometry.y
        self.long = geometry.x
        self.start_time = start_time
        self.end_time = end_time
        self.time_duration = duration_s
        self.uuid = uuid
        self.vicinity_locations = [] #Holds placeOfInterest Data

    def extractVicinityData(self,googleRequestsObject:googleRequests):
        assert isinstance(googleRequestsObject,googleRequests),"googleRequestsObject needs to be of googleRequests Class"
        jsondata = googleRequestsObject._extractData(self.lat,self.long,self.radius)
        if jsondata:
            self._parseJSONData(jsondata)

    def _parseJSONData(self,jsondata):
        for i,details in enumerate(jsondata):
            place = placeOfInterest()
            place.latitude = details['geometry']['location']['lat']
            place.longitude = details['geometry']['location']['lng']
            place.placeType = str(details['types'])
            place.name = details['name']
            place.place_id = details['place_id']
            self.vicinity_locations.append(place)

class ExtractAndOrganizeData:
    def __init__(self,stops_of_interest:GeoDataFrame,radius):
        """
        params : stops_of_interest: takes in the Dataframe obtained from the stopCollection Class
        radius : radius to look for Places of Interest
        """
        self.stops_of_interest = stops_of_interest
        self.radius = radius
        self.points_of_interest = [stopPoint(radius = self.radius,**record) for record in self.stops_of_interest.to_dict(orient = 'records')]
    def __extractData(self):
        googleRequestsObj = googleRequests()
        for point in self.points_of_interest:
            #fills up the locations around a stop point 
            point.extractVicinityData(googleRequestsObj)
    def __organizeData(self):
        #creates a pandas dataframe of the data
        df_dict = {'Stop Point' : [],
                   'UUID' : [],
                   'POI Point' : [],
                   'POI Name' : [],
                   'POI Type': [],
                   'Time Spent at Stop Point' : []}
        for point in self.points_of_interest:
            if len(point.vicinity_locations) > 0:
                for poi in point.vicinity_locations:
                    df_dict['Stop Point'].append(Point([point.long,point.lat]))
                    df_dict['UUID'].append(point.uuid)
                    df_dict['POI Point'].append(Point([poi.longitude,poi.latitude]))
                    df_dict['POI Name'].append(poi.name)
                    df_dict['POI Type'].append(poi.placeType)
                    df_dict['Time Spent at Stop Point'].append(point.time_duration)
        gdf = GeoDataFrame(data=df_dict,geometry='Stop Point')
        return gdf
    def extractAndorganizeData(self):
        self.__extractData()
        return self.__organizeData()

        
            





        


    
        
                

                




