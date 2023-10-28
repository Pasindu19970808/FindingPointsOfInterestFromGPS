import pandas as pd
from shapely.geometry import Point
from geopandas import GeoDataFrame
from pandas.core.indexes.datetimes import DatetimeIndex


class Trajectory:
    def __init__(self,
                 df,
                 lat_col,
                 lon_col,
                 required_cols,
                 geometry_col_name = 'geometry',
                 crs = "EPSG:4326"):
        
        assert isinstance(df.index,DatetimeIndex),"Trajectory has to have Index of DatetimeIndex type that is sorted"
        self.df = df
        self.lat_col = lat_col
        self.lon_col = lon_col
        self.crs = crs
        self.geometry_col_name = geometry_col_name
        self.__processTrajectory()
        self.trajectory = self.__makeGeoDataFrame(required_cols)

    def __processTrajectory(self):
        #long = (east - west) (x axis)
        #lat = (north - south) (y axis)
        self.df[self.geometry_col_name] = [Point(long,lat) for lat,long in zip(self.df[self.lat_col],self.df[self.lon_col])]
    def __makeGeoDataFrame(self,required_cols):
        #appends required columns with geometry column name
        required_cols.append(self.geometry_col_name)
        return GeoDataFrame(self.df[required_cols],crs = self.crs,geometry=self.geometry_col_name)
    def get_col_name(self):
        return self.trajectory.geometry.name
    def __len__(self):
        return self.trajectory.shape[0]
    
class detectStops:
    def __init__(self,trajectory):
        assert isinstance(trajectory,GeoDataFrame),"Invalid Trajectory type. Needs to be GeoDataFrame type"




        